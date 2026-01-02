"""
DB Discovery: Registry de Fuentes
Ejecuta discovery_objects.sql y genera un CSV con los resultados.
"""
import sys
import io
import csv
from pathlib import Path
from sqlalchemy import create_engine, text

# Forzar UTF-8 en Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Leer el script SQL
sql_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_objects.sql"
with open(sql_file, "r", encoding="utf-8") as f:
    sql_query = f.read()

# Conectar a la base de datos
engine = create_engine(settings.database_url)
conn = engine.connect()

try:
    # Ejecutar la consulta
    result = conn.execute(text(sql_query))
    
    # Obtener los nombres de las columnas
    columns = result.keys()
    
    # Generar CSV
    output_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_objects.csv"
    row_count = 0
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Escribir encabezados
        writer.writerow(columns)
        # Escribir datos
        for row in result:
            writer.writerow(row)
            row_count += 1
    
    print(f"[OK] Discovery completado. Resultados guardados en: {output_file}")
    print(f"  Total de objetos encontrados: {row_count}")
    
except Exception as e:
    print(f"[ERROR] Error ejecutando discovery: {e}")
    sys.exit(1)
finally:
    conn.close()

