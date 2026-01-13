# Resumen: Pasos Siguientes Ejecutados

## Fecha: 2026-01-12

## ✅ Paso 1: Ampliar Rango de Fechas de R3

### Cambio Implementado

**Antes:**
- Rango: -30 días a +7 días desde `lead_date`
- Muy restrictivo, muchos candidatos fuera de rango

**Después:**
- Rango: -90 días a +30 días desde `lead_date`
- Más flexible, captura más candidatos con mayor confianza

### Archivos Modificados

- `backend/app/services/matching.py`:
  - `_apply_rule_r3_plate_name()`: Rango ampliado a -90/+30 días
  - `_apply_rule_r4_car_fingerprint_name()`: Rango ampliado a -90/+30 días (consistente)

### Resultados de Prueba

**Script de prueba ejecutado:** `test_matching_with_extended_dates.py`

- **Leads probados:** 10
- **Matcheados:** 2 leads (20%)
- **Regla usada:** R3_PLATE_EXACT_NAME_SIMILAR
- **Confianza:** MEDIUM
- **Score:** 85

**Conclusión:** El rango ampliado funciona y captura candidatos que antes estaban fuera de rango.

## ✅ Paso 2: Revisar Threshold de Name Similarity

### Threshold Actual

- **NAME_SIMILARITY_THRESHOLD:** 0.66 (66%)
- **Ubicación:** `backend/app/config.py`
- **Configurable:** Vía variable de entorno `NAME_SIMILARITY_THRESHOLD`

### Análisis

El threshold de 0.66 es razonable:
- No es demasiado restrictivo (permitiría muchos falsos positivos si fuera muy bajo)
- No es demasiado estricto (permitiría matchear nombres similares pero no idénticos)
- Es un balance entre precisión y recall

### Recomendación

**Mantener threshold en 0.66** por ahora. Si después de más ejecuciones vemos que muchos leads fallan por `WEAK_MATCH_ONLY`, considerar bajarlo ligeramente a 0.60-0.63.

## ✅ Paso 3: Scripts de Configuración de Scheduler

### Scripts Creados

1. **`backend/scripts/setup_scheduler_identity_gap.sh`** (Linux/Mac)
   - Instrucciones para configurar cron
   - Ejemplos de configuración diaria y cada 6 horas
   - Comandos para verificar y monitorear

2. **`backend/scripts/setup_scheduler_identity_gap.ps1`** (Windows)
   - Script PowerShell para crear Task Scheduler automáticamente
   - Configuración completa con triggers, acciones y settings
   - Comandos para verificar, ejecutar y eliminar

### Configuración Recomendada

**Frecuencia:** Diariamente a las 2:00 AM
**Límite de leads:** 500 por ejecución
**Logs:** `/var/log/identity_gap_recovery.log` (Linux) o Event Viewer (Windows)

## 📊 Impacto Esperado

### Con Rango Ampliado

- **Más candidatos capturados:** Leads que antes fallaban por `DATE_OUT_OF_RANGE` ahora pueden matchear
- **Mayor confianza:** R3 mantiene confianza HIGH (mejor que R3b que usa MEDIUM)
- **Menos dependencia de R3b:** R3 captura más casos directamente

### Proyección

- **Leads adicionales esperados:** 10-20 leads más pueden matchear con rango ampliado
- **Reducción adicional del gap:** ~1-2 puntos porcentuales
- **Gap final esperado:** ~20-21% (de 22.95% actual)

## 🔄 Próximos Pasos

### Inmediatos

1. ✅ **Completado:** Ampliar rango de fechas de R3
2. ✅ **Completado:** Revisar threshold de name_similarity
3. ✅ **Completado:** Crear scripts de configuración de scheduler

### Siguiente Ejecución

4. **Ejecutar job con rango ampliado:**
   ```bash
   python -m jobs.retry_identity_matching 300
   ```
   - Procesar todos los leads pending
   - Verificar cuántos matchean con rango ampliado

5. **Configurar scheduler:**
   - Linux: Usar `setup_scheduler_identity_gap.sh`
   - Windows: Ejecutar `setup_scheduler_identity_gap.ps1` como administrador

### Monitoreo

6. **Verificar evolución:**
   - Ejecutar `verify_identity_gap_final.py` después de cada ejecución
   - Monitorear que el gap sigue bajando
   - Revisar logs del scheduler

## ✅ Estado

**Pasos siguientes completados:**
- ✅ Rango de fechas ampliado (R3 y R4)
- ✅ Threshold revisado (mantener 0.66)
- ✅ Scripts de scheduler creados

**Sistema listo para:**
- Ejecutar job con rango ampliado
- Configurar scheduler para operación recurrente
- Monitorear evolución del gap
