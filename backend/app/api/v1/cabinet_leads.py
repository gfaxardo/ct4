"""
Endpoint para upload y procesamiento de CSV de cabinet leads
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime, date
import csv
import io
import logging

from app.db import get_db, SessionLocal
from app.schemas.cabinet_leads import CabinetLeadsUploadResponse
from app.services.cabinet_leads_processor import CabinetLeadsProcessor

logger = logging.getLogger(__name__)
router = APIRouter()


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
            except:
                continue
        return None
    except:
        return None


def parse_date(value: str) -> Optional[date]:
    """Convierte string a date"""
    if not value or value.strip() == '':
        return None
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except:
        return None


@router.post("/upload-csv", response_model=CabinetLeadsUploadResponse)
async def upload_cabinet_leads_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    db: Session = Depends(get_db)
):
    """
    Sube un CSV de cabinet leads y opcionalmente procesa automáticamente.
    
    - **file**: Archivo CSV con columnas: external_id, lead_created_at, first_name, etc.
    - **auto_process**: Si True, ejecuta ingesta automáticamente después del upload
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    
    try:
        # Leer contenido del archivo
        contents = await file.read()
        # Intentar UTF-8 con BOM primero, luego UTF-8 normal
        try:
            text_content = contents.decode('utf-8-sig')
        except:
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
        
        # Procesar filas
        batch = []
        batch_size = 1000
        total_inserted = 0
        total_ignored = 0
        errors = []
        all_external_ids = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Empezar en 2 (header es 1)
            try:
                external_id = row.get('external_id')
                if external_id:
                    all_external_ids.append(external_id)
                
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
                "errors_count": len(errors),
                "auto_process": auto_process
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
                except:
                    continue
        
        if dates:
            date_from = min(dates)
            date_to = max(dates)
            return date_from, date_to
        
        return None, None
    except Exception as e:
        logger.warning(f"Error extrayendo rango de fechas del CSV: {e}")
        return None, None


def insert_batch(db: Session, batch: list) -> tuple[int, int]:
    """Inserta un batch de registros usando ON CONFLICT DO NOTHING"""
    if not batch:
        return 0, 0
    
    # Obtener external_ids del batch antes de insertar
    external_ids = [r.get('external_id') for r in batch if r.get('external_id')]
    
    # Contar cuántos ya existen ANTES del insert
    existing_before = 0
    if external_ids:
        existing_before = count_existing_external_ids(db, external_ids)
    
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
        db.execute(insert_sql, batch)
        db.commit()
        
        # Calcular insertados vs ignorados
        total_in_batch = len(batch)
        inserted = total_in_batch - existing_before
        ignored = existing_before
        
        return inserted, ignored
    except Exception as e:
        db.rollback()
        logger.error(f"Error insertando batch: {e}")
        raise


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

