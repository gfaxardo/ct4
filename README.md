# Contractor Tracker 4 — YEGO
## Sistema de Identidad Canónica (FASE 1)

Sistema end-to-end que identifica de forma única a una PERSONA (conductor) a través de múltiples fuentes de datos.

## Objetivo de la Fase 1

Responder únicamente:
- ¿Quién es esta persona?
- ¿Qué registros de qué fuentes pertenecen a ella?
- ¿Con qué regla, score y evidencia se hizo el match?
- ¿Qué registros NO se pudieron conciliar todavía?

## Concepto Crítico

**SCOUT ≠ PERSONA ≠ DRIVER**

1. **PERSONA**: Individuo real (conductor), representado con `person_key` canónico
2. **DRIVER**: Cuenta operativa en el parque (`driver_id`), pertenece a una PERSONA
3. **SCOUT**: Actor de atribución, NUNCA participa del matching de identidad

## Stack Tecnológico

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- **DB**: PostgreSQL 15+ (schemas: `public`, `canon`, `ops`)
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS

## Estructura del Proyecto

```
CT4/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── services/     # Lógica de negocio
│   │   ├── main.py       # Aplicación FastAPI
│   │   └── db.py         # Configuración DB
│   ├── alembic/          # Migraciones
│   └── requirements.txt
├── frontend/
│   ├── app/              # Páginas Next.js
│   ├── components/       # Componentes React
│   ├── lib/              # Utilidades y API client
│   └── package.json
├── SETUP.md              # Guía de instalación paso a paso
└── README.md
```

## Instalación y Uso

**📖 Para instrucciones detalladas paso a paso, ver [SETUP.md](SETUP.md)**

### Prerrequisitos

- Python 3.12+ instalado
- Node.js 20+ y npm instalados
- Acceso a la base de datos PostgreSQL remota
- Las tablas RAW ya deben existir en PostgreSQL:
  - `public.module_ct_cabinet_leads`
  - `public.drivers`
  - `public.module_ct_scouting_daily`

### Configuración Backend

1. **Navegar al directorio backend**:
   ```bash
   cd backend
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   ```

3. **Activar entorno virtual**:
   ```bash
   # Windows:
   venv\Scripts\activate
   
   # Linux/Mac:
   source venv/bin/activate
   ```

4. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configurar variables de entorno (opcional)**:
   Crear archivo `.env` en `backend/` si deseas sobrescribir:
   ```env
   DATABASE_URL=postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral
   LOG_LEVEL=INFO
   ```
   
   **Nota**: La configuración ya tiene las credenciales por defecto, pero puedes usar `.env` para personalizar.

6. **Aplicar migraciones**:
   ```bash
   alembic upgrade head
   ```

7. **Ejecutar el backend**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   El backend estará disponible en: http://localhost:8000

### Configuración Frontend

1. **Navegar al directorio frontend**:
   ```bash
   cd frontend
   ```

2. **Instalar dependencias**:
   ```bash
   npm install
   ```

3. **Configurar API URL (opcional)**:
   Crear archivo `.env.local` en `frontend/`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   
   **Nota**: Esta es la URL por defecto si no se especifica.

4. **Ejecutar el frontend**:
   ```bash
   npm run dev
   ```

   El frontend estará disponible en: http://localhost:3000

### Ejecutar una Ingesta

1. Desde el frontend, navegar a "Corridas" y hacer clic en "Ejecutar Ingesta"
2. O desde la API: `POST http://localhost:8000/api/v1/identity/run`

### Desarrollo Local

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Fuentes de Datos RAW

El sistema procesa datos de 3 fuentes en el schema `public`:

1. **`module_ct_cabinet_leads`**: Eventos de registro en Yango
   - Campos: `external_id`, `park_phone`, `first_name`, `middle_name`, `last_name`, `asset_plate_number`, `asset_brand`, `asset_model`, `lead_created_at`

2. **`drivers`**: Estado del conductor en el parque
   - Campos: `driver_id`, `phone`, `document_number`, `license_number`, `license_number_norm`, `full_name`, `run_date`

3. **`module_ct_scouting_daily`**: Eventos humanos de afiliación
   - Campos: `scout_id`, `driver_phone`, `driver_license`, `driver_name`, `registration_date`
   - ⚠️ `scout_id` NO se usa para matching, solo como metadata

## Esquema Canónico

### `canon.identity_registry`
Registro canónico de personas identificadas.

### `canon.identity_links`
Vínculos entre personas y fuentes RAW, con evidencia del match.

### `canon.identity_unmatched`
Registros que no pudieron ser conciliados (ambiguos o sin match).

### `ops.ingestion_runs`
Historial de corridas de ingesta.

## Reglas de Matching

Las reglas se aplican en orden de prioridad:

- **R1 PHONE_EXACT**: Match por teléfono exacto
  - Score: 95 / Confianza: HIGH

- **R2 LICENSE_EXACT**: Match por licencia exacta
  - Score: 92 / Confianza: HIGH

- **R3 PLATE_EXACT + NAME_SIMILAR**: Match por placa exacta + nombre similar
  - Score: 85 / Confianza: MEDIUM
  - Requiere similitud de nombre >= 0.5

- **R4 CAR_FINGERPRINT + NAME_SIMILAR**: Match por marca+modelo + nombre similar
  - Score: 75 / Confianza: LOW
  - Requiere similitud de nombre >= 0.5

**Resolución de ambigüedades**: Si múltiples personas matchean, el registro va a `identity_unmatched` con razón "AMBIGUOUS".

## Operación de Identidad en Producción

### Ejecutar Corridas de Matching

#### Primera Corrida (Obligatorio: Scope Requerido)

La primera corrida **DEBE** incluir un scope explícito para evitar procesar todo el histórico accidentalmente:

```bash
POST /api/v1/identity/run?date_from=2024-01-01&date_to=2024-01-31
```

O usando `scope_date` para un solo día:
```bash
POST /api/v1/identity/run?scope_date=2024-01-15
```

**Sin scope, el sistema rechazará la corrida con error 400** si no existe ninguna corrida previa completada.

#### Corridas Incrementales

Después de la primera corrida, el sistema opera en modo incremental por defecto:

```bash
POST /api/v1/identity/run
```

El sistema automáticamente:
- Busca la última corrida completada
- Usa `scope_date_to` de esa corrida como `date_from` de la nueva
- Procesa solo registros nuevos o actualizados desde entonces

#### Refrescar drivers_index

El catálogo `canon.drivers_index` **NO se refresca automáticamente** en cada corrida de matching. Esto es intencional para mantener el matching desacoplado del catálogo.

**Para refrescar drivers_index manualmente:**
```bash
POST /api/v1/identity/drivers-index/refresh
```

**Para refrescar drivers_index antes de una corrida de matching:**
```bash
POST /api/v1/identity/run?refresh_index=true&date_from=2024-01-01&date_to=2024-01-31
```

**Recomendación**: Refrescar `drivers_index` diariamente mediante un job separado (cron), no en cada corrida de matching.

### Trazabilidad por Corrida (run_id)

Cada registro en `canon.identity_links` y `canon.identity_unmatched` incluye un `run_id` que indica de qué corrida proviene. Esto permite:

- Auditar qué se procesó en cada corrida
- Identificar problemas específicos de una corrida
- Analizar tendencias por corrida

### Queries de Auditoría

#### Matched vs Unmatched por Corrida

```sql
SELECT 
    run_id,
    COUNT(*) FILTER (WHERE run_id IS NOT NULL) as total_links,
    (SELECT COUNT(*) FROM canon.identity_unmatched WHERE run_id = il.run_id) as total_unmatched
FROM canon.identity_links il
WHERE run_id = :run_id
GROUP BY run_id;
```

#### Breakdown por Regla de Matching

```sql
SELECT 
    match_rule,
    confidence_level,
    COUNT(*) as count
FROM canon.identity_links
WHERE run_id = :run_id
GROUP BY match_rule, confidence_level
ORDER BY count DESC;
```

#### Breakdown por Razón de Unmatched

```sql
SELECT 
    reason_code,
    COUNT(*) as count
FROM canon.identity_unmatched
WHERE run_id = :run_id
GROUP BY reason_code
ORDER BY count DESC;
```

#### Eventos Convertidos a Driver

```sql
SELECT 
    il.person_key,
    il.source_table,
    il.source_pk,
    il.match_rule,
    il.linked_at
FROM canon.identity_links il
WHERE il.run_id = :run_id
  AND il.person_key IN (
      SELECT person_key 
      FROM canon.identity_links 
      WHERE source_table = 'drivers' 
        AND run_id = :run_id
  )
  AND il.source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily');
```

#### Top Motivos de MISSING_KEYS

```sql
SELECT 
    details->>'missing_keys' as missing_keys,
    COUNT(*) as count
FROM canon.identity_unmatched
WHERE run_id = :run_id
  AND reason_code = 'MISSING_KEYS'
GROUP BY details->>'missing_keys'
ORDER BY count DESC
LIMIT 10;
```

### Interpretación de reason_code

- **MISSING_KEYS**: Faltan campos requeridos para aplicar las reglas de matching (ej: no hay teléfono ni licencia)
- **NO_MATCH**: No se encontró ningún candidato que cumpla las reglas de matching
- **MULTIPLE_CANDIDATES**: Se encontraron múltiples candidatos con scores muy cercanos (gap < 0.15), el sistema no elige automáticamente para evitar errores

### Qué Hacer con MULTIPLE_CANDIDATES

Cuando un registro tiene `reason_code = MULTIPLE_CANDIDATES`:

1. Revisar `candidates_preview` en el registro de `identity_unmatched`
2. Analizar la evidencia de cada candidato
3. Resolver manualmente usando el endpoint `/api/v1/identity/unmatched/{id}/resolve` con el `person_key` correcto

### Reporte Detallado por Corrida

Obtener un breakdown completo de una corrida:

```bash
GET /api/v1/identity/runs/{run_id}/report
```

Este endpoint retorna:
- Conteos por fuente (cabinet_leads, scouting_daily)
- Breakdown de matched por regla y confianza
- Breakdown de unmatched por razón
- Top missing keys
- Samples de top matched y unmatched

## API Endpoints

### Identity

- `POST /api/v1/identity/run`: Ejecutar ingesta (parámetros: `date_from`, `date_to`, `scope_date`, `refresh_index`, `incremental`)
- `GET /api/v1/identity/runs/{run_id}/report`: Obtener reporte detallado de una corrida
- `POST /api/v1/identity/drivers-index/refresh`: Refrescar catálogo de drivers
- `GET /api/v1/identity/persons`: Listar personas (filtros: phone, document, license, name, confidence_level)
- `GET /api/v1/identity/persons/{person_key}`: Obtener detalle de persona con sus links
- `GET /api/v1/identity/unmatched`: Listar registros sin resolver (filtros: reason_code, status, source_table, run_id)
- `POST /api/v1/identity/unmatched/{id}/resolve`: Resolver manualmente un registro unmatched

### Operations

- `GET /api/v1/ops/ingestion-runs`: Historial de corridas de ingesta

### Health

- `GET /health`: Health check

Ver documentación completa en: http://localhost:8000/docs

## Frontend

El frontend ofrece las siguientes vistas:

- **Dashboard**: Métricas generales y última corrida
- **Personas**: Lista de personas identificadas con búsqueda
- **Detalle de Persona**: Información canónica y vínculos con evidencia
- **Sin Resolver**: Lista de registros unmatched con filtros
- **Corridas**: Historial de ingesta y botón para ejecutar nueva corrida

## Normalización de Datos

El sistema normaliza:

- **Teléfonos**: Elimina espacios, guiones, normaliza formato (ej: +593... → 0...)
- **Nombres**: Uppercase, elimina acentos, tokeniza, elimina stopwords
- **Licencias**: Normaliza formato, elimina espacios
- **Placas**: Normaliza formato, elimina espacios
- **Fechas**: Soporta múltiples formatos (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY)

## Consideraciones Importantes

1. **REBUILD Idempotente**: Cada corrida limpia y recrea los registros canónicos
2. **Scout no participa**: `scout_id` es solo metadata, nunca se usa para matching
3. **Robustez**: Formatos inválidos no rompen el pipeline, se registran como errores
4. **Extensibilidad**: El diseño permite agregar nuevas fuentes sin cambiar `identity_registry`

## Troubleshooting

Para soluciones detalladas a problemas comunes, consulta [SETUP.md](SETUP.md).

### Errores Comunes

**Error de conexión a base de datos:**
- Verificar que la IP `168.119.226.236` sea accesible desde tu red
- Verificar credenciales en `backend/app/config.py`
- Verificar que el firewall permita conexiones al puerto 5432

**Migraciones no aplicadas:**
```bash
cd backend
alembic upgrade head
```

**Frontend no conecta al backend:**
- Verificar que el backend esté corriendo en http://localhost:8000
- Verificar variable `NEXT_PUBLIC_API_URL` en `.env.local` (si existe)

**Problemas con módulos Python:**
- Asegurarse de que el entorno virtual esté activado
- Reinstalar dependencias: `pip install -r requirements.txt`

## Licencia

Proyecto interno YEGO.
