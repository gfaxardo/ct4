# Limpieza de Cache y Reinicio - Frontend CT4

## Problema
Los links "Pagos" y "Liquidaciones" no aparecen en el navbar aunque están en el código.

## Solución: Limpiar Cache y Reiniciar

### Paso 1: Detener el servidor de desarrollo
Si está corriendo, presiona `Ctrl+C` en la terminal donde está ejecutándose `npm run dev`.

### Paso 2: Limpiar cache de Next.js
Ejecuta en PowerShell desde `frontend/`:

```powershell
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
```

### Paso 3: Reiniciar el servidor
```powershell
npm run dev
```

### Paso 4: Verificar en el navegador
1. Abre http://localhost:3000
2. Verifica que el navbar muestra: **Dashboard | Personas | Sin Resolver | Corridas | Pagos | Liquidaciones**
3. Si no aparecen, haz **hard refresh**: `Ctrl+Shift+R` (Windows) o `Cmd+Shift+R` (Mac)

### Paso 5: Probar rutas directamente
- http://localhost:3000/pagos
- http://localhost:3000/liquidaciones

## Verificación de Archivos

✅ **Archivos confirmados:**
- `frontend/app/layout.tsx` - Contiene links a /pagos y /liquidaciones (líneas 38-43)
- `frontend/app/pagos/page.tsx` - Existe y compila
- `frontend/app/liquidaciones/page.tsx` - Existe y compila

✅ **Estructura correcta:**
- Next.js 14 usa App Router por defecto
- Solo hay un layout.tsx (no hay layouts anidados que sobreescriban)
- Las rutas están en la estructura correcta: `app/pagos/page.tsx` y `app/liquidaciones/page.tsx`

## Si el problema persiste

1. Verifica que estás en el frontend correcto:
   ```powershell
   cd C:\cursor\CT4\frontend
   ```

2. Verifica que el servidor está corriendo en el puerto 3000:
   ```powershell
   netstat -ano | findstr :3000
   ```

3. Verifica que no hay errores de compilación en la consola del servidor

4. Limpia también node_modules si es necesario:
   ```powershell
   Remove-Item -Recurse -Force node_modules
   npm install
   ```



















