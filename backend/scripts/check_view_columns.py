import sys
from pathlib import Path
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

engine = create_engine(settings.database_url)
conn = engine.connect()

result1 = conn.execute(text("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema='ops' 
    AND table_name='v_scout_payable_items_base' 
    ORDER BY ordinal_position
"""))

print("Columnas de ops.v_scout_payable_items_base:")
for row in result1:
    print(f"  - {row.column_name}")

print("\n" + "="*80 + "\n")

result2 = conn.execute(text("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema='ops' 
    AND table_name='v_scout_liquidation_open_items' 
    ORDER BY ordinal_position
"""))

print("Columnas de ops.v_scout_liquidation_open_items:")
for row in result2:
    print(f"  - {row.column_name}")

conn.close()

