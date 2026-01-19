"""
Endpoint para procesamiento automático de cabinet leads
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
import csv
import io
import logging

from app.db import get_db, SessionLocal
from app.schemas.cabinet_leads import CabinetLeadsUploadResponse
from app.services.cabinet_leads_processor import CabinetLeadsProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# NUEVO: Endpoint para procesar automáticamente nuevos leads
# ============================================================================

@router.get("/pending-count")
def get_pending_leads_count(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna el conteo de leads pendientes de procesar.
    Compara registros en module_ct_cabinet_leads vs identity_links + identity_unmatched.
    Un registro está "procesado" si está en identity_links O en identity_unmatched.
    """
    try:
        # Total en tabla (solo con external_id válido)
        total_query = db.execute(text("""
            SELECT COUNT(*) FROM public.module_ct_cabinet_leads
            WHERE external_id IS NOT NULL AND external_id != ''
        """))
        total_in_table = total_query.scalar() or 0
        
        # Procesados en identity_links
        links_query = db.execute(text("""
            SELECT COUNT(DISTINCT source_pk) 
            FROM canon.identity_links 
            WHERE source_table = 'module_ct_cabinet_leads'
        """))
        total_in_links = links_query.scalar() or 0
        
        # Procesados en identity_unmatched
        unmatched_query = db.execute(text("""
            SELECT COUNT(DISTINCT source_pk) 
            FROM canon.identity_unmatched 
            WHERE source_table = 'module_ct_cabinet_leads'
        """))
        total_in_unmatched = unmatched_query.scalar() or 0
        
        # Total procesados = links + unmatched (sin duplicados entre tablas)
        # Usamos UNION para evitar contar duplicados
        total_processed_query = db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT source_pk FROM canon.identity_links 
                WHERE source_table = 'module_ct_cabinet_leads'
                UNION
                SELECT DISTINCT source_pk FROM canon.identity_unmatched 
                WHERE source_table = 'module_ct_cabinet_leads'
            ) AS processed
        """))
        total_processed = total_processed_query.scalar() or 0
        
        # Pendientes reales
        pending = total_in_table - total_processed
        
        # Fecha del último registro en la tabla
        max_date_query = db.execute(text("""
            SELECT MAX(lead_created_at)::date 
            FROM public.module_ct_cabinet_leads
        """))
        max_lead_date = max_date_query.scalar()
        
        # Fecha del último procesamiento real (última corrida completada)
        last_processed_query = db.execute(text("""
            SELECT MAX(completed_at)::date 
            FROM ops.ingestion_runs 
            WHERE status = 'completed' 
            AND job_type = 'identity_run'
        """))
        last_processed_date = last_processed_query.scalar()
        
        return {
            "total_in_table": total_in_table,
            "total_in_links": total_in_links,
            "total_in_unmatched": total_in_unmatched,
            "total_processed": total_processed,
            "pending_count": max(0, pending),
            "max_lead_date": str(max_lead_date) if max_lead_date else None,
            "last_processed_date": str(last_processed_date) if last_processed_date else None,
            "has_pending": pending > 0
        }
    except Exception as e:
        logger.error(f"Error obteniendo conteo de pendientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-new")
def process_new_leads(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    refresh_index: bool = Query(True, description="Refrescar drivers_index antes de procesar"),
    process_all: bool = Query(True, description="Procesar todos los registros sin filtro de fecha")
) -> Dict[str, Any]:
    """
    Detecta y procesa automáticamente los nuevos leads en module_ct_cabinet_leads
    que aún no han sido procesados.
    
    - process_all=True: Procesa TODOS los registros (recomendado para detectar pendientes antiguos)
    - process_all=False: Solo procesa desde la última fecha procesada
    """
    try:
        # Obtener conteo de pendientes
        pending_info = get_pending_leads_count(db)
        
        if not pending_info["has_pending"]:
            return {
                "status": "no_pending",
                "message": "No hay leads nuevos para procesar",
                "pending_count": 0
            }
        
        # Determinar rango de fechas a procesar
        date_from = None
        date_to = None
        
        if not process_all:
            # Solo procesar desde la última fecha procesada
            if pending_info["last_processed_date"]:
                date_from = datetime.strptime(pending_info["last_processed_date"], "%Y-%m-%d").date()
            if pending_info["max_lead_date"]:
                date_to = datetime.strptime(pending_info["max_lead_date"], "%Y-%m-%d").date()
        
        # Si process_all=True, date_from y date_to quedan None
        # Esto hará que el sistema procese TODOS los registros
        # El motor de identidad detectará automáticamente cuáles ya están procesados
        
        # Ejecutar procesamiento en background
        background_tasks.add_task(
            _process_new_leads_background,
            date_from=date_from,
            date_to=date_to,
            refresh_index=refresh_index
        )
        
        return {
            "status": "processing",
            "message": f"Procesando {pending_info['pending_count']} leads pendientes (modo: {'completo' if process_all else 'incremental'})",
            "pending_count": pending_info["pending_count"],
            "mode": "full" if process_all else "incremental",
            "date_from": str(date_from) if date_from else "sin límite",
            "date_to": str(date_to) if date_to else "sin límite"
        }
        
    except Exception as e:
        logger.error(f"Error iniciando procesamiento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _process_new_leads_background(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    refresh_index: bool = True
):
    """Ejecuta el procesamiento de nuevos leads en background"""
    db = SessionLocal()
    try:
        logger.info(f"Iniciando procesamiento automático de nuevos leads (date_from={date_from}, date_to={date_to})")
        
        processor = CabinetLeadsProcessor(db)
        results = processor.process_all(
            date_from=date_from,
            date_to=date_to,
            refresh_index=refresh_index
        )
        
        logger.info(f"Procesamiento automático completado: {results}")
        
        if results.get("errors"):
            logger.warning(f"Errores durante procesamiento: {results['errors']}")
    
    except Exception as e:
        logger.error(f"Error en procesamiento automático: {e}", exc_info=True)
    finally:
        db.close()


def parse_boolean(value: str) -> Optional[bool]:
    """Convierte string a boolean"""
    if not value or value.strip() == '':
        return None
    if isinstance(value, bool):
        return value
    value_lower = str(value).lower().strip()
    return value_lower in ('true', '1', 'yes', 't', 'y')


def parse_timestamp(value: str) -> Optional[datetime]:
    """Convierte string a timestamp (soporta formato ISO con T)"""
    if not value or value.strip() == '':
        return None
    try:
        # Remover T y convertir
        value_clean = value.replace('T', ' ').strip()
        # Intentar varios formatos
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
            try:
                return datetime.strptime(value_clean, fmt)
            except ValueError:
                continue
        return None
    except (ValueError, AttributeError):
        return None


def parse_date(value: str) -> Optional[date]:
    """Convierte string a date"""
    if not value or value.strip() == '':
        return None
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


@router.post("/ensure-index")
def ensure_unique_index(db: Session = Depends(get_db)):
    """
    Endpoint para crear manualmente el índice único en external_id.
    Útil si el índice no existe y necesitas crearlo antes de subir datos.
    """
    try:
        ensure_unique_index_exists(db)
        return {"status": "success", "message": "Índice único verificado/creado exitosamente"}
    except Exception as e:
        logger.error(f"Error asegurando índice único: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando índice único: {str(e)}")


@router.get("/diagnostics")
def get_cabinet_leads_diagnostics(db: Session = Depends(get_db)):
    """
    Diagnóstico: Verifica estado de la tabla y qué fechas ya están procesadas.
    Útil para determinar desde qué fecha subir datos nuevos.
    """
    diagnostics = {
        "table_exists": False,
        "table_row_count": 0,
        "max_lead_date_in_table": None,
        "max_event_date_in_lead_events": None,
        "max_snapshot_date_in_identity_links": None,
        "recommended_start_date": None,
        "processed_external_ids_count": 0
    }
    
    try:
        # 1. Verificar si la tabla existe
        check_table = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'module_ct_cabinet_leads'
            )
        """))
        table_exists = check_table.scalar()
        diagnostics["table_exists"] = bool(table_exists)
        
        if not table_exists:
            return diagnostics
        
        # 2. Contar filas en la tabla
        count_query = db.execute(text("SELECT COUNT(*) FROM public.module_ct_cabinet_leads"))
        diagnostics["table_row_count"] = count_query.scalar() or 0
        
        # 3. Fecha máxima en module_ct_cabinet_leads
        max_date_query = db.execute(text("""
            SELECT MAX(lead_created_at::date) 
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at IS NOT NULL
        """))
        max_date = max_date_query.scalar()
        if max_date:
            diagnostics["max_lead_date_in_table"] = str(max_date)
        
        # 4. Fecha máxima en lead_events (cabinet)
        try:
            max_event_query = db.execute(text("""
                SELECT MAX(event_date) 
                FROM observational.lead_events
                WHERE source_table = 'module_ct_cabinet_leads'
            """))
            max_event_date = max_event_query.scalar()
            if max_event_date:
                diagnostics["max_event_date_in_lead_events"] = str(max_event_date)
        except Exception as e:
            logger.warning(f"No se pudo consultar lead_events: {e}")
        
        # 5. Fecha máxima en identity_links (cabinet)
        try:
            max_link_query = db.execute(text("""
                SELECT MAX(snapshot_date::date) 
                FROM canon.identity_links
                WHERE source_table = 'module_ct_cabinet_leads'
            """))
            max_link_date = max_link_query.scalar()
            if max_link_date:
                diagnostics["max_snapshot_date_in_identity_links"] = str(max_link_date)
        except Exception as e:
            logger.warning(f"No se pudo consultar identity_links: {e}")
        
        # 6. Contar external_ids ya procesados
        try:
            processed_count_query = db.execute(text("""
                SELECT COUNT(DISTINCT il.source_pk)
                FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_cabinet_leads'
            """))
            diagnostics["processed_external_ids_count"] = processed_count_query.scalar() or 0
        except Exception as e:
            logger.warning(f"No se pudo contar external_ids procesados: {e}")
        
        # 7. Recomendar fecha de inicio
        # Usar la fecha más reciente entre lead_events e identity_links
        dates_to_consider = []
        if diagnostics["max_event_date_in_lead_events"]:
            dates_to_consider.append(datetime.strptime(diagnostics["max_event_date_in_lead_events"], '%Y-%m-%d').date())
        if diagnostics["max_snapshot_date_in_identity_links"]:
            dates_to_consider.append(datetime.strptime(diagnostics["max_snapshot_date_in_identity_links"], '%Y-%m-%d').date())
        
        if dates_to_consider:
            max_processed = max(dates_to_consider)
            # Recomendar empezar desde el día siguiente al último procesado
            recommended = max_processed + timedelta(days=1)
            diagnostics["recommended_start_date"] = str(recommended)
        elif diagnostics["max_lead_date_in_table"]:
            # Si hay datos en la tabla pero no procesados, recomendar desde el inicio
            diagnostics["recommended_start_date"] = diagnostics["max_lead_date_in_table"]
        
        return diagnostics
    
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en diagnóstico: {str(e)}")


@router.post("/upload-csv", response_model=CabinetLeadsUploadResponse)
async def upload_cabinet_leads_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    skip_already_processed: bool = Query(True, description="Si True, solo procesa registros nuevos (basado en fechas ya procesadas)"),
    db: Session = Depends(get_db)
):
    """
    Sube un CSV de cabinet leads y opcionalmente procesa automáticamente.
    
    - **file**: Archivo CSV con columnas: external_id, lead_created_at, first_name, etc.
    - **auto_process**: Si True, ejecuta ingesta automáticamente después del upload
    - **skip_already_processed**: Si True, determina automáticamente qué fechas ya están procesadas y solo procesa las nuevas
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    
    try:
        # Leer contenido del archivo
        contents = await file.read()
        # Intentar UTF-8 con BOM primero, luego UTF-8 normal
        try:
            text_content = contents.decode('utf-8-sig')
        except UnicodeDecodeError:
            text_content = contents.decode('utf-8')
        
        csv_reader = csv.DictReader(io.StringIO(text_content))
        
        # Validar columnas requeridas
        required_columns = ['external_id', 'lead_created_at']
        reader_columns = csv_reader.fieldnames
        if not reader_columns:
            raise HTTPException(status_code=400, detail="CSV vacío o sin headers")
        
        missing_columns = [col for col in required_columns if col not in reader_columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Columnas faltantes: {', '.join(missing_columns)}"
            )
        
        # Determinar fecha de corte si skip_already_processed está activado
        date_cutoff = None
        if skip_already_processed:
            try:
                diagnostics = get_cabinet_leads_diagnostics(db)
                if diagnostics.get("recommended_start_date"):
                    date_cutoff = datetime.strptime(diagnostics["recommended_start_date"], '%Y-%m-%d').date()
                    logger.info(f"Usando fecha de corte: {date_cutoff} (solo procesar registros desde esta fecha)")
            except Exception as e:
                logger.warning(f"No se pudo determinar fecha de corte, procesando todo: {e}")
        
        # Procesar filas
        batch = []
        batch_size = 1000
        total_inserted = 0
        total_ignored = 0
        errors = []
        all_external_ids = []
        skipped_by_date = 0
        
        for row_num, row in enumerate(csv_reader, start=2):  # Empezar en 2 (header es 1)
            try:
                external_id = row.get('external_id')
                if external_id:
                    all_external_ids.append(external_id)
                
                # Si skip_already_processed está activado, filtrar por fecha
                lead_date_str = row.get('lead_created_at')
                if date_cutoff and lead_date_str:
                    try:
                        timestamp_val = parse_timestamp(lead_date_str)
                        if timestamp_val:
                            lead_date = timestamp_val.date() if isinstance(timestamp_val, datetime) else timestamp_val
                            if lead_date < date_cutoff:
                                skipped_by_date += 1
                                continue  # Saltar este registro, ya está procesado
                    except (ValueError, TypeError, AttributeError):
                        pass  # Si no se puede parsear la fecha, procesarlo de todas formas
                
                # Mapear valores
                record = {
                    'external_id': external_id or None,
                    'activation_city': row.get('activation_city') or None,
                    'active_1': parse_boolean(row.get('active_1')),
                    'active_5': parse_boolean(row.get('active_5')),
                    'active_10': parse_boolean(row.get('active_10')),
                    'active_15': parse_boolean(row.get('active_15')),
                    'active_25': parse_boolean(row.get('active_25')),
                    'active_50': parse_boolean(row.get('active_50')),
                    'active_100': parse_boolean(row.get('active_100')),
                    'asset_color': row.get('asset_color') or None,
                    'asset_model': row.get('asset_model') or None,
                    'asset_plate_number': row.get('asset_plate_number') or None,
                    'last_name': row.get('last_name') or None,
                    'first_name': row.get('first_name') or None,
                    'middle_name': row.get('middle_name') or None,
                    'last_active_date': parse_date(row.get('last_active_date')),
                    'lead_created_at': parse_timestamp(row.get('lead_created_at')),
                    'park_name': row.get('park_name') or None,
                    'park_phone': row.get('park_phone') or None,
                    'status': row.get('status') or None,
                    'tariff': row.get('tariff') or None,
                    'target_city': row.get('target_city') or None,
                }
                
                batch.append(record)
                
                # Insertar batch cuando alcance el tamaño
                if len(batch) >= batch_size:
                    inserted, ignored = insert_batch(db, batch)
                    total_inserted += inserted
                    total_ignored += ignored
                    batch = []
            
            except Exception as e:
                errors.append(f"Fila {row_num}: {str(e)}")
                logger.error(f"Error procesando fila {row_num}: {e}")
                continue
        
        # Insertar batch final
        if batch:
            inserted, ignored = insert_batch(db, batch)
            total_inserted += inserted
            total_ignored += ignored
        
        # Ejecutar procesamiento automático si está habilitado
        run_id = None
        if auto_process and total_inserted > 0:
            # Obtener rango de fechas del CSV para procesar solo lo nuevo
            date_from, date_to = get_date_range_from_csv(text_content)
            
            # Si skip_already_processed está activado, ajustar date_from
            if skip_already_processed and date_cutoff:
                if date_from and date_from < date_cutoff:
                    date_from = date_cutoff
                elif not date_from:
                    date_from = date_cutoff
            
            background_tasks.add_task(
                _process_ingestion_after_upload,
                date_from=date_from,
                date_to=date_to
            )
            logger.info(f"Procesamiento automático programado para background (date_from={date_from}, date_to={date_to})")
        
        return CabinetLeadsUploadResponse(
            status="success",
            message="CSV procesado exitosamente",
            stats={
                "total_inserted": total_inserted,
                "total_ignored": total_ignored,
                "total_rows": total_inserted + total_ignored,
                "skipped_by_date": skipped_by_date,
                "errors_count": len(errors),
                "auto_process": auto_process,
                "date_cutoff_used": str(date_cutoff) if date_cutoff else None
            },
            errors=errors[:10] if errors else [],  # Primeros 10 errores
            run_id=run_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando CSV: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error procesando CSV: {str(e)}")


def count_existing_external_ids(db: Session, external_ids: list) -> int:
    """Cuenta cuántos external_ids ya existen en la tabla"""
    if not external_ids:
        return 0
    
    try:
        query = text("""
            SELECT COUNT(*) 
            FROM public.module_ct_cabinet_leads 
            WHERE external_id = ANY(:external_ids)
        """)
        result = db.execute(query, {"external_ids": external_ids})
        count = result.scalar()
        return int(count) if count is not None else 0
    except Exception as e:
        logger.warning(f"Error contando external_ids existentes: {e}")
        return 0


def get_date_range_from_csv(csv_content: str) -> tuple[Optional[date], Optional[date]]:
    """Extrae el rango de fechas del CSV para optimizar el procesamiento"""
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        dates = []
        
        for row in csv_reader:
            lead_date_str = row.get('lead_created_at')
            if lead_date_str:
                    try:
                        timestamp_val = parse_timestamp(lead_date_str)
                        if timestamp_val:
                            # Convertir timestamp a date
                            if isinstance(timestamp_val, datetime):
                                date_val = timestamp_val.date()
                            elif isinstance(timestamp_val, date):
                                date_val = timestamp_val
                            else:
                                continue
                            dates.append(date_val)
                    except (ValueError, TypeError, AttributeError):
                        continue
        
        if dates:
            date_from = min(dates)
            date_to = max(dates)
            return date_from, date_to
        
        return None, None
    except Exception as e:
        logger.warning(f"Error extrayendo rango de fechas del CSV: {e}")
        return None, None


def ensure_unique_index_exists(db: Session):
    """Asegura que existe un constraint único en external_id para ON CONFLICT"""
    try:
        # Verificar si el constraint único existe usando pg_constraint
        check_constraint = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public'
                  AND t.relname = 'module_ct_cabinet_leads'
                  AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                  AND c.contype = 'u'
            )
        """))
        constraint_exists = check_constraint.scalar()
        
        if not constraint_exists:
            logger.info("Constraint único no existe. Creando constraint único en external_id...")
            # Crear constraint único (PostgreSQL permite múltiples NULLs en UNIQUE constraints)
            try:
                db.execute(text("""
                    ALTER TABLE public.module_ct_cabinet_leads
                    ADD CONSTRAINT uq_module_ct_cabinet_leads_external_id
                    UNIQUE (external_id)
                """))
                db.commit()
                logger.info("✅ Constraint único creado exitosamente")
                
                # Verificar que realmente se creó
                verify = db.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM pg_constraint c
                        JOIN pg_class t ON t.oid = c.conrelid
                        JOIN pg_namespace n ON n.oid = t.relnamespace
                        WHERE n.nspname = 'public'
                          AND t.relname = 'module_ct_cabinet_leads'
                          AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                          AND c.contype = 'u'
                    )
                """))
                if not verify.scalar():
                    raise Exception("Constraint no se creó correctamente después del ALTER TABLE")
            except Exception as create_error:
                error_msg = str(create_error)
                # Si el constraint ya existe, está bien
                if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                    logger.info("Constraint único ya existe (ignorando error)")
                    db.rollback()
                else:
                    logger.warning(f"Error creando constraint único: {create_error}")
                    db.rollback()
                    raise
        else:
            logger.debug("Constraint único ya existe")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error en ensure_unique_index_exists: {e}", exc_info=True)
        db.rollback()
        
        # Intentar crear índice único parcial como alternativa
        try:
            logger.info("Intentando crear índice único parcial como alternativa...")
            # Verificar si el índice ya existe
            check_index = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND tablename = 'module_ct_cabinet_leads'
                    AND indexname = 'idx_cabinet_leads_external_id_unique'
                )
            """))
            if not check_index.scalar():
                db.execute(text("""
                    CREATE UNIQUE INDEX idx_cabinet_leads_external_id_unique 
                    ON public.module_ct_cabinet_leads(external_id) 
                    WHERE external_id IS NOT NULL
                """))
                db.commit()
                logger.info("✅ Índice único parcial creado como alternativa")
            else:
                logger.info("Índice único parcial ya existe")
        except Exception as e2:
            logger.error(f"Error creando índice único parcial: {e2}", exc_info=True)
            db.rollback()
            # No lanzar excepción aquí, dejar que el INSERT falle y se maneje arriba


def insert_batch(db: Session, batch: list) -> tuple[int, int]:
    """Inserta un batch de registros usando ON CONFLICT DO NOTHING"""
    if not batch:
        return 0, 0
    
    # Asegurar que el índice único existe
    ensure_unique_index_exists(db)
    
    # Separar registros con y sin external_id
    batch_with_external_id = [r for r in batch if r.get('external_id')]
    batch_without_external_id = [r for r in batch if not r.get('external_id')]
    
    # Obtener external_ids del batch antes de insertar
    external_ids = [r.get('external_id') for r in batch_with_external_id]
    
    # Contar cuántos ya existen ANTES del insert
    existing_before = 0
    if external_ids:
        existing_before = count_existing_external_ids(db, external_ids)
    
    total_inserted = 0
    total_ignored = existing_before
    
    # Insertar registros con external_id usando ON CONFLICT
    if batch_with_external_id:
        # Verificar que el constraint existe antes de intentar INSERT
        verify_constraint = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'public'
                  AND t.relname = 'module_ct_cabinet_leads'
                  AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                  AND c.contype = 'u'
            )
        """))
        constraint_exists = verify_constraint.scalar()
        
        if not constraint_exists:
            logger.warning("Constraint único no existe. Intentando crearlo...")
            ensure_unique_index_exists(db)
            # Verificar nuevamente
            verify_again = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    WHERE n.nspname = 'public'
                      AND t.relname = 'module_ct_cabinet_leads'
                      AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
                      AND c.contype = 'u'
                )
            """))
            if not verify_again.scalar():
                # Si aún no existe, intentar con índice único parcial
                logger.warning("Constraint no se pudo crear. Intentando con índice único parcial...")
                try:
                    db.execute(text("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_cabinet_leads_external_id_unique 
                        ON public.module_ct_cabinet_leads(external_id) 
                        WHERE external_id IS NOT NULL
                    """))
                    db.commit()
                    logger.info("Índice único parcial creado")
                except Exception as idx_error:
                    logger.error(f"No se pudo crear ni constraint ni índice: {idx_error}")
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"No se pudo crear constraint único en external_id. "
                               f"Puede haber duplicados en la tabla. Error: {str(idx_error)}"
                    )
        
        insert_sql = text("""
            INSERT INTO public.module_ct_cabinet_leads (
                external_id, activation_city, active_1, active_5, active_10,
                active_15, active_25, active_50, active_100, asset_color, asset_model,
                asset_plate_number, last_name, first_name, middle_name,
                last_active_date, lead_created_at, park_name, park_phone,
                status, tariff, target_city
            ) VALUES (
                :external_id, :activation_city, :active_1, :active_5, :active_10,
                :active_15, :active_25, :active_50, :active_100, :asset_color, :asset_model,
                :asset_plate_number, :last_name, :first_name, :middle_name,
                :last_active_date, :lead_created_at, :park_name, :park_phone,
                :status, :tariff, :target_city
            )
            ON CONFLICT (external_id) DO NOTHING
        """)
        
        try:
            db.execute(insert_sql, batch_with_external_id)
            db.commit()
            
            # Calcular insertados vs ignorados para registros con external_id
            total_with_id = len(batch_with_external_id)
            inserted_with_id = total_with_id - existing_before
            total_inserted += inserted_with_id
        except Exception as e:
            db.rollback()
            error_msg = str(e).lower()
            logger.error(f"Error insertando batch con external_id: {e}")
            
            # Si falla por falta de constraint, intentar crearlo y reintentar
            if "no unique or exclusion constraint" in error_msg:
                logger.info("Constraint no encontrado en INSERT. Creando y reintentando...")
                ensure_unique_index_exists(db)
                try:
                    db.execute(insert_sql, batch_with_external_id)
                    db.commit()
                    inserted_with_id = total_with_id - existing_before
                    total_inserted += inserted_with_id
                except Exception as retry_error:
                    db.rollback()
                    logger.error(f"Error en reintento: {retry_error}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"No se pudo insertar datos. El constraint único no se pudo crear. "
                               f"Verifica que no haya duplicados en external_id. Error: {str(retry_error)}"
                    )
            else:
                raise
    
    # Insertar registros sin external_id (sin ON CONFLICT, ya que no hay clave única)
    if batch_without_external_id:
        insert_sql_no_id = text("""
            INSERT INTO public.module_ct_cabinet_leads (
                external_id, activation_city, active_1, active_5, active_10,
                active_15, active_25, active_50, active_100, asset_color, asset_model,
                asset_plate_number, last_name, first_name, middle_name,
                last_active_date, lead_created_at, park_name, park_phone,
                status, tariff, target_city
            ) VALUES (
                :external_id, :activation_city, :active_1, :active_5, :active_10,
                :active_15, :active_25, :active_50, :active_100, :asset_color, :asset_model,
                :asset_plate_number, :last_name, :first_name, :middle_name,
                :last_active_date, :lead_created_at, :park_name, :park_phone,
                :status, :tariff, :target_city
            )
        """)
        
        try:
            db.execute(insert_sql_no_id, batch_without_external_id)
            db.commit()
            total_inserted += len(batch_without_external_id)
        except Exception as e:
            db.rollback()
            logger.error(f"Error insertando batch sin external_id: {e}")
            raise
    
    return total_inserted, total_ignored


def _process_ingestion_after_upload(date_from: Optional[date] = None, date_to: Optional[date] = None):
    """Ejecuta procesamiento automático después del upload"""
    from datetime import date as date_type
    
    db = SessionLocal()
    try:
        logger.info(f"Iniciando procesamiento automático después de upload CSV (date_from={date_from}, date_to={date_to})")
        
        processor = CabinetLeadsProcessor(db)
        results = processor.process_all(
            date_from=date_from,
            date_to=date_to,
            refresh_index=True
        )
        
        logger.info(f"Procesamiento automático completado: {results}")
        
        if results.get("errors"):
            logger.warning(f"Errores durante procesamiento: {results['errors']}")
    
    except Exception as e:
        logger.error(f"Error en procesamiento automático: {e}", exc_info=True)
    finally:
        db.close()
