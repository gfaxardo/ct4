# Guía de Instalación Manual - CT4 Sistema de Identidad Canónica

## Pasos para Ejecutar la Aplicación

### Paso 1: Verificar Prerrequisitos

Asegúrate de tener instalado:
- ✅ Python 3.12 o superior
- ✅ Node.js 20 o superior
- ✅ npm (viene con Node.js)
- ✅ Acceso a la base de datos PostgreSQL remota (168.119.226.236)

Verificar versiones:
```bash
python --version
node --version
npm --version
```

---

### Paso 2: Configurar Backend

#### 2.1 Navegar al directorio backend
```bash
cd backend
```

#### 2.2 Crear entorno virtual
```bash
python -m venv venv
```

#### 2.3 Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

Después de activar, deberías ver `(venv)` al inicio de tu línea de comando.

#### 2.4 Instalar dependencias Python
```bash
pip install -r requirements.txt
```

Esto instalará: FastAPI, SQLAlchemy, Alembic, Pydantic, etc.

#### 2.5 Verificar configuración de base de datos

La configuración ya está lista con las credenciales correctas en:
- `backend/app/config.py`
- `backend/alembic.ini`

Si necesitas cambiarlas, edita estos archivos o crea un `.env` en `backend/`:
```env
DATABASE_URL=postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral
LOG_LEVEL=INFO
```

#### 2.6 Aplicar migraciones de base de datos

Desde el directorio `backend/` (con el venv activado):
```bash
alembic upgrade head
```

Esto creará los schemas `canon` y `ops` y todas las tablas necesarias.

**✅ Verificación:** Si todo salió bien, verás mensajes de Alembic confirmando las migraciones.

#### 2.7 Ejecutar el backend

Mantén el entorno virtual activado y ejecuta:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**✅ Verificación:** Deberías ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Deja esta terminal abierta** - El backend debe seguir corriendo.

**Probar backend:**
- Health check: http://localhost:8000/health
- API Docs: http://localhost:8000/docs

---

### Paso 3: Configurar Frontend

Abre **una nueva terminal** (el backend debe seguir corriendo en la primera).

#### 3.1 Navegar al directorio frontend
```bash
cd frontend
```

#### 3.2 Instalar dependencias Node.js
```bash
npm install
```

Esto puede tomar unos minutos la primera vez. Instalará: Next.js, React, TypeScript, Tailwind, etc.

#### 3.3 (Opcional) Configurar URL del API

Si el backend corre en otro puerto o host, crea `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Por defecto ya usa `http://localhost:8000`, así que este paso es opcional.

#### 3.4 Ejecutar el frontend
```bash
npm run dev
```

**✅ Verificación:** Deberías ver:
```
- ready started server on 0.0.0.0:3000, url: http://localhost:3000
- event compiled client and server successfully
```

**Deja esta terminal abierta** - El frontend debe seguir corriendo.

---

### Paso 4: Acceder a la Aplicación

Abre tu navegador y ve a:

- **Frontend:** http://localhost:3000
- **Backend API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

### Paso 5: Ejecutar una Ingesta

Una vez que la aplicación esté corriendo:

1. Ve al frontend: http://localhost:3000
2. Haz clic en "Corridas" en el menú
3. Haz clic en el botón "Ejecutar Ingesta"
4. Espera a que termine (puede tardar según la cantidad de datos)

O desde la línea de comandos:
```bash
curl -X POST http://localhost:8000/api/v1/identity/run
```

---

## Resumen de Comandos Rápidos

### Terminal 1 - Backend:
```bash
cd backend
venv\Scripts\activate          # Windows
# o: source venv/bin/activate  # Linux/Mac
uvicorn app.main:app --reload
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

---

## Solución de Problemas Comunes

### ❌ Error: "No module named 'app'"
**Solución:** Asegúrate de estar en el directorio `backend/` cuando ejecutas uvicorn, y que el venv esté activado.

### ❌ Error: "Could not connect to database"
**Solución:** 
- Verifica que la IP `168.119.226.236` sea accesible desde tu red
- Verifica que el firewall permita conexiones al puerto 5432
- Verifica las credenciales en `backend/app/config.py`

### ❌ Error: "alembic: command not found"
**Solución:** Asegúrate de que el venv esté activado y que hayas ejecutado `pip install -r requirements.txt`

### ❌ Error: "Module not found" en frontend
**Solución:** Ejecuta `npm install` nuevamente en el directorio `frontend/`

### ❌ Error: "Port 8000 already in use"
**Solución:** Cierra el proceso que usa el puerto 8000, o cambia el puerto:
```bash
uvicorn app.main:app --port 8001 --reload
```
Y actualiza `NEXT_PUBLIC_API_URL` en el frontend.

### ❌ Error: "Port 3000 already in use"
**Solución:** Next.js te preguntará si quieres usar otro puerto, o cierra el proceso que usa el puerto 3000.

### ❌ Las migraciones fallan
**Solución:** 
- Verifica la conexión a la base de datos
- Asegúrate de tener permisos para crear schemas
- Verifica que la base de datos `yego_integral` exista

---

## Estructura de Carpetas Después de la Instalación

```
CT4/
├── backend/
│   ├── venv/              ← Se crea después de python -m venv venv
│   ├── app/
│   ├── alembic/
│   └── requirements.txt
└── frontend/
    ├── node_modules/      ← Se crea después de npm install
    ├── .next/             ← Se crea después de npm run dev
    ├── app/
    └── package.json
```

---

## Detener la Aplicación

Para detener los servicios:
1. En cada terminal, presiona `Ctrl + C`
2. Para desactivar el venv de Python: `deactivate` (opcional)

---

## Re-ejecutar la Aplicación (Después del Primer Setup)

Una vez configurado todo, solo necesitas:

**Terminal 1:**
```bash
cd backend
venv\Scripts\activate  # o source venv/bin/activate en Linux/Mac
uvicorn app.main:app --reload
```

**Terminal 2:**
```bash
cd frontend
npm run dev
```

No necesitas volver a ejecutar `pip install` ni `npm install` a menos que actualices las dependencias.

---

## Verificar que Todo Funciona

1. ✅ Backend corriendo: http://localhost:8000/health devuelve `{"status":"ok"}`
2. ✅ Frontend corriendo: http://localhost:3000 se abre sin errores
3. ✅ Base de datos: Las migraciones se aplicaron correctamente
4. ✅ API Docs: http://localhost:8000/docs muestra la documentación interactiva

---

¡Listo! Tu aplicación debería estar corriendo correctamente.




