"""
Job permanente "Recovery→Impact" que conecta recovery con impacto en Cobranza Cabinet 14d.
Propósito: Asegurar que cuando el matching engine encuentre person_key para un lead cabinet,
se crea/actualiza el vínculo canónico y se registra en audit para medición de impacto.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID

from app.db import SessionLocal
from app.models.canon import IdentityLink, IdentityOrigin, OriginTag, DecidedBy, OriginResolutionStatus

logger = logging.getLogger(__name__)

# Configuración
BATCH_SIZE = 500  # Procesar en lotes de 500
DEFAULT_CONFIDENCE = 95.0


class CabinetRecoveryImpactJob:
    """Job para conectar recovery con impacto en Cobranza Cabinet 14d"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run(
        self,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el job de recovery impact.
        
        Propósito:
        - Asegurar que cuando el matching engine encuentre person_key para un lead cabinet:
          1) Se crea/actualiza el vínculo canónico lead_id -> person_key (canon.identity_links)
          2) Se hace upsert en canon.identity_origin (cabinet_lead + origin_source_id=lead_id)
          3) Se registra first_recovered_at (si estaba null) en ops.cabinet_lead_recovery_audit
        
        Args:
            limit: Número máximo de leads a procesar (None = todos)
        
        Returns:
            Dict con estadísticas del procesamiento
        """
        stats = {
            "processed": 0,
            "links_created": 0,
            "links_updated": 0,
            "origins_created": 0,
            "origins_updated": 0,
            "audit_created": 0,
            "audit_updated": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            start_time = datetime.utcnow()
            
            # Obtener leads "unidentified" o "identified_no_origin" en ops.v_cabinet_identity_recovery_impact_14d
            query = text("""
                SELECT 
                    lead_id,
                    lead_date,
                    person_key_effective,
                    identity_effective,
                    origin_ok,
                    claim_status_bucket
                FROM ops.v_cabinet_identity_recovery_impact_14d
                WHERE claim_status_bucket IN ('unidentified', 'identified_no_origin')
                ORDER BY lead_date DESC
                LIMIT :limit
            """)
            
            limit_val = limit or 10000  # Si no hay limit, procesar hasta 10000
            result = self.db.execute(query, {"limit": limit_val})
            all_leads = result.fetchall()
            
            total_leads = len(all_leads)
            logger.info(f"Encontrados {total_leads} leads para procesar (batch_size={BATCH_SIZE})")
            
            # Procesar en batches
            for batch_start in range(0, len(all_leads), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(all_leads))
                batch = all_leads[batch_start:batch_end]
                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (len(all_leads) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Procesando batch {batch_num}/{total_batches} ({len(batch)} leads)")
                
                for lead_row in batch:
                    try:
                        lead_id = lead_row.lead_id
                        lead_date = lead_row.lead_date
                        person_key_effective = lead_row.person_key_effective
                        identity_effective = lead_row.identity_effective
                        origin_ok = lead_row.origin_ok
                        claim_status_bucket = lead_row.claim_status_bucket
                        
                        # Si no tiene person_key, saltar (necesita matching primero)
                        if not person_key_effective:
                            stats["skipped"] += 1
                            continue
                        
                        # Asegurar identity_origin
                        origin_result = self._ensure_identity_origin(lead_id, person_key_effective, lead_date)
                        if origin_result["created"]:
                            stats["origins_created"] += 1
                        elif origin_result["updated"]:
                            stats["origins_updated"] += 1
                        
                        # Registrar en audit
                        audit_result = self._ensure_recovery_audit(lead_id, person_key_effective)
                        if audit_result["created"]:
                            stats["audit_created"] += 1
                        elif audit_result["updated"]:
                            stats["audit_updated"] += 1
                        
                        stats["processed"] += 1
                        
                        # Commit por batch
                        if stats["processed"] % BATCH_SIZE == 0:
                            self.db.commit()
                            logger.info(f"Commit batch: procesados {stats['processed']}/{total_leads}")
                    
                    except Exception as e:
                        logger.error(f"Error procesando lead {lead_row.lead_id if hasattr(lead_row, 'lead_id') else 'unknown'}: {e}", exc_info=True)
                        stats["errors"].append(str(e))
                        self.db.rollback()
                        continue
                
                # Commit final del batch
                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Error en commit batch {batch_num}: {e}", exc_info=True)
                    self.db.rollback()
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Job completado en {elapsed:.2f}s. Procesados: {stats['processed']}, Creados: {stats['origins_created']}, Actualizados: {stats['origins_updated']}, Audit: {stats['audit_created']}")
            
            return stats
        
        except Exception as e:
            logger.error(f"Error fatal en job: {e}", exc_info=True)
            self.db.rollback()
            stats["errors"].append(str(e))
            return stats
    
    def _ensure_identity_origin(
        self,
        lead_id: str,
        person_key: UUID,
        lead_date
    ) -> Dict[str, bool]:
        """
        Asegura que existe identity_origin para el person_key con origin_tag='cabinet_lead' y origin_source_id=lead_id
        """
        result = {"created": False, "updated": False}
        
        # Verificar si existe
        check_query = text("""
            SELECT person_key, origin_tag, origin_source_id
            FROM canon.identity_origin
            WHERE person_key = :person_key
            LIMIT 1
        """)
        check_result = self.db.execute(check_query, {"person_key": str(person_key)})
        existing_origin = check_result.fetchone()
        
        # Calcular origin_created_at desde lead_date
        origin_created_at = lead_date
        if isinstance(origin_created_at, str):
            origin_created_at = datetime.fromisoformat(origin_created_at.replace('Z', '+00:00'))
        elif hasattr(origin_created_at, 'date'):
            origin_created_at = datetime.combine(origin_created_at.date(), datetime.min.time())
        
        if not existing_origin:
            # Crear identity_origin
            self.db.execute(text("""
                INSERT INTO canon.identity_origin 
                (person_key, origin_tag, origin_source_id, origin_confidence, origin_created_at, decided_by, resolution_status)
                VALUES (:person_key, 'cabinet_lead', :origin_source_id, :origin_confidence, :origin_created_at, 'system', 'resolved_auto')
            """), {
                "person_key": str(person_key),
                "origin_source_id": lead_id,
                "origin_confidence": DEFAULT_CONFIDENCE,
                "origin_created_at": origin_created_at or datetime.utcnow()
            })
            result["created"] = True
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
                result["updated"] = True
        
        self.db.flush()
        return result
    
    def _ensure_recovery_audit(
        self,
        lead_id: str,
        person_key: UUID
    ) -> Dict[str, bool]:
        """
        Asegura que existe registro en ops.cabinet_lead_recovery_audit.
        Registra first_recovered_at (si estaba null) y actualiza last_recovered_at.
        """
        result = {"created": False, "updated": False}
        now = datetime.utcnow()
        
        # Verificar si existe
        check_query = text("""
            SELECT lead_id, first_recovered_at
            FROM ops.cabinet_lead_recovery_audit
            WHERE lead_id = :lead_id
            LIMIT 1
        """)
        check_result = self.db.execute(check_query, {"lead_id": lead_id})
        existing_audit = check_result.fetchone()
        
        if not existing_audit:
            # Crear registro
            self.db.execute(text("""
                INSERT INTO ops.cabinet_lead_recovery_audit 
                (lead_id, first_recovered_at, last_recovered_at, recovered_person_key, recovered_by, recovery_method, updated_at)
                VALUES (:lead_id, :first_recovered_at, :last_recovered_at, :recovered_person_key, :recovered_by, :recovery_method, :updated_at)
            """), {
                "lead_id": lead_id,
                "first_recovered_at": now,
                "last_recovered_at": now,
                "recovered_person_key": str(person_key),
                "recovered_by": "system",
                "recovery_method": "identity_link",
                "updated_at": now
            })
            result["created"] = True
        else:
            # Actualizar last_recovered_at (first_recovered_at no cambia)
            first_recovered_at = existing_audit.first_recovered_at if hasattr(existing_audit, 'first_recovered_at') else existing_audit[1]
            
            if not first_recovered_at:
                # Si first_recovered_at es null, actualizarlo
                self.db.execute(text("""
                    UPDATE ops.cabinet_lead_recovery_audit
                    SET first_recovered_at = :first_recovered_at,
                        last_recovered_at = :last_recovered_at,
                        recovered_person_key = :recovered_person_key,
                        updated_at = :updated_at
                    WHERE lead_id = :lead_id
                """), {
                    "lead_id": lead_id,
                    "first_recovered_at": now,
                    "last_recovered_at": now,
                    "recovered_person_key": str(person_key),
                    "updated_at": now
                })
                result["updated"] = True
            else:
                # Solo actualizar last_recovered_at
                self.db.execute(text("""
                    UPDATE ops.cabinet_lead_recovery_audit
                    SET last_recovered_at = :last_recovered_at,
                        recovered_person_key = :recovered_person_key,
                        updated_at = :updated_at
                    WHERE lead_id = :lead_id
                """), {
                    "lead_id": lead_id,
                    "last_recovered_at": now,
                    "recovered_person_key": str(person_key),
                    "updated_at": now
                })
                result["updated"] = True
        
        self.db.flush()
        return result


def run_job(
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Función de entrada para ejecutar el job.
    Puede ser llamada desde CLI, cron, o API.
    """
    db = SessionLocal()
    try:
        job = CabinetRecoveryImpactJob(db)
        return job.run(limit)
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
