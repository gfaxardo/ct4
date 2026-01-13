# Rutas y Comandos para Armar el Sistema Manualmente

## 📋 Prerrequisitos

Verificar que tengas instalado:
```powershell
python --version    # Debe ser 3.12 o superior
node --version      # Debe ser 20 o superior
npm --version       # Viene con Node.js
```

---

## 🎯 Rutas Absolutas del Proyecto

**Proyecto raíz:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4
```

**Backend:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend
```

**Frontend:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend
```

---

## 🚀 Pasos de Instalación

### PASO 1: Configurar Backend

#### 1.1 Navegar al directorio backend
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend
```

#### 1.2 Crear entorno virtual
```powershell
python -m venv venv
```

**Ruta del venv:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\venv
```

#### 1.3 Activar entorno virtual (Windows)
```powershell
venv\Scripts\activate
```

**O usar la ruta completa:**
```powershell
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\venv\Scripts\activate
```

#### 1.4 Instalar dependencias Python
```powershell
pip install -r requirements.txt
```

**Archivo de dependencias:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\requirements.txt
```

#### 1.5 (Opcional) Crear archivo .env para configuración
**Ruta:** `C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\.env`

**Contenido:**
```env
DATABASE_URL=postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral
LOG_LEVEL=INFO
```

**Nota:** Si no creas `.env`, el sistema usa las credenciales por defecto de `config.py`:
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\app\config.py
```

#### 1.6 Aplicar migraciones de base de datos
```powershell
alembic upgrade head
```

**Configuración de Alembic:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\alembic.ini
```

**Migraciones:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\alembic\versions\
```

#### 1.7 Ejecutar el backend
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**URLs del backend:**
- API: http://localhost:8000
- Health Check: http://localhost:8000/health
- Documentación: http://localhost:8000/docs

**Archivo principal:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\app\main.py
```

---

### PASO 2: Configurar Frontend

**Abrir una NUEVA terminal** (mantener el backend corriendo)

#### 2.1 Navegar al directorio frontend
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend
```

#### 2.2 Instalar dependencias Node.js
```powershell
npm install
```

**Archivo de dependencias:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend\package.json
```

**Node modules se creará en:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend\node_modules
```

#### 2.3 (Opcional) Configurar URL del API
**Ruta:** `C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend\.env.local`

**Contenido:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Nota:** Por defecto ya usa `http://localhost:8000`, así que este paso es opcional.

#### 2.4 Ejecutar el frontend
```powershell
npm run dev
```

**URL del frontend:**
- Frontend: http://localhost:3000

**Archivos principales:**
```
C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend\app\page.tsx
C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend\app\layout.tsx
```

---

## 📝 Comandos Rápidos (Resumen)

### Terminal 1 - Backend:
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

### Terminal 2 - Frontend:
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend
npm run dev
```

---

## 🔍 Rutas Importantes del Proyecto

### Backend
```
backend/
├── app/
│   ├── main.py                    # Aplicación FastAPI principal
│   ├── config.py                  # Configuración (DB, settings)
│   ├── db.py                      # Configuración de base de datos
│   ├── api/
│   │   └── v1/
│   │       ├── identity.py        # Endpoints de identidad
│   │       ├── attribution.py     # Endpoints de atribución
│   │       └── ops.py             # Endpoints de operaciones
│   ├── models/
│   │   ├── canon.py               # Modelos del schema canon
│   │   ├── observational.py       # Modelos observacionales
│   │   └── ops.py                 # Modelos del schema ops
│   ├── schemas/
│   │   ├── identity.py            # Schemas Pydantic de identidad
│   │   ├── attribution.py         # Schemas de atribución
│   │   └── ingestion.py           # Schemas de ingesta
│   └── services/
│       ├── ingestion.py           # Servicio de ingesta
│       ├── matching.py            # Servicio de matching
│       ├── normalization.py       # Normalización de datos
│       └── lead_attribution.py    # Atribución de leads
├── alembic/
│   ├── env.py                     # Configuración de Alembic
│   └── versions/                  # Migraciones SQL
├── requirements.txt               # Dependencias Python
└── alembic.ini                    # Configuración Alembic
```

### Frontend
```
frontend/
├── app/
│   ├── page.tsx                   # Página principal (Dashboard)
│   ├── layout.tsx                 # Layout principal
│   ├── globals.css                # Estilos globales
│   ├── persons/
│   │   ├── page.tsx               # Lista de personas
│   │   └── [person_key]/
│   │       └── page.tsx           # Detalle de persona
│   ├── unmatched/
│   │   └── page.tsx               # Registros sin resolver
│   └── runs/
│       └── page.tsx               # Historial de corridas
├── components/
│   ├── WeeklyFilters.tsx          # Filtros semanales
│   └── WeeklyMetricsView.tsx      # Vista de métricas
├── lib/
│   ├── api.ts                     # Cliente API
│   └── utils.ts                   # Utilidades
└── package.json                   # Dependencias Node.js
```

---

## 🔌 Endpoints API Principales

**Base URL:** http://localhost:8000

### Identity
- `POST /api/v1/identity/run` - Ejecutar ingesta
- `GET /api/v1/identity/runs/{run_id}/report` - Reporte de corrida
- `POST /api/v1/identity/drivers-index/refresh` - Refrescar índice de drivers
- `GET /api/v1/identity/persons` - Listar personas
- `GET /api/v1/identity/persons/{person_key}` - Detalle de persona
- `GET /api/v1/identity/unmatched` - Listar sin resolver
- `POST /api/v1/identity/unmatched/{id}/resolve` - Resolver manualmente

### Operations
- `GET /api/v1/ops/ingestion-runs` - Historial de corridas

### Health
- `GET /health` - Health check

**Documentación completa:** http://localhost:8000/docs

---

## 🗄️ Base de Datos

**Conexión:**
- Host: `168.119.226.236`
- Puerto: `5432`
- Database: `yego_integral`
- Usuario: `yego_user`
- Contraseña: `37>MNA&-35+`

**Schemas creados:**
- `public` - Fuentes RAW (ya existente)
- `canon` - Identidad canónica (creado por migraciones)
- `ops` - Operaciones (creado por migraciones)

**Tablas RAW requeridas (deben existir en `public`):**
- `module_ct_cabinet_leads`
- `drivers`
- `module_ct_scouting_daily`

---

## 🛑 Detener el Sistema

Para detener los servicios:
1. En cada terminal, presiona `Ctrl + C`
2. Para desactivar el venv: `deactivate` (opcional)

---

## 🔄 Re-ejecutar (Después del Primer Setup)

Una vez configurado todo, solo necesitas:

**Terminal 1 - Backend:**
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```powershell
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\frontend
npm run dev
```

No necesitas volver a ejecutar `pip install` ni `npm install` a menos que actualices las dependencias.

---

## ✅ Verificación Final

1. ✅ Backend corriendo: http://localhost:8000/health → `{"status":"ok"}`
2. ✅ Frontend corriendo: http://localhost:3000 se abre sin errores
3. ✅ Base de datos: Las migraciones se aplicaron correctamente
4. ✅ API Docs: http://localhost:8000/docs muestra la documentación

---

## 📚 Documentación Adicional

- **README.md**: Descripción general del proyecto
- **SETUP.md**: Guía detallada de instalación
- **docs/**: Documentación adicional

---

¡Listo! Con estas rutas y comandos puedes armar el sistema manualmente.










