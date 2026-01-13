# URL CORRECTA para el Endpoint

El router `yango_payments` está registrado con el prefijo `/yango`, por lo que la URL completa es:

## ✅ URL CORRECTA:
```
http://localhost:8000/api/v1/yango/payments/cabinet/drivers?limit=100
```

Nota: Tiene `/yango/` antes de `/payments/`

## ❌ URL INCORRECTA (la que estabas usando):
```
http://localhost:8000/api/v1/payments/cabinet/drivers?limit=100
```

---

## Instrucciones:

1. **Copia esta URL en tu navegador:**
   ```
   http://localhost:8000/api/v1/yango/payments/cabinet/drivers?limit=100
   ```

2. **Presiona Enter**

3. **Deberías ver una respuesta JSON** (no el error "Not Found")

Los logs se generarán automáticamente en: `c:\Users\Pc\Documents\Cursor Proyectos\ct4\.cursor\debug.log`







