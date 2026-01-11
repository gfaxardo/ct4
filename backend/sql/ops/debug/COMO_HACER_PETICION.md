# Cómo Hacer la Petición GET (3 Opciones Simples)

## ✅ OPCIÓN 1: Desde el Navegador (MÁS FÁCIL)

1. **Abre tu navegador** (Chrome, Edge, Firefox, etc.)
2. **Copia y pega esta URL** en la barra de direcciones:
   ```
   http://localhost:8000/api/v1/payments/cabinet/drivers?limit=100
   ```
3. **Presiona Enter**
4. Verás una respuesta JSON (puede verse feo en el navegador, pero está bien)

**Importante:** Asegúrate de que el backend esté corriendo primero.

---

## ✅ OPCIÓN 2: Usando el Frontend (si ya lo tienes abierto)

Si ya tienes el frontend abierto en `http://localhost:3000`:

1. Ve a la ruta: `/pagos/claims`
2. Esto automáticamente hará la petición al endpoint y generará los logs

---

## ✅ OPCIÓN 3: Desde PowerShell (para usuarios avanzados)

1. Abre PowerShell
2. Ejecuta este comando:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/payments/cabinet/drivers?limit=100" -Method Get
```

---

## ⚠️ IMPORTANTE: Antes de hacer la petición

**Asegúrate de que el backend esté corriendo:**

1. Abre una terminal
2. Ve al directorio backend:
   ```powershell
   cd "C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend"
   ```
3. Activa el entorno virtual:
   ```powershell
   venv\Scripts\activate
   ```
4. Ejecuta el servidor:
   ```powershell
   uvicorn app.main:app --reload
   ```

Deberías ver algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 📝 Después de hacer la petición

Los logs se generarán automáticamente en:
```
c:\Users\Pc\Documents\Cursor Proyectos\ct4\.cursor\debug.log
```

Puedes abrir este archivo con cualquier editor de texto para ver los datos capturados.





