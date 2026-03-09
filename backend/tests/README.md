# Tests del backend

## Cómo ejecutar

Desde la raíz del backend (donde está `app/` y `pytest.ini`):

```bash
cd backend
pytest
```

O con ruta explícita:

```bash
pytest tests/ -v
```

Para ejecutar un solo archivo o un test:

```bash
pytest tests/test_payments_driver_matrix.py -v
pytest tests/test_ops_payments_driver_matrix.py::test_ops_driver_matrix_endpoint_returns_200 -v
```

## Requisitos

- **pytest**: instalar con `pip install pytest` (o está en dependencias de desarrollo).
- **Tests de API** (`test_payments_driver_matrix.py`, `test_ops_payments_driver_matrix.py`): no requieren base de datos si los endpoints no la usan en la ruta probada.
- **Tests con DB** (`test_scouting_observation.py`, `test_report_weekly.py`): requieren `DATABASE_URL` configurada (`.env` o variable de entorno). Crean tablas con `Base.metadata.create_all` en la DB indicada.
- **Tests de integridad** (`test_orphans_integrity.py`): requieren base de datos con esquema real (vistas `ops.v_cabinet_funnel_status`, tablas `canon.identity_links`, `canon.driver_orphan_quarantine`). No crean tablas.

## Estructura

- **conftest.py**: fixtures compartidas:
  - `client`: `TestClient(app)` para llamar a la API.
  - `db_session`: sesión de DB con tablas creadas; para tests que escriben en la base.
- Los tests que usan solo la API reciben `client`; los que tocan la DB reciben `db_session` (o su propia fixture `db` en el caso de `test_orphans_integrity.py`).
