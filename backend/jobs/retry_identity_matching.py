"""
Job de reintento de matching para leads Cabinet sin identidad.
Idempotente: puede ejecutarse múltiples veces sin romper.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.db import SessionLocal
from app.models.ops import IdentityMatchingJob
from app.models.canon import IdentityLink, IdentityOrigin, OriginTag, DecidedBy, OriginResolutionStatus, IdentityUnmatched
from app.services.matching import MatchingEngine, IdentityCandidateInput
from app.services.data_contract import DataContract
from app.services.normalization import normalize_phone, normalize_name

logger = logging.getLogger(__name__)

# Configuración
MAX_ATTEMPTS = 5
BATCH_SIZE = 500  # Procesar en lotes de 500
DEFAULT_CONFIDENCE = 95.0


class IdentityMatchingRetryJob:
    """Job para reintentar matching de leads sin identidad"""
    
    def __init__(self, db: Session):
        self.db = db
        self.matching_engine = MatchingEngine(db)
    
    def run(
        self,
        limit: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        gap_reason: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el job de reintento de matching.
        
        Args:
            limit: Número máximo de leads a procesar (None = todos)
            date_from: Fecha mínima de lead_date
            date_to: Fecha máxima de lead_date
            gap_reason: Filtrar por gap_reason específico
            risk_level: Filtrar por risk_level específico
        
        Returns:
            Dict con estadísticas del procesamiento
        """
        stats = {
            "processed": 0,
            "matched": 0,
            "failed": 0,
            "pending": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            start_time = datetime.utcnow()
            
            # Obtener leads unresolved de la vista (sin limit para procesar en batches)
            all_leads = self._get_unresolved_leads(None, date_from, date_to, gap_reason, risk_level)
            total_leads = len(all_leads)
            
            if limit:
                all_leads = all_leads[:limit]
                total_leads = min(len(all_leads), limit)
            
            logger.info(f"Encontrados {total_leads} leads unresolved para procesar (batch_size={BATCH_SIZE})")
            
            # Procesar en batches
            for batch_start in range(0, len(all_leads), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(all_leads))
                batch = all_leads[batch_start:batch_end]
                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (len(all_leads) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Procesando batch {batch_num}/{total_batches} ({len(batch)} leads)")
                
                batch_stats = {
                    "matched": 0,
                    "failed": 0,
                    "pending": 0,
                    "skipped": 0,
                    "errors": []
                }
                
                for lead in batch:
                    try:
                        result = self._process_lead(lead)
                        stats["processed"] += 1
                        
                        if result["status"] == "matched":
                            stats["matched"] += 1
                            batch_stats["matched"] += 1
                        elif result["status"] == "failed":
                            stats["failed"] += 1
                            batch_stats["failed"] += 1
                        elif result["status"] == "pending":
                            stats["pending"] += 1
                            batch_stats["pending"] += 1
                        else:
                            stats["skipped"] += 1
                            batch_stats["skipped"] += 1
                            
                    except Exception as e:
                        logger.error(f"Error procesando lead {lead.get('lead_id')}: {e}", exc_info=True)
                        error_msg = f"Lead {lead.get('lead_id')}: {str(e)}"
                        stats["errors"].append(error_msg)
                        batch_stats["errors"].append(error_msg)
                        stats["processed"] += 1
                
                # Commit después de cada batch
                try:
                    self.db.commit()
                    logger.info(f"Batch {batch_num} completado: matched={batch_stats['matched']}, failed={batch_stats['failed']}, pending={batch_stats['pending']}, skipped={batch_stats['skipped']}")
                except Exception as e:
                    logger.error(f"Error en commit del batch {batch_num}: {e}", exc_info=True)
                    self.db.rollback()
                    stats["errors"].append(f"Batch {batch_num} commit error: {str(e)}")
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Job completado en {elapsed:.1f}s: processed={stats['processed']}, matched={stats['matched']}, failed={stats['failed']}, pending={stats['pending']}, skipped={stats['skipped']}")
            stats["elapsed_seconds"] = round(elapsed, 2)
            return stats
            
        except Exception as e:
            logger.error(f"Error en job de matching: {e}", exc_info=True)
            stats["errors"].append(f"Error general: {str(e)}")
            return stats
    
    def _get_unresolved_leads(
        self,
        limit: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        gap_reason: Optional[str],
        risk_level: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Obtiene leads unresolved de la vista v_identity_gap_analysis"""
        query = """
            SELECT 
                lead_id,
                lead_date,
                person_key,
                gap_reason,
                risk_level,
                gap_age_days
            FROM ops.v_identity_gap_analysis
            WHERE gap_reason != 'resolved'
        """
        params = {}
        conditions = []
        
        if date_from:
            conditions.append("lead_date >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            conditions.append("lead_date <= :date_to")
            params["date_to"] = date_to
        
        if gap_reason:
            conditions.append("gap_reason = :gap_reason")
            params["gap_reason"] = gap_reason
        
        if risk_level:
            conditions.append("risk_level = :risk_level")
            params["risk_level"] = risk_level
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY gap_age_days DESC, lead_date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        result = self.db.execute(text(query), params)
        rows = result.fetchall()
        
        return [
            {
                "lead_id": row.lead_id,
                "lead_date": row.lead_date,
                "person_key": row.person_key,
                "gap_reason": row.gap_reason,
                "risk_level": row.risk_level,
                "gap_age_days": row.gap_age_days
            }
            for row in rows
        ]
    
    def _process_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa un lead individual: crea/actualiza job y intenta matching o crea origin"""
        lead_id = lead["lead_id"]
        gap_reason = lead.get("gap_reason")
        person_key_existing = lead.get("person_key")
        
        # Asegurar existencia de job (upsert)
        job = self.db.query(IdentityMatchingJob).filter(
            IdentityMatchingJob.source_type == "cabinet",
            IdentityMatchingJob.source_id == lead_id
        ).first()
        
        if not job:
            job = IdentityMatchingJob(
                source_type="cabinet",
                source_id=lead_id,
                status="pending",
                attempt_count=0
            )
            self.db.add(job)
            self.db.flush()
        
        # Si ya está matched, skip
        if job.status == "matched":
            return {"status": "skipped", "reason": "already_matched"}
        
        # Si ya falló después de MAX_ATTEMPTS, skip
        if job.status == "failed" and job.attempt_count >= MAX_ATTEMPTS:
            return {"status": "skipped", "reason": "max_attempts_reached"}
        
        # CASO ESPECIAL: Si gap_reason es 'no_origin' y ya tiene person_key, crear origin directamente
        if gap_reason == "no_origin" and person_key_existing:
            try:
                from uuid import UUID
                person_key_uuid = UUID(str(person_key_existing))
                
                # Obtener datos del lead
                lead_data = self._get_lead_data(lead_id)
                if not lead_data:
                    job.status = "failed"
                    job.fail_reason = "lead_not_found"
                    self.db.flush()
                    return {"status": "failed", "reason": "lead_not_found"}
                
                # Crear/actualizar identity_origin directamente
                self._ensure_identity_origin(lead_id, person_key_uuid, lead_data)
                
                # Actualizar job
                job.status = "matched"
                job.matched_person_key = person_key_uuid
                job.fail_reason = None
                job.attempt_count += 1
                job.last_attempt_at = datetime.utcnow()
                self.db.flush()
                
                logger.info(f"Lead {lead_id} origin creado para person_key existente {person_key_uuid}")
                return {"status": "matched", "person_key": str(person_key_uuid), "action": "created_origin"}
            
            except Exception as e:
                logger.error(f"Error creando origin para lead {lead_id}: {e}", exc_info=True)
                self.db.rollback()
                job.status = "pending" if job.attempt_count < MAX_ATTEMPTS else "failed"
                job.fail_reason = f"error_creating_origin: {str(e)}"
                job.attempt_count += 1
                job.last_attempt_at = datetime.utcnow()
                self.db.flush()
                return {"status": job.status, "reason": "error_creating_origin"}
        
        # CASO NORMAL: Intentar matching (gap_reason == 'no_identity' o 'inconsistent_origin')
        job.attempt_count += 1
        job.last_attempt_at = datetime.utcnow()
        
        try:
            # Obtener datos del lead
            lead_data = self._get_lead_data(lead_id)
            if not lead_data:
                job.status = "failed"
                job.fail_reason = "lead_not_found"
                self.db.flush()  # Cambiar a flush (commit se hace por batch)
                return {"status": "failed", "reason": "lead_not_found"}
            
            # Crear candidate para matching
            candidate = self._create_candidate(lead_data)
            
            # Intentar matching
            match_result = self.matching_engine.match_person(candidate)
            
            if match_result.person_key:
                # Matching exitoso
                person_key = match_result.person_key
                
                # Crear/actualizar identity_link
                self._ensure_identity_link(lead_id, person_key, match_result, lead_data)
                
                # Crear/actualizar identity_origin
                self._ensure_identity_origin(lead_id, person_key, lead_data)
                
                # Actualizar job
                job.status = "matched"
                job.matched_person_key = person_key
                job.fail_reason = None
                self.db.flush()  # Cambiar a flush (commit se hace por batch)
                
                logger.info(f"Lead {lead_id} matcheado exitosamente a person_key {person_key}")
                return {"status": "matched", "person_key": str(person_key), "action": "matched_and_linked"}
            else:
                # Matching falló
                fail_reason = match_result.reason_code or "no_match_found"
                
                if job.attempt_count >= MAX_ATTEMPTS:
                    job.status = "failed"
                else:
                    job.status = "pending"
                
                job.fail_reason = fail_reason
                self.db.flush()  # Cambiar a flush (commit se hace por batch)
                
                logger.debug(f"Lead {lead_id} no matcheado (intento {job.attempt_count}): {fail_reason}")
                return {"status": "pending" if job.status == "pending" else "failed", "reason": fail_reason}
        
        except Exception as e:
            logger.error(f"Error en matching para lead {lead_id}: {e}", exc_info=True)
            self.db.rollback()  # Rollback en caso de error
            job.status = "pending" if job.attempt_count < MAX_ATTEMPTS else "failed"
            job.fail_reason = f"error: {str(e)}"
            self.db.flush()  # Cambiar a flush (commit se hace por batch)
            return {"status": job.status, "reason": "error"}
    
    def _get_lead_data(self, lead_id: str) -> Optional[Dict[str, Any]]:
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
            WHERE external_id = :lead_id OR id::TEXT = :lead_id
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"lead_id": lead_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
    
    def _create_candidate(self, lead_data: Dict[str, Any]) -> IdentityCandidateInput:
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
        
        # Model (no hay brand en cabinet_leads)
        model_norm = lead_data.get("asset_model")
        
        snapshot_date = lead_data.get("lead_created_at")
        if isinstance(snapshot_date, str):
            from datetime import datetime
            snapshot_date = datetime.fromisoformat(snapshot_date.replace('Z', '+00:00'))
        
        source_pk = lead_data.get("external_id") or str(lead_data.get("id", ""))
        
        return IdentityCandidateInput(
            source_table="module_ct_cabinet_leads",
            source_pk=source_pk,
            snapshot_date=snapshot_date or datetime.utcnow(),
            park_id=None,  # No disponible en cabinet_leads
            phone_norm=phone_norm,
            license_norm=None,  # No disponible en cabinet_leads
            plate_norm=plate_norm,
            name_norm=name_norm,
            brand_norm=None,  # No disponible en cabinet_leads
            model_norm=model_norm
        )
    
    def _ensure_identity_link(
        self,
        lead_id: str,
        person_key: UUID,
        match_result: Any,
        lead_data: Dict[str, Any]
    ):
        """Asegura que existe identity_link para el lead"""
        source_pk = lead_data.get("external_id") or str(lead_data.get("id", ""))
        
        existing_link = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == "module_ct_cabinet_leads",
            IdentityLink.source_pk == source_pk
        ).first()
        
        if not existing_link:
            snapshot_date = lead_data.get("lead_created_at")
            if isinstance(snapshot_date, str):
                from datetime import datetime
                snapshot_date = datetime.fromisoformat(snapshot_date.replace('Z', '+00:00'))
            
            link = IdentityLink(
                person_key=person_key,
                source_table="module_ct_cabinet_leads",
                source_pk=source_pk,
                snapshot_date=snapshot_date or datetime.utcnow(),
                match_rule=match_result.rule or "RETRY_JOB",
                match_score=match_result.score or 0,
                confidence_level=match_result.confidence or "HIGH",
                evidence=match_result.evidence or {}
            )
            self.db.add(link)
        
        # Limpiar de identity_unmatched si existía previamente
        self.db.query(IdentityUnmatched).filter(
            IdentityUnmatched.source_table == "module_ct_cabinet_leads",
            IdentityUnmatched.source_pk == source_pk
        ).delete(synchronize_session=False)
        
        self.db.flush()
    
    def _ensure_identity_origin(
        self,
        lead_id: str,
        person_key: UUID,
        lead_data: Dict[str, Any]
    ):
        """Asegura que existe identity_origin para el person_key"""
        # Usar SQL directo para evitar problemas con enum
        check_query = text("""
            SELECT person_key, origin_tag, origin_source_id
            FROM canon.identity_origin
            WHERE person_key = :person_key
            LIMIT 1
        """)
        result = self.db.execute(check_query, {"person_key": str(person_key)})
        existing_origin = result.fetchone()
        
        if not existing_origin:
            origin_created_at = lead_data.get("lead_created_at")
            if isinstance(origin_created_at, str):
                from datetime import datetime
                origin_created_at = datetime.fromisoformat(origin_created_at.replace('Z', '+00:00'))
            
            # Workaround: usar SQL directo porque SQLAlchemy está enviando el nombre del enum en lugar del valor
            origin_created_at_val = origin_created_at or datetime.utcnow()
            self.db.execute(text("""
                INSERT INTO canon.identity_origin 
                (person_key, origin_tag, origin_source_id, origin_confidence, origin_created_at, decided_by, resolution_status)
                VALUES (:person_key, 'cabinet_lead', :origin_source_id, :origin_confidence, :origin_created_at, 'system', 'resolved_auto')
                ON CONFLICT (person_key) DO UPDATE
                SET origin_tag = 'cabinet_lead',
                    origin_source_id = :origin_source_id,
                    resolution_status = 'resolved_auto',
                    updated_at = NOW()
            """), {
                "person_key": str(person_key),
                "origin_source_id": lead_id,
                "origin_confidence": DEFAULT_CONFIDENCE,
                "origin_created_at": origin_created_at_val
            })
            self.db.flush()  # Cambiar a flush (commit se hace por batch)
        else:
            # Si ya existe pero no es cabinet_lead o source_id es diferente, actualizar
            origin_tag_val = existing_origin.origin_tag if hasattr(existing_origin, 'origin_tag') else existing_origin[1]
            origin_source_id_val = existing_origin.origin_source_id if hasattr(existing_origin, 'origin_source_id') else existing_origin[2]
            
            if origin_tag_val != 'cabinet_lead' or origin_source_id_val != lead_id:
                self.db.execute(text("""
                    UPDATE canon.identity_origin
                    SET origin_tag = 'cabinet_lead',
                        origin_source_id = :origin_source_id,
                        resolution_status = 'resolved_auto',
                        updated_at = NOW()
                    WHERE person_key = :person_key
                """), {
                    "person_key": str(person_key),
                    "origin_source_id": lead_id
                })
                self.db.flush()


def run_job(
    limit: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    gap_reason: Optional[str] = None,
    risk_level: Optional[str] = None
) -> Dict[str, Any]:
    """
    Función de entrada para ejecutar el job.
    Puede ser llamada desde CLI, cron, o API.
    """
    db = SessionLocal()
    try:
        job = IdentityMatchingRetryJob(db)
        return job.run(limit, date_from, date_to, gap_reason, risk_level)
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    # Parsear argumentos simples
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    
    result = run_job(limit=limit)
    print(f"Resultado: {result}")
