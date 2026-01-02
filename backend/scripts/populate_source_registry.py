"""
Poblar Source Registry desde Discovery Scripts
Ejecuta UPSERT idempotente respetando overrides manuales.
"""
import sys
import json
import csv
import io
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from sqlalchemy import create_engine, text

# Forzar UTF-8 en Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# MVs críticas desde refresh_ops_mvs.py
CRITICAL_MVS = [
    "ops.mv_yango_payments_raw_current",
    "ops.mv_yango_payments_ledger_latest",
    "ops.mv_yango_payments_ledger_latest_enriched",
    "ops.mv_yango_receivable_payable_detail",
    "ops.mv_claims_payment_status_cabinet",
    "ops.mv_yango_cabinet_claims_for_collection",
]

# Objetos críticos desde endpoints UI-ready (del contrato)
CRITICAL_OBJECTS_FROM_ENDPOINTS = [
    # Vistas críticas
    ("ops", "v_scout_liquidation_open_items_payable_policy"),
    ("ops", "v_scout_liquidation_open_items_enriched"),
    ("ops", "v_yango_receivable_payable"),
    ("ops", "v_yango_receivable_payable_detail"),
    ("ops", "v_payment_calculation"),
    ("ops", "v_yango_payments_claims_cabinet_14d"),
    ("ops", "v_yango_payments_ledger_latest_enriched"),
    # Tablas canónicas
    ("canon", "identity_registry"),
    ("canon", "identity_links"),
    ("canon", "identity_unmatched"),
    ("canon", "drivers_index"),
    # Observational
    ("observational", "lead_events"),
    ("observational", "lead_ledger"),
    ("observational", "scouting_match_candidates"),
    # Public
    ("public", "module_ct_scouting_daily"),
    ("public", "module_ct_cabinet_leads"),
    ("public", "module_ct_migrations"),
    ("public", "drivers"),
]


def infer_layer(schema_name: str, object_type: str) -> str:
    """Infiere layer desde schema y tipo."""
    if schema_name == "raw":
        return "RAW"
    elif schema_name == "canon":
        return "CANON"
    elif object_type == "matview":
        return "MV"
    else:
        return "DERIVED"


def infer_role(schema_name: str, object_type: str, layer: str) -> str:
    """Infiere role desde schema, tipo y layer."""
    if layer in ("RAW", "CANON"):
        return "PRIMARY"
    elif layer == "MV":
        return "SECONDARY"
    else:  # DERIVED
        return "SECONDARY"


def infer_criticality(
    schema_name: str,
    object_name: str,
    object_type: str,
    usage_context: str,
    full_name: str,
    dependencies: dict = None
) -> str:
    """Infiere criticality desde uso y contexto."""
    # MV en refresh_ops_mvs.py => critical
    if full_name in CRITICAL_MVS:
        return "critical"
    
    # Objeto en lista de críticos desde endpoints
    if (schema_name, object_name) in CRITICAL_OBJECTS_FROM_ENDPOINTS:
        return "critical"
    
    # Usado por endpoint => critical (según requerimiento)
    if usage_context and "endpoint" in usage_context:
        return "critical"
    
    return "normal"


def propagate_criticality(registry_data: dict, dependencies: dict) -> dict:
    """Propaga criticidad: RAW que alimenta MV crítica → critical.
    
    dependencies: {child_key: [parent1, parent2, ...]}
    Si una MV es crítica, sus parents (especialmente RAW) se vuelven critical.
    """
    # Primera pasada: identificar MVs críticas
    critical_mvs = set()
    for key, data in registry_data.items():
        if data.get("criticality") == "critical" and data.get("object_type") == "matview":
            critical_mvs.add(key)
    
    # Segunda pasada: para cada MV crítica, marcar sus parents como critical si son RAW
    for mv_key in critical_mvs:
        # dependencies[mv_key] contiene los parents de esta MV
        parents = dependencies.get(mv_key, [])
        for parent in parents:
            parent_key = (parent["schema"], parent["name"])
            if parent_key in registry_data:
                parent_data = registry_data[parent_key]
                # Si el parent es RAW y alimenta MV crítica, se vuelve critical
                if parent_data.get("layer") == "RAW" and parent_data.get("criticality") != "critical":
                    parent_data["criticality"] = "critical"
    
    return registry_data


def load_discovery_objects(backend_path: Path) -> dict:
    """Carga discovery_objects.csv."""
    objects = {}
    csv_file = backend_path / "sql" / "ops" / "discovery_objects.csv"
    
    if not csv_file.exists():
        print(f"  [WARN] {csv_file} no existe. Ejecutar discovery_objects.py primero.")
        return objects
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["schema_name"], row["object_name"])
            objects[key] = {
                "schema_name": row["schema_name"],
                "object_name": row["object_name"],
                "object_type": row["object_type"],
                "estimated_rows": int(row.get("estimated_rows", 0)),
                "size_mb": float(row.get("size_mb", 0)),
                "last_analyze": row.get("last_analyze", "")
            }
    
    return objects


def load_dependencies(backend_path: Path) -> dict:
    """Carga discovery_dependencies.csv."""
    dependencies = defaultdict(list)
    csv_file = backend_path / "sql" / "ops" / "discovery_dependencies.csv"
    
    if not csv_file.exists():
        print(f"  [WARN] {csv_file} no existe. Ejecutar discovery_dependencies.py primero.")
        return dependencies
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            child_key = (row["child_schema"], row["child_name"])
            dependencies[child_key].append({
                "schema": row["parent_schema"],
                "name": row["parent_name"]
            })
    
    return dependencies


def load_usage(backend_path: Path) -> dict:
    """Carga discovery_usage_backend.csv."""
    usage = {}
    csv_file = backend_path / "sql" / "ops" / "discovery_usage_backend.csv"
    
    if not csv_file.exists():
        print(f"  [WARN] {csv_file} no existe. Ejecutar discovery_usage_backend.py primero.")
        return usage
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["schema_name"], row["object_name"])
            usage[key] = {
                "usage_context": row.get("usage_context", ""),
                "usage_locations": json.loads(row.get("usage_locations", "[]"))
            }
    
    return usage


def populate_registry(engine):
    """Pobla el registry desde discovery scripts."""
    backend_path = Path(__file__).parent.parent
    
    print("Cargando datos de discovery...")
    objects = load_discovery_objects(backend_path)
    dependencies = load_dependencies(backend_path)
    usage = load_usage(backend_path)
    
    print(f"  Objetos: {len(objects)}")
    print(f"  Dependencias: {sum(len(deps) for deps in dependencies.values())}")
    print(f"  Uso: {len(usage)}")
    
    with engine.connect() as conn:
        # Crear tabla si no existe
        sql_file = backend_path / "sql" / "ops" / "source_registry.sql"
        if sql_file.exists():
            with open(sql_file, "r", encoding="utf-8") as f:
                create_sql = f.read()
                # Ejecutar solo CREATE TABLE (antes de comentarios)
                create_table = create_sql.split("COMMENT ON")[0].strip()
                try:
                    conn.execute(text(create_table))
                    conn.commit()
                except Exception as e:
                    # Tabla ya existe, continuar
                    conn.rollback()
        
        # Preparar datos para propagación de criticidad
        registry_data = {}
        for (schema_name, object_name), obj_data in objects.items():
            full_name = f"{schema_name}.{object_name}"
            layer = infer_layer(schema_name, obj_data["object_type"])
            role = infer_role(schema_name, obj_data["object_type"], layer)
            
            # Obtener usage_context
            usage_context = None
            if (schema_name, object_name) in usage:
                usage_context = usage[(schema_name, object_name)]["usage_context"]
                if not usage_context:
                    usage_context = None
            
            # Inferir criticality inicial
            criticality = infer_criticality(
                schema_name, object_name, obj_data["object_type"],
                usage_context, full_name
            )
            
            registry_data[(schema_name, object_name)] = {
                "schema_name": schema_name,
                "object_name": object_name,
                "object_type": obj_data["object_type"],
                "layer": layer,
                "role": role,
                "criticality": criticality,
                "usage_context": usage_context
            }
        
        # Propagación de criticidad: RAW que alimenta MV crítica → critical
        print("  Propagando criticidad...")
        registry_data = propagate_criticality(registry_data, dependencies)
        
        # UPSERT para cada objeto
        print("\nPoblando registry...")
        upsert_count = 0
        update_count = 0
        
        for (schema_name, object_name), data in registry_data.items():
            obj_data = objects[(schema_name, object_name)]
            full_name = f"{schema_name}.{object_name}"
            layer = data["layer"]
            role = data["role"]
            criticality = data["criticality"]
            usage_context = data["usage_context"]
            
            # Obtener depends_on
            depends_on_list = dependencies.get((schema_name, object_name), [])
            depends_on_json = json.dumps(depends_on_list) if depends_on_list else None
            
            # Determinar should_monitor (default: critical)
            should_monitor = criticality == "critical"
            
            # UPSERT respetando overrides manuales
            result = conn.execute(text("""
                INSERT INTO ops.source_registry (
                    schema_name, object_name, object_type, layer, role,
                    criticality, should_monitor, usage_context, depends_on,
                    discovered_at, last_verified_at
                )
                VALUES (
                    :schema_name, :object_name, :object_type, :layer, :role,
                    :criticality, :should_monitor, :usage_context, CAST(:depends_on AS jsonb),
                    :discovered_at, :last_verified_at
                )
                ON CONFLICT (schema_name, object_name) DO UPDATE SET
                    object_type = EXCLUDED.object_type,
                    layer = EXCLUDED.layer,
                    role = EXCLUDED.role,
                    criticality = CASE 
                        WHEN ops.source_registry.is_critical IS NOT NULL 
                        THEN ops.source_registry.criticality
                        ELSE EXCLUDED.criticality
                    END,
                    should_monitor = CASE
                        WHEN ops.source_registry.health_enabled IS NOT NULL
                        THEN ops.source_registry.should_monitor
                        ELSE EXCLUDED.should_monitor
                    END,
                    usage_context = EXCLUDED.usage_context,
                    depends_on = EXCLUDED.depends_on,
                    discovered_at = COALESCE(ops.source_registry.discovered_at, EXCLUDED.discovered_at),
                    last_verified_at = EXCLUDED.last_verified_at,
                    updated_at = now()
                RETURNING id, discovered_at
            """), {
                "schema_name": schema_name,
                "object_name": object_name,
                "object_type": obj_data["object_type"],
                "layer": layer,
                "role": role,
                "criticality": criticality,
                "should_monitor": should_monitor,
                "usage_context": usage_context,
                "depends_on": depends_on_json,
                "discovered_at": datetime.now(),
                "last_verified_at": datetime.now()
            })
            
            row = result.fetchone()
            if row and row[1] is None:
                # Nuevo registro
                upsert_count += 1
            else:
                # Registro existente actualizado
                update_count += 1
        
        conn.commit()
        
        print(f"  Nuevos registros: {upsert_count}")
        print(f"  Registros actualizados: {update_count}")
        print(f"  Total procesados: {upsert_count + update_count}")


def main():
    print("=" * 70)
    print("POBLAR SOURCE REGISTRY")
    print("=" * 70)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    engine = create_engine(settings.database_url)
    
    try:
        populate_registry(engine)
        print("\n[OK] Registry poblado exitosamente.")
    except Exception as e:
        print(f"\n[ERROR] Error poblando registry: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

