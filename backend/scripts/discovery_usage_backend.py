"""
Discovery de Uso de Objetos DB en el Repositorio
Escanear backend/**/*.py y backend/sql/**/*.sql para detectar referencias a objetos DB.
Validar contra catálogo DB y agrupar por endpoint/script.
"""
import sys
import io
import re
import json
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from sqlalchemy import create_engine, text

# Forzar UTF-8 en Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Patrones regex para detectar objetos DB
OBJECT_PATTERNS = [
    # FROM schema.table, JOIN schema.table
    r'\bFROM\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)',
    r'\bJOIN\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)',
    # schema.table en queries SQL
    r'\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)',
    # text("SELECT * FROM schema.table")
    r'text\(["\']([^"\']*)["\']\)',
    # execute("SELECT * FROM schema.table")
    r'execute\(["\']([^"\']*)["\']\)',
]

# Schemas conocidos
KNOWN_SCHEMAS = ['public', 'ops', 'canon', 'raw', 'observational']

# Endpoint patterns
ENDPOINT_PATTERN = re.compile(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']')


def extract_endpoint_path(file_path: Path, content: str) -> str:
    """Extrae el path del endpoint desde el archivo."""
    # Buscar router prefix desde imports o definición
    prefix_match = re.search(r'router\s*=\s*APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)["\']', content)
    prefix = prefix_match.group(1) if prefix_match else ""
    
    # Buscar include_router con prefix
    include_match = re.search(r'include_router\([^,]+,\s*prefix\s*=\s*["\']([^"\']+)["\']', content)
    if include_match:
        prefix = include_match.group(1)
    
    # Si no hay prefix explícito, inferir desde estructura de archivos
    if not prefix:
        if 'app/api/v1' in str(file_path):
            prefix = "/api/v1"
        elif 'app/api' in str(file_path):
            prefix = "/api"
        else:
            prefix = ""
    
    # Buscar primer endpoint decorator
    endpoint_match = ENDPOINT_PATTERN.search(content)
    if endpoint_match:
        method, path = endpoint_match.groups()
        return f"{prefix}{path}"
    
    return None


def find_db_objects_in_content(content: str) -> set:
    """Encuentra referencias a objetos DB en el contenido."""
    objects = set()
    
    # Buscar patrones directos schema.table
    for pattern in OBJECT_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                schema = match.group(1).lower()
                table = match.group(2).lower()
                if schema in KNOWN_SCHEMAS:
                    objects.add((schema, table))
            elif len(match.groups()) == 1:
                # Patrón text() o execute() - buscar dentro del SQL
                sql_content = match.group(1)
                # Buscar schema.table dentro del SQL
                sql_matches = re.finditer(
                    r'\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)',
                    sql_content,
                    re.IGNORECASE
                )
                for sql_match in sql_matches:
                    schema = sql_match.group(1).lower()
                    table = sql_match.group(2).lower()
                    if schema in KNOWN_SCHEMAS:
                        objects.add((schema, table))
    
    return objects


def validate_objects_against_db(engine, objects: set) -> dict:
    """Valida que los objetos existan en la base de datos."""
    valid_objects = {}
    
    if not objects:
        return valid_objects
    
    # Construir query para verificar existencia
    with engine.connect() as conn:
        for schema, obj_name in objects:
            try:
                result = conn.execute(text("""
                    SELECT 
                        n.nspname AS schema_name,
                        c.relname AS object_name,
                        CASE 
                            WHEN c.relkind = 'r' THEN 'table'
                            WHEN c.relkind = 'v' THEN 'view'
                            WHEN c.relkind = 'm' THEN 'matview'
                            ELSE 'other'
                        END AS object_type
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = :schema_name
                        AND c.relname = :object_name
                        AND c.relkind IN ('r', 'v', 'm')
                """), {
                    "schema_name": schema,
                    "object_name": obj_name
                })
                row = result.fetchone()
                if row:
                    valid_objects[(schema, obj_name)] = {
                        "schema_name": row[0],
                        "object_name": row[1],
                        "object_type": row[2]
                    }
            except Exception as e:
                # Silenciar errores de validación individual
                pass
    
    return valid_objects


def scan_backend_files(backend_path: Path) -> dict:
    """Escanea archivos .py y .sql en backend."""
    usage_data = defaultdict(lambda: {
        "schema_name": None,
        "object_name": None,
        "usage_context": set(),  # 'endpoint', 'script', 'both'
        "usage_locations": []
    })
    
    # Escanear archivos Python
    for py_file in backend_path.rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8")
            objects = find_db_objects_in_content(content)
            
            # Determinar contexto
            is_endpoint = "app/api" in str(py_file) and "@router" in content
            is_script = "scripts" in str(py_file)
            
            endpoint_path = None
            if is_endpoint:
                endpoint_path = extract_endpoint_path(py_file, content)
            
            for schema, obj_name in objects:
                key = (schema, obj_name)
                if key not in usage_data:
                    usage_data[key] = {
                        "schema_name": schema,
                        "object_name": obj_name,
                        "usage_context": set(),
                        "usage_locations": []
                    }
                
                if is_endpoint:
                    usage_data[key]["usage_context"].add("endpoint")
                    usage_data[key]["usage_locations"].append({
                        "file": str(py_file.relative_to(backend_path)),
                        "type": "endpoint",
                        "endpoint_path": endpoint_path
                    })
                elif is_script:
                    usage_data[key]["usage_context"].add("script")
                    usage_data[key]["usage_locations"].append({
                        "file": str(py_file.relative_to(backend_path)),
                        "type": "script"
                    })
                else:
                    usage_data[key]["usage_context"].add("script")  # Default para otros archivos
                    usage_data[key]["usage_locations"].append({
                        "file": str(py_file.relative_to(backend_path)),
                        "type": "other"
                    })
        except Exception as e:
            print(f"  [WARN] Error procesando {py_file}: {e}")
    
    # Escanear archivos SQL
    sql_path = backend_path / "sql"
    if sql_path.exists():
        for sql_file in sql_path.rglob("*.sql"):
            try:
                content = sql_file.read_text(encoding="utf-8")
                objects = find_db_objects_in_content(content)
                
                for schema, obj_name in objects:
                    key = (schema, obj_name)
                    if key not in usage_data:
                        usage_data[key] = {
                            "schema_name": schema,
                            "object_name": obj_name,
                            "usage_context": set(),
                            "usage_locations": []
                        }
                    
                    usage_data[key]["usage_context"].add("script")
                    usage_data[key]["usage_locations"].append({
                        "file": str(sql_file.relative_to(backend_path)),
                        "type": "sql"
                    })
            except Exception as e:
                print(f"  [WARN] Error procesando {sql_file}: {e}")
    
    return usage_data


def main():
    backend_path = Path(__file__).parent.parent
    
    print("=" * 70)
    print("DISCOVERY DE USO DE OBJETOS DB EN REPOSITORIO")
    print("=" * 70)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Escanear archivos
    print("Escaneando archivos .py y .sql...")
    usage_data = scan_backend_files(backend_path)
    print(f"  Objetos detectados (sin validar): {len(usage_data)}")
    
    # Validar contra DB
    print("\nValidando objetos contra catálogo DB...")
    engine = create_engine(settings.database_url)
    all_objects = set(usage_data.keys())
    valid_objects = validate_objects_against_db(engine, all_objects)
    
    # Filtrar solo objetos válidos
    valid_usage_data = {}
    for key, data in usage_data.items():
        if key in valid_objects:
            obj_info = valid_objects[key]
            valid_usage_data[key] = {
                **data,
                "object_type": obj_info["object_type"]
            }
    
    print(f"  Objetos válidos: {len(valid_usage_data)}")
    
    # Generar CSV
    output_file = backend_path / "sql" / "ops" / "discovery_usage_backend.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "schema_name", "object_name", "object_type",
            "usage_context", "usage_locations", "discovered_at"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for key, data in valid_usage_data.items():
            usage_context_str = ",".join(sorted(data["usage_context"]))
            if not usage_context_str:
                usage_context_str = "script"  # Default
            
            writer.writerow({
                "schema_name": data["schema_name"],
                "object_name": data["object_name"],
                "object_type": data.get("object_type", "unknown"),
                "usage_context": usage_context_str,
                "usage_locations": json.dumps(data["usage_locations"], ensure_ascii=False),
                "discovered_at": datetime.now().isoformat()
            })
    
    print(f"\n[OK] Discovery completado. Resultados guardados en: {output_file}")
    print(f"  Total de objetos usados: {len(valid_usage_data)}")
    
    # Resumen por contexto
    endpoint_count = sum(1 for d in valid_usage_data.values() if "endpoint" in d["usage_context"])
    script_count = sum(1 for d in valid_usage_data.values() if "script" in d["usage_context"])
    both_count = sum(1 for d in valid_usage_data.values() if len(d["usage_context"]) > 1)
    
    print(f"\nResumen:")
    print(f"  Usados en endpoints: {endpoint_count}")
    print(f"  Usados en scripts: {script_count}")
    print(f"  Usados en ambos: {both_count}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Error ejecutando discovery: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

