# Arquitectura y organización del código — CT4

Este documento describe cómo está organizado el proyecto para que sea **entendible** y **escalable**. Sigue estas convenciones al añadir código nuevo.

---

## 1. Visión general

```
ct4/
├── backend/          # API FastAPI + servicios + BD
├── frontend/         # Next.js (App Router) + UI
├── docs/             # Documentación (runbooks, contratos, esta guía)
├── scripts/          # Scripts de utilidad (backup, etc.)
└── backend/scripts/  # Scripts de datos y validación (SQL, Python)
```

- **Backend**: expone `/api/v1/*` por dominio (auth, identity, payments, scouts, ops, etc.).
- **Frontend**: llama solo a esa API; toda la lógica de negocio y datos vive en el backend.
- **Base de datos**: PostgreSQL con schemas `public`, `canon`, `ops`. Vistas y funciones en `backend/sql/`.

---

## 2. Dominios del sistema

Agrupa el código por **dominio** (área de negocio), no por tipo técnico:

| Dominio | Descripción | Backend (app) | Frontend (app) |
|--------|-------------|---------------|----------------|
| **Auth** | Login, tokens | `api/v1/auth.py` | `app/login/` |
| **Identidad** | Personas, unmatched, runs, métricas | `api/v1/identity.py` | `app/persons/`, `app/unmatched/`, `app/runs/` |
| **Identidad – Auditoría** | Origen, alertas de auditoría | `api/v1/identity_audit.py` | `app/audit/` |
| **Identity gaps** | Gaps de identidad, recuperación | (en `ops`) | — |
| **Pagos (core)** | Elegibilidad, driver matrix | `api/v1/payments.py` | `app/pagos/` |
| **Pagos Yango** | Reconciliación, claims, cobranza | `api/v1/yango_payments.py` | `app/pagos/cobranza-yango/`, `yango-cabinet*` |
| **Pagos Ops** | Cabinet financial 14d, limbo, claims gap, KPIs cobranza | `api/v1/ops_payments.py` | mismo |
| **Scouts** | Atribución, liquidaciones, conflictos | `api/v1/scouts.py` | `app/scouts/` |
| **Cabinet leads** | Carga de leads, auto-processor | `api/v1/cabinet_leads.py` | `app/cabinet-leads/` |
| **Dashboard** | Resúmenes scout y Yango | `api/v1/dashboard.py` | `app/dashboard/` |
| **Liquidación** | Preview y mark paid scouts | `api/v1/liquidation.py` | `app/liquidaciones/` |
| **Attribution** | Eventos y ledger de atribución | `api/v1/attribution.py` | — |
| **Ops** | Health, alertas, ingest, MVs | `api/v1/ops.py` | `app/ops/` |

Al añadir un **nuevo endpoint**, decide a qué dominio pertenece y colócalo en el router de ese dominio (o crea un nuevo router solo si es un dominio nuevo).

---

## 3. Backend: estructura recomendada

```
backend/app/
├── main.py              # FastAPI app, CORS, lifespan (punto de entrada: uvicorn app.main:app)
├── config.py            # Re-exporta app.core.config (compatibilidad)
├── db.py                # Re-exporta app.core.db (compatibilidad)
├── core/                # Núcleo: configuración y BD
│   ├── config.py        # Settings, DATABASE_URL, CORS, etc.
│   ├── db.py            # Engine, SessionLocal, get_db, Base
│   └── db_utils.py      # row_to_dict, utilidades de resultados
├── api/
│   ├── health.py        # /health
│   └── v1/
│       ├── __init__.py  # Agrupa todos los routers bajo /api/v1
│       ├── auth.py
│       ├── identity.py
│       ├── payments.py
│       ├── yango_payments.py
│       ├── ops_payments.py   # Ops + Cobranza (archivo grande; ver sección 5)
│       ├── ops.py
│       ├── scouts.py
│       ├── dashboard.py
│       ├── cabinet_leads.py
│       ├── liquidation.py
│       ├── attribution.py
│       └── identity_audit.py
├── core/                # Utilidades compartidas (DB, etc.)
├── models/              # SQLAlchemy (canon, ops, observacional)
├── schemas/             # Pydantic (request/response por dominio)
└── services/            # Lógica de negocio (no HTTP)
```

**Reglas:**

- **Rutas**: definir en `api/v1/<dominio>.py` y registrar en `api/v1/__init__.py` con un prefijo claro (`/auth`, `/identity`, `/payments`, etc.).
- **Lógica pesada**: ponerla en `services/` y llamarla desde el router; evita bloques de muchas líneas en los endpoints.
- **Schemas**: un archivo (o varios) por dominio en `schemas/`; que los nombres coincidan con el dominio (p. ej. `payments`, `cabinet_financial`).
- **SQL**: vistas y funciones en `backend/sql/` (por schema o feature); migraciones en `alembic/`.

---

## 4. Frontend: estructura recomendada

```
frontend/
├── app/                 # App Router (páginas y layouts)
│   ├── layout.tsx
│   ├── page.tsx
│   ├── login/
│   ├── pagos/            # Cobranza, driver matrix, claims
│   ├── scouts/
│   ├── ops/
│   ├── audit/
│   ├── cabinet-leads/
│   └── ...
├── components/           # Componentes reutilizables (si los hay)
├── lib/
│   ├── api.ts           # Punto de entrada: re-exporta todo el cliente API
│   ├── api/             # (opcional) Módulos por dominio para escalar
│   ├── types.ts         # Tipos compartidos
│   ├── utils.ts
│   ├── endpoints.ts
│   └── hooks/
└── ...
```

**Reglas:**

- Todas las llamadas HTTP pasan por `lib/api.ts` (o por módulos que este re-exporte).
- Rutas de la app (`app/pagos/`, `app/scouts/`, etc.) alineadas con los dominios del backend.
- Tipos compartidos en `lib/types.ts`; mantener nombres alineados con los schemas del backend.

---

## 5. Escalabilidad: archivos muy grandes

Algunos archivos del backend son muy largos (p. ej. `ops_payments.py` ~2600 líneas). Para escalar sin romper nada:

1. **Corto plazo**: mantener un solo archivo pero **ordenar por secciones** con comentarios (`# --- Driver matrix ---`, `# --- Cabinet financial 14d ---`, `# --- Cobranza Yango ---`, etc.) y agrupar endpoints relacionados.
2. **Mediano plazo**: extraer **handlers** a módulos internos, por ejemplo:
   - `api/v1/ops_payments_handlers/cabinet_financial.py`
   - `api/v1/ops_payments_handlers/cobranza_yango.py`
   - `api/v1/ops_payments_handlers/limbo_claims_gap.py`  
   y que `ops_payments.py` solo registre rutas y delegue en esas funciones.
3. **Routers**: no hace falta partir el router en muchos archivos hasta que un dominio crezca mucho; entonces puedes crear `api/v1/payments/` con `router.py` + `cobranza.py`, `driver_matrix.py`, etc., e incluirlos desde un único router de “payments”.

Lo mismo aplica al frontend: si `lib/api.ts` crece mucho, divídelo en `lib/api/identity.ts`, `lib/api/payments.ts`, etc., y que `lib/api.ts` re-exporte todo para no cambiar imports en el resto de la app.

---

## 6. Nombres y convenciones

- **URLs**: `kebab-case` (`/cabinet-financial-14d`, `/scout-attribution-metrics`).
- **Python**: `snake_case` en funciones y variables; nombres de routers/archivos que reflejen el dominio.
- **TypeScript**: `camelCase` en funciones y variables; nombres de archivos coherentes con el dominio (`cobranza-yango`, `driver-matrix`).
- **Rutas API**: prefijo por dominio (`/api/v1/payments/...`, `/api/v1/ops/...`) y un solo lugar donde se documenta el mapa completo (p. ej. `backend/docs/API_ORGANIZATION.md`).

---

## 7. Dónde documentar qué

| Qué | Dónde |
|-----|--------|
| Contrato API (endpoints, schemas) | `docs/contracts/FRONTEND_BACKEND_CONTRACT_v1.md` |
| Mapa de rutas → módulos backend | `backend/docs/API_ORGANIZATION.md` |
| Setup BD, migraciones, vistas | `backend/docs/SETUP_BASE_DE_DATOS.md` |
| Runbooks operativos | `docs/runbooks/*.md` |
| Esta guía de arquitectura | `docs/ARCHITECTURE.md` |

---

Resumen: **organiza por dominio**, **mantén rutas y módulos alineados entre backend y frontend**, y **extrae lógica a servicios/handlers** cuando un archivo crezca demasiado. Así el código sigue siendo entendible y escalable.
