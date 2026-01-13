#!/usr/bin/env python
"""
Job para sembrar la cola de recovery desde el backlog del KPI rojo.
Inserta/Upsert todos los lead_source_pk de ops.v_cabinet_kpi_red_backlog
en ops.cabinet_kpi_red_recovery_queue como pending.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import SessionLocal
from app.models.ops import CabinetKpiRedRecoveryQueue

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


class SeedKpiRedQueueJob:
    """Job para sembrar la cola de recovery desde el backlog del KPI rojo"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run(self) -> Dict[str, Any]:
        """
        Ejecuta el job para sembrar la cola.
        
        Returns:
            Dict con estadísticas del procesamiento
        """
        stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": []
        }
        
        try:
            start_time = datetime.utcnow()
            logger.info(f"Iniciando SeedKpiRedQueueJob a las {start_time}")
            
            # Obtener todos los lead_source_pk del backlog
            backlog_query = text("""
                SELECT lead_source_pk
                FROM ops.v_cabinet_kpi_red_backlog
                ORDER BY age_days DESC, lead_date DESC
            """)
            backlog_result = self.db.execute(backlog_query)
            backlog_leads = [row.lead_source_pk for row in backlog_result.fetchall()]
            
            total_leads = len(backlog_leads)
            logger.info(f"Encontrados {total_leads} leads en el backlog del KPI rojo")
            
            # Procesar en batches
            for batch_start in range(0, total_leads, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_leads)
                batch = backlog_leads[batch_start:batch_end]
                batch_num = (batch_start // BATCH_SIZE) + 1
                total_batches = (total_leads + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Procesando batch {batch_num}/{total_batches} ({len(batch)} leads)")
                
                for lead_source_pk in batch:
                    try:
                        # Buscar si ya existe en la queue
                        existing = self.db.query(CabinetKpiRedRecoveryQueue).filter(
                            CabinetKpiRedRecoveryQueue.lead_source_pk == lead_source_pk
                        ).first()
                        
                        if existing:
                            # Si ya existe pero está matched/failed, resetear a pending si está en el backlog
                            # (puede haber sido removido y vuelto a entrar)
                            if existing.status in ('matched', 'failed'):
                                existing.status = 'pending'
                                existing.attempt_count = 0
                                existing.fail_reason = None
                                existing.matched_person_key = None
                                existing.last_attempt_at = None
                                existing.updated_at = datetime.utcnow()
                                stats["updated"] += 1
                            # Si ya está pending, no hacer nada
                            else:
                                pass
                        else:
                            # Insertar nuevo registro
                            queue_entry = CabinetKpiRedRecoveryQueue(
                                lead_source_pk=lead_source_pk,
                                status='pending',
                                attempt_count=0
                            )
                            self.db.add(queue_entry)
                            stats["inserted"] += 1
                        
                        stats["processed"] += 1
                        
                    except Exception as e:
                        logger.error(f"Error procesando lead {lead_source_pk}: {e}", exc_info=True)
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
            logger.info(f"SeedKpiRedQueueJob finalizado en {duration:.2f} segundos. Estadísticas: {stats}")
            
        except Exception as e:
            logger.critical(f"Error crítico en SeedKpiRedQueueJob: {e}", exc_info=True)
            stats["errors"].append(f"Critical error: {str(e)}")
            self.db.rollback()
        
        return stats


def run_job() -> Dict[str, Any]:
    """
    Función de entrada para ejecutar el job.
    Puede ser llamada desde CLI, cron, o API.
    """
    db = SessionLocal()
    try:
        job = SeedKpiRedQueueJob(db)
        return job.run()
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    result = run_job()
    print(f"Job Result: {result}")
