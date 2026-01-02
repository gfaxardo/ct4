"""
DB Discovery: Dependencias entre Objetos
Ejecuta discovery_dependencies.sql y genera un CSV con los resultados.
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
sql_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_dependencies.sql"
with open(sql_file, "r", encoding="utf-8") as f:
    sql_content = f.read()
    
    # Extraer solo la query (antes de la sección de comandos)
    # Buscar el marcador de comandos
    cmd_marker = "-- ============================================================================\n-- COMANDOS"
    if cmd_marker in sql_content:
        sql_query = sql_content.split(cmd_marker)[0].strip()
    else:
        # Si no hay marcador, usar todo el contenido
        sql_query = sql_content.strip()
    
    # Remover comentarios SQL (líneas que empiezan con --)
    lines = sql_query.split("\n")
    sql_lines = []
    for line in lines:
        stripped = line.strip()
        # Mantener líneas vacías y líneas que no son comentarios
        if not stripped or not stripped.startswith("--"):
            sql_lines.append(line)
    
    sql_query = "\n".join(sql_lines).strip()
    
    # Verificar que tenemos una query válida
    if not sql_query or ("SELECT" not in sql_query.upper() and "WITH" not in sql_query.upper()):
        raise ValueError("No se pudo extraer una query válida del archivo SQL")

# Conectar a la base de datos
engine = create_engine(settings.database_url)
conn = engine.connect()

try:
    # Ejecutar la consulta
    result = conn.execute(text(sql_query))
    
    # Obtener los nombres de las columnas
    columns = result.keys()
    
    # Generar CSV
    output_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_dependencies.csv"
    row_count = 0
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Escribir encabezados
        writer.writerow(columns)
        # Escribir datos
        for row in result:
            writer.writerow(row)
            row_count += 1
    
    print(f"[OK] Discovery de dependencias completado. Resultados guardados en: {output_file}")
    print(f"  Total de dependencias encontradas: {row_count}")
    
except Exception as e:
    print(f"[ERROR] Error ejecutando discovery de dependencias: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    conn.close()

