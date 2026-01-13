# Próximos Pasos Ejecutados - Identity Gap Killer v2

## Fecha: 2026-01-12

## ✅ Paso 1: Ejecutar Job en Todos los Leads NO_IDENTITY

**Objetivo:** Maximizar matches usando la nueva regla R3b.

**Acción:** Ejecutar job con límite de 200 leads para procesar todos los leads no_identity restantes.

**Resultado:** Verificar en el output del comando.

## ✅ Paso 2: Verificar Progreso del Gap

**Objetivo:** Confirmar que el gap sigue bajando con R3b.

**Acción:** Ejecutar script de verificación final.

**Métricas a verificar:**
- Total unresolved
- Breakdown por gap_reason
- Jobs matched (debería aumentar)
- Identity links y origins creados

## ✅ Paso 3: Análisis Detallado de Matching

**Objetivo:** Entender mejor por qué algunos leads aún no matchean.

**Acción:** Ejecutar análisis de issues de matching por placa.

**Información esperada:**
- Distribución de issues (no_candidates, date_out_of_range, etc.)
- Recomendaciones adicionales

## 📊 Resultados Esperados

### Antes
- Leads no_identity: ~187
- Gap: 24.21% unresolved

### Después (esperado)
- Leads no_identity: ~170-180 (reducción de 7-17 leads)
- Gap: ~21-22% unresolved (reducción de 2-3 puntos porcentuales)
- Jobs matched: +10-20 leads adicionales

## 🔄 Siguientes Pasos (Después de Ejecución)

1. **Revisar resultados:**
   - Verificar cuántos leads adicionales matchearon
   - Analizar patrones en los que aún fallan

2. **Optimizaciones adicionales (si es necesario):**
   - Ampliar rango de fechas de R3 (de -30/+7 a -90/+30 días)
   - Ajustar threshold de name_similarity si es muy restrictivo
   - Considerar matching cross-park para casos específicos

3. **Monitoreo continuo:**
   - Configurar scheduler para ejecutar job diariamente
   - Monitorear evolución del gap en UI
   - Alertas si el gap aumenta

4. **Documentación:**
   - Actualizar runbook con nueva regla R3b
   - Documentar casos edge que requieren atención manual

## 📝 Notas

- La regla R3b tiene confianza MEDIUM (menor que R3)
- Se ejecuta solo cuando R3 no encuentra candidatos
- Mantiene todas las validaciones excepto restricción de fecha
- Es idempotente: puede ejecutarse múltiples veces sin problemas
