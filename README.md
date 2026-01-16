# CT4 Identity System — YEGO

Sistema integral de **Identidad Canónica** y **Gestión Operativa** para conductores YEGO.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-Next.js%2014-black)

## 🎯 Objetivo

Sistema end-to-end que:
1. **Identifica** de forma única a cada conductor a través de múltiples fuentes
2. **Gestiona pagos** y reconciliación con Yango Cabinet
3. **Administra scouts** y atribución de conductores
4. **Monitorea** la salud operativa del sistema

## 📊 Módulos del Sistema

### 💰 Pagos
- **Cobranza Yango**: Dashboard de cobranza y pagos
- **Claims Cabinet**: Claims exigibles pendientes de cobro
- **Reconciliación**: Cruce de pagos achieveds vs ledger
- **Elegibilidad**: Estado de elegibilidad por conductor
- **Driver Matrix**: Vista consolidada por conductor y milestone

### 🎯 Scouts
- **Atribución**: Salud del proceso de atribución de scouts
- **Liquidaciones**: Base para liquidación de scouts
- **Conflictos**: Resolución de atribuciones múltiples
- **Backlog**: Personas sin scout asignado

### 👤 Identidad
- **Personas**: Registro canónico de conductores
- **Unmatched**: Registros pendientes de resolución
- **Auditoría**: Historial de corridas de matching

### ⚙️ Operaciones
- **Alerts**: Centro de alertas operacionales
- **Health**: Estado del sistema
- **Cargar Leads**: Importación de Cabinet Leads

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **Base de Datos** | PostgreSQL 15+ (schemas: `public`, `canon`, `ops`) |
| **Contenedores** | Docker, Docker Compose |

## 📁 Estructura del Proyecto

```
ct4/
├── backend/
│   ├── app/
│   │   ├── api/v1/         # Endpoints por módulo
│   │   ├── models/         # Modelos SQLAlchemy
│   │   ├── schemas/        # Schemas Pydantic
│   │   ├── services/       # Lógica de negocio
│   │   └── main.py         # Aplicación FastAPI
│   ├── sql/                # Vistas y funciones SQL
│   ├── alembic/            # Migraciones
│   └── requirements.txt
├── frontend/
│   ├── app/                # Páginas Next.js (App Router)
│   ├── components/         # Componentes React reutilizables
│   ├── lib/                # API client y utilidades
│   └── package.json
├── docs/                   # Documentación técnica
├── scripts/                # Scripts de utilidad
├── docker-compose.yml
├── README.md
└── SETUP.md
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.12+
- Node.js 20+
- Acceso a PostgreSQL

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

**Acceder a:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

> 📖 **Instrucciones detalladas en [SETUP.md](SETUP.md)**

## 🔑 Concepto Clave

**SCOUT ≠ PERSONA ≠ DRIVER**

| Entidad | Descripción | Identificador |
|---------|-------------|---------------|
| **PERSONA** | Individuo real (conductor) | `person_key` |
| **DRIVER** | Cuenta operativa en el parque | `driver_id` |
| **SCOUT** | Actor de atribución (referidor) | `scout_id` |

## 📡 API Endpoints Principales

### Identity
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/identity/run` | Ejecutar corrida de matching |
| `GET` | `/api/v1/identity/persons` | Listar personas |
| `GET` | `/api/v1/identity/unmatched` | Registros sin resolver |

### Payments
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/yango/cabinet/claims` | Claims exigibles |
| `GET` | `/api/v1/payments/driver-matrix` | Matriz de conductores |
| `GET` | `/api/v1/payments/eligibility` | Elegibilidad de pagos |

### Scouts
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/scouts/attribution/metrics` | Métricas de atribución |
| `GET` | `/api/v1/scouts/liquidation/base` | Base de liquidación |
| `GET` | `/api/v1/scouts/conflicts` | Conflictos de atribución |

### Operations
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/ops/alerts` | Alertas del sistema |
| `POST` | `/api/v1/cabinet-leads/upload` | Cargar leads CSV |

> Ver documentación completa en: http://localhost:8000/docs

## 🎨 Componentes UI

El frontend incluye componentes reutilizables:

- **StatCard**: Tarjetas de métricas
- **Badge**: Etiquetas de estado
- **Pagination**: Paginación de tablas
- **Modal**: Diálogos modales (con Portal)
- **DataTable**: Tablas de datos
- **PageLoadingOverlay**: Indicador de carga

## 📊 Schemas de Base de Datos

### Schema `canon` (Datos Canónicos)
- `identity_registry`: Registro de personas
- `identity_links`: Vínculos persona-fuente
- `identity_unmatched`: Registros sin resolver

### Schema `ops` (Operaciones)
- `ingestion_runs`: Corridas de ingesta
- `ops_alerts`: Alertas del sistema
- `v_payments_*`: Vistas de pagos
- `v_scout_*`: Vistas de scouts

## 🔧 Reglas de Matching

| Regla | Descripción | Score | Confianza |
|-------|-------------|-------|-----------|
| R1 PHONE_EXACT | Match por teléfono exacto | 95 | HIGH |
| R2 LICENSE_EXACT | Match por licencia exacta | 92 | HIGH |
| R3 PLATE+NAME | Placa + nombre similar | 85 | MEDIUM |
| R4 CAR+NAME | Marca/modelo + nombre | 75 | LOW |

## 🐳 Docker

```bash
# Levantar todo el sistema
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## 🔍 Troubleshooting

### Error de conexión a BD
```bash
# Verificar conectividad
psql -h 168.119.226.236 -U yego_user -d yego_integral
```

### Frontend no conecta al backend
```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health
```

### Migraciones pendientes
```bash
cd backend
alembic upgrade head
```

> Más soluciones en [SETUP.md](SETUP.md)

## 📝 Licencia

Proyecto interno YEGO © 2024-2026
