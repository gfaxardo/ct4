# Instrucciones para Reproducir el Bug y Capturar Logs

## Paso 1: Reiniciar el Backend
Si el backend está corriendo, reinícialo para que cargue el código con instrumentación:
```bash
# Detener el servidor (Ctrl+C)
# Reiniciar el servidor backend
cd backend
python -m uvicorn app.main:app --reload
```

## Paso 2: Acceder al Endpoint Problemático
Abre el frontend en `/pagos/claims` o haz una petición directa al endpoint:

```bash
# Opción 1: Desde el navegador
# Navegar a: http://localhost:3000/pagos/claims

# Opción 2: Desde curl/Postman
curl "http://localhost:8000/api/v1/payments/cabinet/drivers?limit=100"
```

El endpoint automáticamente capturará datos de los drivers problemáticos:
- b264635aea6c41c7b14b481b02d8cb09 (Oscar Sanabria)
- 88881990913f4b8181ff342c99635452 (Alexander Anaya)  
- 3d809fc2cca64071a46dabe3223e314c (Prado Wilfredo)

## Paso 3: Revisar los Logs
Los logs se escriben en: `c:\Users\Pc\Documents\Cursor Proyectos\ct4\.cursor\debug.log`

El log contiene:
- **Hipótesis A**: Datos RAW de la vista (cuántas filas por milestone, montos)
- **Hipótesis B**: expected_total después de la agregación

## Paso 4: Analizar Resultados
Buscar en los logs:
1. Si `n_rows > 1` para algún milestone → hay duplicados (vista no actualizada o problema upstream)
2. Si `expected_amounts` contiene valores != {25, 35, 100} → montos no corregidos
3. Si la vista tiene datos correctos pero `expected_total = 195` → problema en agregación




