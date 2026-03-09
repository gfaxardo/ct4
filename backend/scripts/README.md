# Scripts del backend

Scripts de soporte, verificación, backfill y one-off. No son parte de la API; se ejecutan a mano o por cron.

## Cómo ejecutar

Desde la raíz del **backend** (donde está `app/`):

```bash
cd backend
export DATABASE_URL="postgresql://user:pass@host:port/dbname"   # o usar .env
python scripts/nombre_script.py
```

Algunos scripts asumen `sys.path` con el backend; suelen hacer `sys.path.insert(0, str(Path(__file__).parent.parent))` al inicio.

## Acceso a base de datos (convención)

**No** crear `create_engine` ni `sessionmaker` propios. Usar siempre `app.db`:

| Necesitas | Importar | Uso |
|-----------|----------|-----|
| Sesión (consultas ORM o `text()`) | `from app.db import SessionLocal` | `db = SessionLocal()` y `db.close()` en `finally` |
| Engine (solo si usas `engine.connect()`) | `from app.db import engine` | `with engine.connect() as conn:` |
| URL (subprocess psql, etc.) | `from app.db import get_db_url` | `url = get_db_url()` |

Config (por ejemplo `database_url`) con `from app.config import settings`.

Opcional: context manager para sesión en `scripts/common.py`:

```python
from scripts.common import get_session
with get_session() as db:
    ...
```

## Carpetas relacionadas

- **sql/** – DDL, vistas, MVs; algunos scripts los ejecutan o referencian.
- **app/** – Código de la API; los scripts importan `app.db`, `app.config`, etc.
