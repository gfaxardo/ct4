#!/usr/bin/env python3
"""Script rápido para verificar el schema de module_ct_cabinet_payments"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Verificar si existe la tabla
        check_table = text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'module_ct_cabinet_payments'
            )
        """)
        exists = session.execute(check_table).scalar()
        print(f"Tabla module_ct_cabinet_payments existe: {exists}")
        
        if exists:
            # Obtener columnas
            columns_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                    AND table_name = 'module_ct_cabinet_payments'
                ORDER BY ordinal_position
            """)
            columns = session.execute(columns_query).fetchall()
            print("\nColumnas:")
            for col in columns:
                print(f"  {col.column_name:30s} {col.data_type:20s} {'NULL' if col.is_nullable == 'YES' else 'NOT NULL'}")
            
            # Verificar si tiene scout_id
            has_scout_id = any(col.column_name == 'scout_id' for col in columns)
            print(f"\nTiene scout_id: {has_scout_id}")
            
            # Verificar columnas de fecha
            date_cols = [col.column_name for col in columns if 'date' in col.column_name.lower() or 'at' in col.column_name.lower()]
            print(f"Columnas de fecha/timestamp: {date_cols}")
            
    finally:
        session.close()

if __name__ == "__main__":
    main()
