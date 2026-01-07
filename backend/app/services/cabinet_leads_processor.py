"""
Servicio que orquesta el procesamiento completo de cabinet leads después del upload CSV.
Ejecuta en secuencia: ingesta de identidad, atribución de leads, y refresh de materialized views.
"""
import logging
from typing import Optional, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.ingestion import IngestionService
from app.services.lead_attribution import LeadAttributionService
from app.models.ops import IngestionRun, RunStatus

logger = logging.getLogger(__name__)


class CabinetLeadsProcessor:
    """Procesador que ejecuta toda la cadena de procesamiento de cabinet leads"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = IngestionService(db)
        self.attribution_service = LeadAttributionService(db)
    
    def process_all(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        refresh_index: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta todo el procesamiento en secuencia:
        1. Ingesta de identidad (crea identity_links)
        2. Poblar lead_events (crea eventos en observational.lead_events)
        3. Refresh materialized views
        
        Retorna diccionario con estadísticas de cada paso.
        """
        results = {
            "ingestion": None,
            "attribution": None,
            "refresh_mvs": None,
            "errors": []
        }
        
        try:
            # Paso 1: Ingesta de Identidad
            logger.info("Paso 1: Ejecutando ingesta de identidad para cabinet_leads...")
            try:
                ingestion_run = self.ingestion_service.run_ingestion(
                    scope_date_from=date_from,
                    scope_date_to=date_to,
                    source_tables=["module_ct_cabinet_leads"],
                    incremental=False,  # Procesar todo
                    refresh_index=refresh_index
                )
                
                results["ingestion"] = {
                    "run_id": ingestion_run.id,
                    "status": ingestion_run.status.value if hasattr(ingestion_run.status, 'value') else str(ingestion_run.status),
                    "stats": ingestion_run.stats or {}
                }
                logger.info(f"Ingesta completada: run_id={ingestion_run.id}, status={ingestion_run.status}")
            except Exception as e:
                error_msg = f"Error en ingesta de identidad: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
                results["ingestion"] = {"error": error_msg}
            
            # Paso 2: Poblar Lead Events
            logger.info("Paso 2: Poblando lead_events desde cabinet_leads...")
            try:
                attribution_stats = self.attribution_service.populate_events_from_cabinet(
                    date_from=date_from,
                    date_to=date_to
                )
                
                results["attribution"] = {
                    "processed": attribution_stats.get("processed", 0),
                    "created": attribution_stats.get("created", 0),
                    "updated": attribution_stats.get("updated", 0),
                    "skipped": attribution_stats.get("skipped", 0),
                    "errors": attribution_stats.get("errors", 0)
                }
                logger.info(f"Atribución completada: {attribution_stats}")
            except Exception as e:
                error_msg = f"Error poblando lead_events: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
                results["attribution"] = {"error": error_msg}
            
            # Paso 3: Refresh Materialized Views
            logger.info("Paso 3: Refrescando materialized views...")
            try:
                mv_results = self._refresh_materialized_views()
                results["refresh_mvs"] = mv_results
                logger.info(f"Refresh de MVs completado: {mv_results}")
            except Exception as e:
                error_msg = f"Error refrescando materialized views: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
                results["refresh_mvs"] = {"error": error_msg}
            
            return results
            
        except Exception as e:
            error_msg = f"Error general en procesamiento: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)
            return results
    
    def _refresh_materialized_views(self) -> Dict[str, Any]:
        """Refresca las materialized views relacionadas con cabinet leads"""
        mv_results = {}
        
        # MV 1: mv_yango_cabinet_claims_for_collection
        mv_name_1 = "ops.mv_yango_cabinet_claims_for_collection"
        logger.info(f"Refrescando {mv_name_1}...")
        try:
            # Verificar si existe índice único para usar CONCURRENTLY
            has_unique = self._check_unique_index(mv_name_1)
            
            if has_unique:
                try:
                    self.db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv_name_1}"))
                    self.db.commit()
                    mv_results[mv_name_1] = {"status": "ok", "method": "concurrent"}
                    logger.info(f"{mv_name_1} refrescado con CONCURRENTLY")
                except Exception as e:
                    logger.warning(f"CONCURRENTLY falló para {mv_name_1}, usando refresh normal: {e}")
                    self.db.rollback()
                    self.db.execute(text(f"REFRESH MATERIALIZED VIEW {mv_name_1}"))
                    self.db.commit()
                    mv_results[mv_name_1] = {"status": "ok", "method": "normal"}
            else:
                self.db.execute(text(f"REFRESH MATERIALIZED VIEW {mv_name_1}"))
                self.db.commit()
                mv_results[mv_name_1] = {"status": "ok", "method": "normal"}
                logger.info(f"{mv_name_1} refrescado (sin índice único)")
        except Exception as e:
            error_msg = f"Error refrescando {mv_name_1}: {str(e)}"
            logger.error(error_msg)
            mv_results[mv_name_1] = {"status": "error", "error": error_msg}
        
        # MV 2: mv_cabinet_financial_14d (si existe)
        mv_name_2 = "ops.mv_cabinet_financial_14d"
        logger.info(f"Verificando si existe {mv_name_2}...")
        try:
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_cabinet_financial_14d'
                )
            """)
            exists = self.db.execute(check_query).scalar()
            
            if exists:
                logger.info(f"Refrescando {mv_name_2}...")
                self.db.execute(text(f"REFRESH MATERIALIZED VIEW {mv_name_2}"))
                self.db.commit()
                mv_results[mv_name_2] = {"status": "ok", "method": "normal"}
                logger.info(f"{mv_name_2} refrescado")
            else:
                logger.info(f"{mv_name_2} no existe, omitiendo")
                mv_results[mv_name_2] = {"status": "skipped", "reason": "does_not_exist"}
        except Exception as e:
            error_msg = f"Error verificando/refrescando {mv_name_2}: {str(e)}"
            logger.error(error_msg)
            mv_results[mv_name_2] = {"status": "error", "error": error_msg}
        
        return mv_results
    
    def _check_unique_index(self, mv_name: str) -> bool:
        """Verifica si existe un índice único en la materialized view"""
        try:
            # Extraer schema y nombre de la MV
            parts = mv_name.split('.')
            if len(parts) == 2:
                schema_name, mv_name_only = parts
            else:
                return False
            
            query = text("""
                SELECT COUNT(*) > 0 AS has_unique_index
                FROM pg_index i
                JOIN pg_class c ON c.oid = i.indexrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_namespace tn ON tn.oid = t.relnamespace
                WHERE tn.nspname = :schema_name
                  AND t.relname = :mv_name
                  AND i.indisunique = true
            """)
            
            result = self.db.execute(query, {
                "schema_name": schema_name,
                "mv_name": mv_name_only
            })
            has_index = result.scalar()
            return bool(has_index) if has_index is not None else False
        except Exception as e:
            logger.warning(f"Error verificando índice único para {mv_name}: {e}")
            return False


