import json
import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def introspect_table(session, schema: str, table_name: str):
    query = text("""
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :table_name
        ORDER BY ordinal_position
    """)
    
    result = session.execute(query, {"schema": schema, "table_name": table_name})
    columns = []
    for row in result:
        columns.append({
            "column_name": row.column_name,
            "data_type": row.data_type,
            "is_nullable": row.is_nullable,
            "ordinal_position": row.ordinal_position
        })
    return columns

def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        tables = [
            ("public", "module_ct_cabinet_leads"),
            ("public", "module_ct_scouting_daily"),
            ("public", "drivers")
        ]
        
        introspection_result = {}
        
        for schema, table_name in tables:
            print(f"\n=== Introspección: {schema}.{table_name} ===")
            columns = introspect_table(session, schema, table_name)
            introspection_result[f"{schema}.{table_name}"] = columns
            
            print(f"Total columnas: {len(columns)}")
            for col in columns:
                nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                print(f"  {col['ordinal_position']:3d}. {col['column_name']:40s} {col['data_type']:20s} {nullable}")
        
        output_dir = Path(__file__).parent.parent.parent / "docs"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "schema_introspection.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(introspection_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n[OK] Resultados guardados en: {output_file}")
        return introspection_result
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()

