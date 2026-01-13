"""Script temporal para verificar estado de la tabla driver_orphan_quarantine"""
from sqlalchemy import text
from app.db import SessionLocal

db = SessionLocal()

try:
    # Verificar si la tabla existe
    result = db.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'canon' 
        AND table_name = 'driver_orphan_quarantine'
    """))
    table_exists = result.fetchone() is not None
    print(f"[OK] Tabla driver_orphan_quarantine existe: {table_exists}")
    
    # Verificar tipos ENUM
    result = db.execute(text("""
        SELECT typname 
        FROM pg_type 
        WHERE typname IN ('orphan_detected_reason', 'orphan_status')
        ORDER BY typname
    """))
    enums = [row[0] for row in result.fetchall()]
    print(f"[OK] Tipos ENUM existentes: {enums}")
    
    # Verificar específicamente cada tipo
    for enum_name in ['orphan_detected_reason', 'orphan_status']:
        result = db.execute(text(f"SELECT 1 FROM pg_type WHERE typname = '{enum_name}'"))
        exists = result.fetchone() is not None
        print(f"  - {enum_name}: {'EXISTE' if exists else 'NO EXISTE'}")
    
    # Verificar versión actual de Alembic
    result = db.execute(text("""
        SELECT version_num 
        FROM alembic_version
    """))
    row = result.fetchone()
    current_version = row[0] if row else None
    print(f"[OK] Version actual de Alembic: {current_version}")
    
    if table_exists:
        # Contar registros
        result = db.execute(text("SELECT COUNT(*) FROM canon.driver_orphan_quarantine"))
        count = result.fetchone()[0]
        print(f"[OK] Registros en quarantine: {count}")
        
finally:
    db.close()

