#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script idempotente para refrescar ops.mv_yango_cabinet_claims_for_collection

Registra cada refresh en ops.mv_refresh_log con el nuevo formato:
- refresh_started_at: inicio del refresh
- refresh_finished_at: fin del refresh (NULL si falla antes de terminar)
- status: RUNNING -> OK/ERROR
- rows_after_refresh: número de filas después del refresh
- host: hostname opcional
- meta: metadata adicional opcional

Uso:
    cd backend
    python scripts/refresh_yango_cabinet_claims_mv.py

O usando el comando:
    make refresh:yango-cabinet-claims
    # o
    poetry run python scripts/refresh_yango_cabinet_claims_mv.py
"""
import os
import sys
import time
import socket
from pathlib import Path
from datetime import datetime

# Agregar el directorio app al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.db import engine
    from sqlalchemy import text
except ImportError as e:
    print("ERROR: No se pueden importar los módulos necesarios.")
    print("   Asegúrate de:")
    print("   1. Estar en el directorio backend/")
    print("   2. Tener el entorno virtual activado")
    print("   3. Haber instalado las dependencias: pip install -r requirements.txt")
    print(f"\n   Error específico: {e}")
    sys.exit(1)

# Configuración
MV_NAME = "ops.mv_yango_cabinet_claims_for_collection"
SCHEMA_NAME = "ops"
MV_NAME_ONLY = "mv_yango_cabinet_claims_for_collection"

# Intentar usar CONCURRENTLY primero, fallback a normal si falla
USE_CONCURRENTLY = True


def get_hostname():
    """Obtiene el hostname del sistema."""
    try:
        return socket.gethostname()
    except:
        return None


def insert_refresh_log_start(conn, log_id: int, started_at: datetime, host: str = None):
    """Inserta registro inicial de refresh (status=RUNNING)."""
    try:
        conn.execute(text("""
            INSERT INTO ops.mv_refresh_log (
                id,
                schema_name,
                mv_name,
                refresh_started_at,
                status,
                host,
                refreshed_at  -- Mantener compatibilidad con estructura antigua
            )
            VALUES (
                :id,
                :schema_name,
                :mv_name,
                :refresh_started_at,
                'RUNNING',
                :host,
                :refreshed_at
            )
        """), {
            "id": log_id,
            "schema_name": SCHEMA_NAME,
            "mv_name": MV_NAME_ONLY,
            "refresh_started_at": started_at,
            "host": host,
            "refreshed_at": started_at  # Compatibilidad
        })
        conn.commit()
    except Exception as e:
        print(f"    [WARN] No se pudo insertar registro inicial en BD: {e}")
        conn.rollback()


def update_refresh_log_finish(
    conn, log_id: int, finished_at: datetime, status: str, 
    rows_after: int = None, error_message: str = None, duration_ms: int = None
):
    """Actualiza registro de refresh al finalizar (status=OK/ERROR)."""
    try:
        conn.execute(text("""
            UPDATE ops.mv_refresh_log
            SET refresh_finished_at = :finished_at,
                status = :status,
                rows_after_refresh = :rows_after,
                error_message = :error_message,
                duration_ms = :duration_ms,
                refreshed_at = :refreshed_at  -- Mantener compatibilidad
            WHERE id = :id
        """), {
            "id": log_id,
            "finished_at": finished_at,
            "status": status,
            "rows_after": rows_after,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "refreshed_at": finished_at  # Compatibilidad
        })
        conn.commit()
    except Exception as e:
        print(f"    [WARN] No se pudo actualizar registro final en BD: {e}")
        conn.rollback()


def get_rows_count(conn) -> int:
    """Obtiene el número de filas en la MV después del refresh."""
    try:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {MV_NAME}"))
        count = result.scalar()
        return int(count) if count is not None else None
    except Exception as e:
        print(f"    [WARN] No se pudo obtener conteo de filas: {e}")
        return None


def refresh_mv(conn, log_id: int, started_at: datetime, host: str = None):
    """
    Refresca la MV y actualiza el log.
    Retorna (success: bool, rows_after: int, error_message: str)
    """
    refresh_start_time = time.time()
    
    try:
        # Intentar CONCURRENTLY primero si está habilitado
        if USE_CONCURRENTLY:
            try:
                refresh_sql = f"REFRESH MATERIALIZED VIEW CONCURRENTLY {MV_NAME};"
                print(f"    Refrescando {MV_NAME} (CONCURRENTLY)...")
                conn.execute(text(refresh_sql))
                conn.commit()
                print(f"    [OK] Refresh CONCURRENTLY completado")
            except Exception as e:
                error_msg = str(e)
                if "concurrently" in error_msg.lower() or "unique index" in error_msg.lower():
                    print(f"    [WARN] CONCURRENTLY falló, intentando sin CONCURRENTLY...")
                    conn.rollback()
                    refresh_sql = f"REFRESH MATERIALIZED VIEW {MV_NAME};"
                    conn.execute(text(refresh_sql))
                    conn.commit()
                    print(f"    [OK] Refresh NORMAL completado (sin CONCURRENTLY)")
                else:
                    raise
        else:
            refresh_sql = f"REFRESH MATERIALIZED VIEW {MV_NAME};"
            print(f"    Refrescando {MV_NAME} (NORMAL)...")
            conn.execute(text(refresh_sql))
            conn.commit()
            print(f"    [OK] Refresh NORMAL completado")
        
        # Obtener conteo de filas
        rows_after = get_rows_count(conn)
        if rows_after is not None:
            print(f"    Filas después del refresh: {rows_after:,}")
        
        refresh_elapsed = time.time() - refresh_start_time
        duration_ms = int(refresh_elapsed * 1000)
        
        finished_at = datetime.now()
        
        # Actualizar log como OK
        update_refresh_log_finish(
            conn, log_id, finished_at, "OK", 
            rows_after=rows_after, 
            duration_ms=duration_ms
        )
        
        return (True, rows_after, None)
    
    except Exception as e:
        error_msg = str(e)
        refresh_elapsed = time.time() - refresh_start_time
        duration_ms = int(refresh_elapsed * 1000)
        
        finished_at = datetime.now()
        
        # Actualizar log como ERROR
        update_refresh_log_finish(
            conn, log_id, finished_at, "ERROR",
            error_message=error_msg,
            duration_ms=duration_ms
        )
        
        return (False, None, error_msg)


def main():
    """Función principal."""
    print("=" * 70)
    print("REFRESH DE MATERIALIZED VIEW - YANGO CABINET CLAIMS")
    print("=" * 70)
    print(f"MV: {MV_NAME}")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    started_at = datetime.now()
    host = get_hostname()
    
    # Obtener próximo ID para el log
    log_id = None
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COALESCE(MAX(id), 0) + 1 
                FROM ops.mv_refresh_log
            """))
            log_id = result.scalar()
    except Exception as e:
        print(f"[ERROR] No se pudo obtener ID para log: {e}")
        sys.exit(1)
    
    total_start = time.time()
    
    try:
        with engine.connect() as conn:
            # Insertar registro inicial (RUNNING)
            print(f"[{log_id}] Insertando registro inicial (status=RUNNING)...")
            insert_refresh_log_start(conn, log_id, started_at, host)
            
            # Refrescar MV
            print(f"[{log_id}] Iniciando refresh de {MV_NAME}...")
            success, rows_after, error_msg = refresh_mv(conn, log_id, started_at, host)
            
            total_elapsed = time.time() - total_start
            
            # Resumen
            print("\n" + "=" * 70)
            print("RESUMEN DE REFRESH")
            print("=" * 70)
            
            if success:
                print(f"  [OK] Refresh completado exitosamente")
                print(f"  Duración: {total_elapsed:.2f} segundos")
                if rows_after is not None:
                    print(f"  Filas después del refresh: {rows_after:,}")
                print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)
                sys.exit(0)
            else:
                print(f"  [ERROR] Refresh falló después de {total_elapsed:.2f} segundos")
                print(f"  Error: {error_msg}")
                print(f"  Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrumpido por el usuario (Ctrl+C)")
        
        # Marcar como ERROR si tenemos log_id
        if log_id:
            try:
                with engine.connect() as conn:
                    finished_at = datetime.now()
                    total_elapsed = time.time() - total_start
                    duration_ms = int(total_elapsed * 1000)
                    update_refresh_log_finish(
                        conn, log_id, finished_at, "ERROR",
                        error_message="Interrumpido por el usuario (Ctrl+C)",
                        duration_ms=duration_ms
                    )
            except:
                pass
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        
        # Marcar como ERROR si tenemos log_id
        if log_id:
            try:
                with engine.connect() as conn:
                    finished_at = datetime.now()
                    total_elapsed = time.time() - total_start
                    duration_ms = int(total_elapsed * 1000)
                    update_refresh_log_finish(
                        conn, log_id, finished_at, "ERROR",
                        error_message=str(e),
                        duration_ms=duration_ms
                    )
            except:
                pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()

