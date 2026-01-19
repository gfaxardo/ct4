#!/usr/bin/env python
"""
Job para recuperar leads del KPI rojo.
Lee pending de ops.cabinet_kpi_red_recovery_queue y intenta matching.
Si match:
  - UPSERT canon.identity_links
  - UPSERT canon.identity_origin (FIX ORIGIN_MISSING)
  - Marca queue status=matched
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.db import SessionLocal
from app.models.ops import CabinetKpiRedRecoveryQueue
from app.models.canon import IdentityLink, IdentityOrigin, OriginTag, DecidedBy, OriginResolutionStatus, IdentityUnmatched
from app.services.matching import MatchingEngine, IdentityCandidateInput
from app.services.data_contract import DataContract
from app.services.normalization import normalize_phone, normalize_name, normalize_plate

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
MAX_ATTEMPTS = 5
DEFAULT_CONFIDENCE = 95.0


class RecoverKpiRedLeadsJob:
    """Job para recuperar leads del KPI rojo"""
    
    def __init__(self, db: Session):
        self.db = db
        self.matching_engine = MatchingEngine(db)
    
    def run(
        self,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el job para recuperar leads del KPI rojo.
        
        Args:
            limit: Número máximo de leads a procesar (None = todos los pending)
        
        Returns:
            Dict con estadísticas del procesamiento
        """
        stats = {
            "processed": 0,
            "matched": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            start_time = datetime.utcnow()
            logger.info(f"Iniciando RecoverKpiRedLeadsJob a las {start_time}")
            
            # Obtener leads pending de la queue
            query = self.db.query(CabinetKpiRedRecoveryQueue).filter(
                CabinetKpiRedRecoveryQueue.status == 'pending'
            ).order_by(
                CabinetKpiRedRecoveryQueue.attempt_count.asc(),
                CabinetKpiRedRecoveryQueue.created_at.asc()
            )
            
            if limit:
                query = query.limit(limit)
            
            pending_leads = query.all()
            total_leads = len(pending_leads)
            
            logger.info(f"Encontrados {total_leads} leads pending en la queue (batch_size={BATCH_SIZE})")
            
            # Procesar en batches
            for batch_start in range(0, total_leads, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_leads)
                batch = pending_leads[batch_start:batch_end]
                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (total_leads + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Procesando batch {batch_num}/{total_batches} ({len(batch)} leads)")
                
                for queue_entry in batch:
                    lead_source_pk = queue_entry.lead_source_pk
                    try:
                        result = self._process_lead(queue_entry)
                        stats["processed"] += 1
                        
                        if result["status"] == "matched":
                            stats["matched"] += 1
                        elif result["status"] == "skipped":
                            stats["skipped"] += 1
                        else:
                            stats["failed"] += 1
                            stats["errors"].append(f"Lead {lead_source_pk}: {result.get('reason', 'unknown_error')}")
                            
                    except Exception as e:
                        logger.error(f"Error inesperado procesando lead {lead_source_pk}: {e}", exc_info=True)
                        stats["failed"] += 1
                        stats["errors"].append(f"Lead {lead_source_pk}: {str(e)}")
                        self.db.rollback()
                        continue
                
                # Commit después de cada batch
                try:
                    self.db.commit()
                    logger.info(f"Commit de batch {batch_num} completado.")
                except Exception as e:
                    logger.error(f"Error haciendo commit de batch {batch_num}: {e}", exc_info=True)
                    self.db.rollback()
                    stats["errors"].append(f"Batch {batch_num} commit failed: {str(e)}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"RecoverKpiRedLeadsJob finalizado en {duration:.2f} segundos. Estadísticas: {stats}")
            
        except Exception as e:
            logger.critical(f"Error crítico en RecoverKpiRedLeadsJob: {e}", exc_info=True)
            stats["errors"].append(f"Critical error: {str(e)}")
            self.db.rollback()
        
        return stats
    
    def _process_lead(self, queue_entry: CabinetKpiRedRecoveryQueue) -> Dict[str, Any]:
        """Procesa un lead individual: intenta matching y crea links/origin"""
        lead_source_pk = queue_entry.lead_source_pk
        
        # Verificar si ya tiene link (puede haber sido creado por otro proceso)
        existing_link = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == 'module_ct_cabinet_leads',
            IdentityLink.source_pk == lead_source_pk
        ).first()
        
        if existing_link:
            # Ya tiene link, solo asegurar origin y marcar como matched
            person_key = existing_link.person_key
            lead_data = self._get_lead_data(lead_source_pk)
            if lead_data:
                self._ensure_identity_origin(lead_source_pk, person_key, lead_data)
                queue_entry.status = 'matched'
                queue_entry.matched_person_key = person_key
                queue_entry.fail_reason = None
                queue_entry.updated_at = datetime.utcnow()
                self.db.flush()
                logger.info(f"Lead {lead_source_pk} ya tenía link, origin asegurado y marcado como matched")
                return {"status": "matched", "person_key": str(person_key), "action": "already_linked"}
            else:
                logger.warning(f"Lead {lead_source_pk} tiene link pero no se encontró en module_ct_cabinet_leads")
                return {"status": "skipped", "reason": "lead_not_found"}
        
        # Incrementar attempt_count
        queue_entry.attempt_count += 1
        queue_entry.last_attempt_at = datetime.utcnow()
        
        # Obtener datos del lead
        lead_data = self._get_lead_data(lead_source_pk)
        if not lead_data:
            queue_entry.status = 'failed'
            queue_entry.fail_reason = 'lead_not_found'
            self.db.flush()
            return {"status": "failed", "reason": "lead_not_found"}
        
        try:
            # Crear candidate para matching
            candidate = self._create_candidate(lead_data, lead_source_pk)
            
            # Intentar matching
            match_result = self.matching_engine.match_person(candidate)
            
            if match_result.person_key:
                # Matching exitoso
                person_key = UUID(match_result.person_key)
                
                # Crear/actualizar identity_link
                self._ensure_identity_link(lead_source_pk, person_key, match_result, lead_data)
                
                # Crear/actualizar identity_origin (FIX ORIGIN_MISSING)
                self._ensure_identity_origin(lead_source_pk, person_key, lead_data)
                
                # Actualizar queue
                queue_entry.status = 'matched'
                queue_entry.matched_person_key = person_key
                queue_entry.fail_reason = None
                queue_entry.updated_at = datetime.utcnow()
                self.db.flush()
                
                logger.info(f"Lead {lead_source_pk} matcheado exitosamente a person_key {person_key}")
                return {"status": "matched", "person_key": str(person_key), "action": "matched_and_linked"}
            else:
                # Matching falló
                fail_reason = match_result.reason_code or "no_match_found"
                
                if queue_entry.attempt_count >= MAX_ATTEMPTS:
                    queue_entry.status = 'failed'
                else:
                    queue_entry.status = 'pending'
                
                queue_entry.fail_reason = fail_reason
                queue_entry.updated_at = datetime.utcnow()
                self.db.flush()
                
                logger.debug(f"Lead {lead_source_pk} no matcheado (intento {queue_entry.attempt_count}): {fail_reason}")
                return {"status": "pending" if queue_entry.status == 'pending' else "failed", "reason": fail_reason}
                
        except Exception as e:
            logger.error(f"Error en matching para lead {lead_source_pk}: {e}", exc_info=True)
            self.db.rollback()
            
            if queue_entry.attempt_count >= MAX_ATTEMPTS:
                queue_entry.status = 'failed'
            else:
                queue_entry.status = 'pending'
            
            queue_entry.fail_reason = f"error: {str(e)}"
            queue_entry.updated_at = datetime.utcnow()
            self.db.flush()
            return {"status": queue_entry.status, "reason": "error"}
    
    def _get_lead_data(self, lead_source_pk: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos del lead desde module_ct_cabinet_leads"""
        query = text("""
            SELECT 
                id,
                external_id,
                lead_created_at,
                park_phone,
                first_name,
                middle_name,
                last_name,
                asset_plate_number,
                asset_model
            FROM public.module_ct_cabinet_leads
            WHERE COALESCE(external_id::text, id::text) = :lead_source_pk
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"lead_source_pk": lead_source_pk})
        row = result.fetchone()
        
        if not row:
            return None
        
        return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
    
    def _create_candidate(self, lead_data: Dict[str, Any], lead_source_pk: str) -> IdentityCandidateInput:
        """Crea un IdentityCandidateInput desde datos del lead"""
        # Normalizar phone
        phone_norm = None
        if lead_data.get("park_phone"):
            phone_norm = normalize_phone(lead_data["park_phone"])
        
        # Normalizar name
        name_parts = [
            lead_data.get("first_name"),
            lead_data.get("middle_name"),
            lead_data.get("last_name")
        ]
        name_raw = " ".join([p for p in name_parts if p])
        name_norm = normalize_name(name_raw) if name_raw else None
        
        # Normalizar plate
        plate_norm = None
        if lead_data.get("asset_plate_number"):
            from app.services.normalization import normalize_plate
            plate_norm = normalize_plate(lead_data["asset_plate_number"])
        
        # Model
        model_norm = lead_data.get("asset_model")
        
        snapshot_date = lead_data.get("lead_created_at")
        if isinstance(snapshot_date, str):
            snapshot_date = datetime.fromisoformat(snapshot_date.replace('Z', '+00:00'))
        
        return IdentityCandidateInput(
            source_table="module_ct_cabinet_leads",
            source_pk=lead_source_pk,
            snapshot_date=snapshot_date or datetime.utcnow(),
            park_id=None,
            phone_norm=phone_norm,
            license_norm=None,
            plate_norm=plate_norm,
            name_norm=name_norm,
            brand_norm=None,
            model_norm=model_norm
        )
    
    def _ensure_identity_link(
        self,
        lead_source_pk: str,
        person_key: UUID,
        match_result: Any,
        lead_data: Dict[str, Any]
    ):
        """Asegura que existe identity_link para el lead"""
        existing_link = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == 'module_ct_cabinet_leads',
            IdentityLink.source_pk == lead_source_pk
        ).first()
        
        if not existing_link:
            snapshot_date = lead_data.get("lead_created_at")
            if isinstance(snapshot_date, str):
                snapshot_date = datetime.fromisoformat(snapshot_date.replace('Z', '+00:00'))
            
            link = IdentityLink(
                person_key=person_key,
                source_table="module_ct_cabinet_leads",
                source_pk=lead_source_pk,
                snapshot_date=snapshot_date or datetime.utcnow(),
                match_rule=match_result.rule or "KPI_RED_RECOVERY",
                match_score=match_result.score or 0,
                confidence_level=match_result.confidence or "HIGH",
                evidence=match_result.evidence or {}
            )
            self.db.add(link)
            logger.info(f"Creado IdentityLink para lead {lead_source_pk} a person_key {person_key}")
        else:
            # Si ya existe, actualizar si es necesario
            if existing_link.person_key != person_key:
                logger.warning(f"Lead {lead_source_pk} ya linkeado a {existing_link.person_key}, pero nuevo match es {person_key}. Actualizando link.")
                existing_link.person_key = person_key
                existing_link.match_rule = match_result.rule or "KPI_RED_RECOVERY_UPDATE"
                existing_link.match_score = match_result.score or 0
                existing_link.confidence_level = match_result.confidence or "HIGH"
                existing_link.evidence = match_result.evidence or {}
                existing_link.linked_at = datetime.utcnow()
                logger.info(f"Actualizado IdentityLink para lead {lead_source_pk} a person_key {person_key}")
        
        # Limpiar de identity_unmatched si existía previamente
        self.db.query(IdentityUnmatched).filter(
            IdentityUnmatched.source_table == "module_ct_cabinet_leads",
            IdentityUnmatched.source_pk == lead_source_pk
        ).delete(synchronize_session=False)
        
        self.db.flush()
    
    def _ensure_identity_origin(
        self,
        lead_source_pk: str,
        person_key: UUID,
        lead_data: Dict[str, Any]
    ):
        """Asegura que existe identity_origin para el person_key (FIX ORIGIN_MISSING)"""
        check_query = text("""
            SELECT person_key, origin_tag, origin_source_id
            FROM canon.identity_origin
            WHERE person_key = :person_key
            LIMIT 1
        """)
        result = self.db.execute(check_query, {"person_key": str(person_key)})
        existing_origin = result.fetchone()
        
        origin_created_at = lead_data.get("lead_created_at")
        if isinstance(origin_created_at, str):
            origin_created_at = datetime.fromisoformat(origin_created_at.replace('Z', '+00:00'))
        origin_created_at_val = origin_created_at or datetime.utcnow()
        
        if not existing_origin:
            # Crear origin
            self.db.execute(text("""
                INSERT INTO canon.identity_origin
                (person_key, origin_tag, origin_source_id, origin_confidence, origin_created_at, decided_by, resolution_status)
                VALUES (:person_key, :origin_tag, :origin_source_id, :origin_confidence, :origin_created_at, :decided_by, :resolution_status)
                ON CONFLICT (person_key) DO UPDATE
                SET origin_tag = EXCLUDED.origin_tag,
                    origin_source_id = EXCLUDED.origin_source_id,
                    resolution_status = EXCLUDED.resolution_status,
                    updated_at = NOW()
            """), {
                "person_key": str(person_key),
                "origin_tag": OriginTag.CABINET_LEAD.value,
                "origin_source_id": lead_source_pk,
                "origin_confidence": DEFAULT_CONFIDENCE,
                "origin_created_at": origin_created_at_val,
                "decided_by": DecidedBy.SYSTEM.value,
                "resolution_status": OriginResolutionStatus.RESOLVED_AUTO.value
            })
            self.db.flush()
            logger.info(f"Creado IdentityOrigin para person_key {person_key} con lead {lead_source_pk}")
        else:
            # Si ya existe pero no es cabinet_lead o source_id es diferente, actualizar
            origin_tag_val = existing_origin.origin_tag if hasattr(existing_origin, 'origin_tag') else existing_origin[1]
            origin_source_id_val = existing_origin.origin_source_id if hasattr(existing_origin, 'origin_source_id') else existing_origin[2]
            
            if origin_tag_val != OriginTag.CABINET_LEAD.value or origin_source_id_val != lead_source_pk:
                logger.warning(f"IdentityOrigin para person_key {person_key} tiene tag '{origin_tag_val}' y source_id '{origin_source_id_val}', actualizando a 'cabinet_lead' y '{lead_source_pk}'.")
                self.db.execute(text("""
                    UPDATE canon.identity_origin
                    SET origin_tag = :origin_tag,
                        origin_source_id = :origin_source_id,
                        resolution_status = :resolution_status,
                        updated_at = NOW()
                    WHERE person_key = :person_key
                """), {
                    "person_key": str(person_key),
                    "origin_tag": OriginTag.CABINET_LEAD.value,
                    "origin_source_id": lead_source_pk,
                    "resolution_status": OriginResolutionStatus.RESOLVED_AUTO.value
                })
                self.db.flush()
                logger.info(f"Actualizado IdentityOrigin para person_key {person_key} con lead {lead_source_pk}")


def run_job(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Función de entrada para ejecutar el job.
    Puede ser llamada desde CLI, cron, o API.
    """
    db = SessionLocal()
    try:
        job = RecoverKpiRedLeadsJob(db)
        return job.run(limit)
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    _limit = None
    if len(sys.argv) > 1:
        try:
            _limit = int(sys.argv[1])
        except ValueError:
            pass
    
    result = run_job(limit=_limit)
    print(f"Job Result: {result}")
