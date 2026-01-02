#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script oficial para refrescar Materialized Views de Yego/Yango Cabinet Cobranza.

Ejecuta los REFRESH en orden canónico:
1) mv_yango_payments_raw_current (CONCURRENTLY)
2) mv_yango_payments_ledger_latest (CONCURRENTLY)
3) mv_yango_payments_ledger_latest_enriched (CONCURRENTLY)
4) mv_yango_receivable_payable_detail (CONCURRENTLY)
5) mv_claims_payment_status_cabinet (CONCURRENTLY)
6) mv_yango_cabinet_claims_for_collection (CONCURRENTLY)

Uso:
    cd backend
    python scripts/refresh_ops_mvs.py

O usando el comando:
    make refresh:mvs
    # o
    poetry run python scripts/refresh_ops_mvs.py
"""
import os
import sys
import time
import uuid
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

# Orden canónico de refresh
MVS_REFRESH_ORDER = [
    {
        "name": "ops.mv_yango_payments_raw_current",
        "concurrently": True,
        "description": "Pagos raw actuales"
    },
    {
        "name": "ops.mv_yango_payments_ledger_latest",
        "concurrently": True,
        "description": "Ledger de pagos más reciente"
    },
    {
        "name": "ops.mv_yango_payments_ledger_latest_enriched",
        "concurrently": True,
        "description": "Ledger enriquecido con identidad"
    },
    {
        "name": "ops.mv_yango_receivable_payable_detail",
        "concurrently": True,  # Ahora soporta CONCURRENTLY gracias al índice único ux_mv_yango_receivable_payable_detail
        "description": "Detalle de receivables y payables"
    },
    {
        "name": "ops.mv_claims_payment_status_cabinet",
        "concurrently": True,
        "description": "Claims cabinet con estado de pago"
    },
    {
        "name": "ops.mv_yango_cabinet_claims_for_collection",
        "concurrently": True,
        "description": "Claims cabinet para cobranza"
    },
]


def log_step(conn, run_id: str, step_name: str, step_started_at: datetime, step_finished_at: datetime, step_status: str, error_message: str = None):
    """Loggea un step del refresh en la tabla ops.refresh_runs"""
    try:
        conn.execute(text("""
            UPDATE ops.refresh_runs
            SET step_name = :step_name,
                step_started_at = :step_started_at,
                step_finished_at = :step_finished_at,
                step_status = :step_status,
                error_message = :error_message
            WHERE run_id = :run_id
        """), {
            "run_id": run_id,
            "step_name": step_name,
            "step_started_at": step_started_at,
            "step_finished_at": step_finished_at,
            "step_status": step_status,
            "error_message": error_message
        })
        conn.commit()
    except Exception as e:
        print(f"    [WARN] No se pudo loggear step en BD: {e}")


def log_mv_refresh(conn, schema_name: str, mv_name: str, status: str, duration_ms: int, error_message: str = None):
    """Loggea un refresh de MV en la tabla ops.mv_refresh_log"""
    try:
        conn.execute(text("""
            INSERT INTO ops.mv_refresh_log (schema_name, mv_name, status, duration_ms, error_message)
            VALUES (:schema_name, :mv_name, :status, :duration_ms, :error_message)
        """), {
            "schema_name": schema_name,
            "mv_name": mv_name,
            "status": status,
            "duration_ms": duration_ms,
            "error_message": error_message
        })
        conn.commit()
    except Exception as e:
        print(f"    [WARN] No se pudo loggear refresh en ops.mv_refresh_log: {e}")


def refresh_mv(mv_name: str, concurrently: bool = True, run_id: str = None, conn=None):
    """
    Refresca una vista materializada y retorna (success, elapsed_time, error_message)
    Si se proporciona run_id y conn, loggea el step en la BD
    También loggea en ops.mv_refresh_log
    """
    start_time = time.time()
    step_started_at = datetime.now()
    
    # Extraer schema_name y mv_name del nombre completo
    if '.' in mv_name:
        schema_name, mv_name_only = mv_name.split('.', 1)
    else:
        schema_name = 'public'
        mv_name_only = mv_name
    
    try:
        if conn is None:
            conn = engine.connect()
            should_close = True
        else:
            should_close = False
        
        try:
            if concurrently:
                refresh_sql = f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv_name};"
            else:
                refresh_sql = f"REFRESH MATERIALIZED VIEW {mv_name};"
            
            conn.execute(text(refresh_sql))
            conn.commit()
            
            elapsed = time.time() - start_time
            elapsed_ms = int(elapsed * 1000)
            step_finished_at = datetime.now()
            
            # Loggear en ops.mv_refresh_log
            log_mv_refresh(conn, schema_name, mv_name_only, 'SUCCESS', elapsed_ms, None)
            
            if run_id:
                log_step(conn, run_id, mv_name, step_started_at, step_finished_at, "SUCCESS")
            
            if should_close:
                conn.close()
            
            return (True, elapsed, "")
        
        except Exception as e:
            error_msg = str(e)
            elapsed = time.time() - start_time
            elapsed_ms = int(elapsed * 1000)
            
            # Si CONCURRENTLY falla, intentar sin CONCURRENTLY (solo si estaba habilitado)
            if concurrently and ("concurrently" in error_msg.lower() or "unique index" in error_msg.lower()):
                print(f"    [WARN] CONCURRENTLY falló, intentando sin CONCURRENTLY...")
                try:
                    # Hacer rollback de la transacción abortada antes de intentar de nuevo
                    conn.rollback()
                    
                    start_time = time.time()
                    refresh_sql = f"REFRESH MATERIALIZED VIEW {mv_name};"
                    conn.execute(text(refresh_sql))
                    conn.commit()
                    elapsed = time.time() - start_time
                    elapsed_ms = int(elapsed * 1000)
                    step_finished_at = datetime.now()
                    
                    # Loggear en ops.mv_refresh_log (SUCCESS después del retry)
                    log_mv_refresh(conn, schema_name, mv_name_only, 'SUCCESS', elapsed_ms, None)
                    
                    if run_id:
                        log_step(conn, run_id, mv_name, step_started_at, step_finished_at, "SUCCESS")
                    
                    if should_close:
                        conn.close()
                    
                    return (True, elapsed, "")
                except Exception as e2:
                    # Rollback también en caso de error
                    try:
                        conn.rollback()
                    except:
                        pass
                    
                    elapsed = time.time() - start_time
                    elapsed_ms = int(elapsed * 1000)
                    step_finished_at = datetime.now()
                    
                    # Loggear en ops.mv_refresh_log (FAILED)
                    log_mv_refresh(conn, schema_name, mv_name_only, 'FAILED', elapsed_ms, str(e2))
                    
                    if run_id:
                        log_step(conn, run_id, mv_name, step_started_at, step_finished_at, "FAIL", str(e2))
                    if should_close:
                        conn.close()
                    return (False, elapsed, str(e2))
            
            # Si no es error de CONCURRENTLY, hacer rollback y retornar error
            try:
                conn.rollback()
            except:
                pass
            
            step_finished_at = datetime.now()
            
            # Loggear en ops.mv_refresh_log (FAILED)
            log_mv_refresh(conn, schema_name, mv_name_only, 'FAILED', elapsed_ms, error_msg)
            
            if run_id:
                log_step(conn, run_id, mv_name, step_started_at, step_finished_at, "FAIL", error_msg)
            
            if should_close:
                conn.close()
            
            return (False, elapsed, error_msg)
    
    except Exception as e:
        # Error al conectar o loggear
        elapsed = time.time() - start_time
        elapsed_ms = int(elapsed * 1000)
        
        # Intentar loggear el error de conexión si tenemos conn
        if conn:
            try:
                log_mv_refresh(conn, schema_name, mv_name_only, 'FAILED', elapsed_ms, str(e))
            except:
                pass
        
        return (False, elapsed, str(e))


def main():
    print("=" * 70)
    print("REFRESH DE MATERIALIZED VIEWS - YEGO/YANGO CABINET COBRANZA")
    print("=" * 70)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total de MVs a refrescar: {len(MVS_REFRESH_ORDER)}")
    print("NOTA: Esto puede tomar varios minutos dependiendo del tamaño de los datos.\n")
    
    # Crear run_id y loggear inicio
    run_id = str(uuid.uuid4())
    started_at = datetime.now()
    
    # Intentar crear registro en BD (opcional, no crítico)
    try:
        with engine.connect() as conn:
            # Verificar si la tabla existe
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'ops' 
                    AND table_name = 'refresh_runs'
                )
            """))
            table_exists = table_check.fetchone()[0]
            
            if table_exists:
                conn.execute(text("""
                    INSERT INTO ops.refresh_runs (run_id, started_at, status)
                    VALUES (:run_id, :started_at, 'RUNNING')
                """), {
                    "run_id": run_id,
                    "started_at": started_at
                })
                conn.commit()
            else:
                print(f"[INFO] Tabla ops.refresh_runs no existe. Ejecutar migración: alembic upgrade head")
                print("   Continuando sin logging en BD...")
                run_id = None
    except Exception as e:
        print(f"[WARN] No se pudo crear registro de run en BD: {e}")
        print("   Continuando sin logging en BD...")
        run_id = None
    
    total_start = time.time()
    results = []
    conn = None
    
    try:
        # Mantener una conexión abierta para logging
        if run_id:
            try:
                conn = engine.connect()
            except Exception as e:
                print(f"[WARN] No se pudo mantener conexión para logging: {e}")
                conn = None
        
        for idx, mv_config in enumerate(MVS_REFRESH_ORDER, 1):
            mv_name = mv_config["name"]
            concurrently = mv_config["concurrently"]
            description = mv_config["description"]
            
            mode_str = "CONCURRENTLY" if concurrently else "NORMAL"
            print(f"[{idx}/{len(MVS_REFRESH_ORDER)}] Refrescando {mv_name} ({mode_str})...")
            print(f"         Descripción: {description}")
            print(f"         Inicio: {datetime.now().strftime('%H:%M:%S')}", end=" ", flush=True)
            
            success, elapsed, error_msg = refresh_mv(mv_name, concurrently, run_id=run_id, conn=conn)
            
            if success:
                print(f"[OK] Completado en {elapsed:.2f}s")
                results.append({
                    "mv": mv_name,
                    "success": True,
                    "elapsed": elapsed,
                    "description": description
                })
            else:
                print(f"[ERROR] ERROR después de {elapsed:.2f}s")
                print(f"         Error: {error_msg}")
                results.append({
                    "mv": mv_name,
                    "success": False,
                    "elapsed": elapsed,
                    "error": error_msg,
                    "description": description
                })
                # Si falla, continuar con las siguientes pero marcar como fallido
                print(f"         Continuando con las siguientes MVs...")
            
            print()
        
        total_elapsed = time.time() - total_start
        
        # Resumen
        print("=" * 70)
        print("RESUMEN DE REFRESH")
        print("=" * 70)
        
        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count
        
        for result in results:
            status = "[OK]" if result["success"] else "[ERROR]"
            print(f"  {status:8} {result['mv']:50} {result['elapsed']:>8.2f}s")
            if not result["success"]:
                print(f"           Error: {result.get('error', 'Unknown error')}")
        
        print("=" * 70)
        print(f"Total: {total_elapsed:.2f} segundos")
        print(f"Exitosos: {success_count}/{len(results)}")
        print(f"Fallidos: {failed_count}/{len(results)}")
        print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Actualizar run final
        finished_at = datetime.now()
        final_status = "SUCCESS" if failed_count == 0 else "FAIL"
        
        if run_id:
            try:
                if conn:
                    conn.execute(text("""
                        UPDATE ops.refresh_runs
                        SET finished_at = :finished_at,
                            status = :status
                        WHERE run_id = :run_id
                    """), {
                        "run_id": run_id,
                        "finished_at": finished_at,
                        "status": final_status
                    })
                    conn.commit()
                else:
                    with engine.connect() as conn2:
                        conn2.execute(text("""
                            UPDATE ops.refresh_runs
                            SET finished_at = :finished_at,
                                status = :status
                            WHERE run_id = :run_id
                        """), {
                            "run_id": run_id,
                            "finished_at": finished_at,
                            "status": final_status
                        })
                        conn2.commit()
            except Exception as e:
                print(f"[WARN] No se pudo actualizar estado final en BD: {e}")
        
        if conn:
            conn.close()
        
        # Exit code basado en si hubo errores
        if failed_count > 0:
            print("\n[WARN] ADVERTENCIA: Algunas MVs fallaron al refrescar.")
            print("   Revisa los errores arriba y verifica la base de datos.")
            sys.exit(1)
        else:
            print("\n[OK] Todas las MVs se refrescaron exitosamente.")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrumpido por el usuario (Ctrl+C)")
        print("   Algunas MVs pueden haber quedado en estado inconsistente.")
        
        # Marcar run como FAIL
        if run_id:
            try:
                if conn:
                    conn.execute(text("""
                        UPDATE ops.refresh_runs
                        SET finished_at = NOW(),
                            status = 'FAIL',
                            error_message = 'Interrumpido por el usuario (Ctrl+C)'
                        WHERE run_id = :run_id
                    """), {"run_id": run_id})
                    conn.commit()
                    conn.close()
                else:
                    with engine.connect() as conn2:
                        conn2.execute(text("""
                            UPDATE ops.refresh_runs
                            SET finished_at = NOW(),
                                status = 'FAIL',
                                error_message = 'Interrumpido por el usuario (Ctrl+C)'
                            WHERE run_id = :run_id
                        """), {"run_id": run_id})
                        conn2.commit()
            except Exception:
                pass
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n[ERROR] ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        
        # Marcar run como FAIL
        if run_id:
            try:
                if conn:
                    conn.execute(text("""
                        UPDATE ops.refresh_runs
                        SET finished_at = NOW(),
                            status = 'FAIL',
                            error_message = :error_message
                        WHERE run_id = :run_id
                    """), {
                        "run_id": run_id,
                        "error_message": str(e)
                    })
                    conn.commit()
                    conn.close()
                else:
                    with engine.connect() as conn2:
                        conn2.execute(text("""
                            UPDATE ops.refresh_runs
                            SET finished_at = NOW(),
                                status = 'FAIL',
                                error_message = :error_message
                            WHERE run_id = :run_id
                        """), {
                            "run_id": run_id,
                            "error_message": str(e)
                        })
                        conn2.commit()
            except Exception:
                pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()

