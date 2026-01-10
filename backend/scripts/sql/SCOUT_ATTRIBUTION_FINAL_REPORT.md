# Scout Attribution Fix - Reporte Final Completo

**Fecha de ejecución**: 2026-01-09  
**Estado**: COMPLETADO EXITOSAMENTE

## Resumen Ejecutivo

El proceso de Scout Attribution Fix se ejecutó completamente sin errores. Todas las vistas, backfills y verificaciones se completaron correctamente.

## Estadísticas Clave

### Cobertura Scout Satisfactorio

- **Total scouting_daily con scout_id**: 609
- **Con lead_ledger scout satisfactorio**: 367
- **% Cobertura**: 60.26%

**✅ OBJETIVO CUMPLIDO**: La cobertura ya NO es 0%. Se alcanzó 60.26% de cobertura satisfactorio.

### Cobranza Yango con Scout

- **Total claims**: 417
- **Claims con scout**: 363
- **% Cobertura**: 87.05%
- **Por calidad**:
  - SATISFACTORY_LEDGER: 363 (87.05%)
  - MISSING: 54 (12.95%)

**✅ EXCELENTE**: 87% de los claims de cobranza Yango tienen scout asignado desde lead_ledger (source-of-truth).

## Conflictos Detectados

**Total conflictos**: 5 personas con múltiples scout_ids distintos

Estos requieren revisión manual:

1. Person: b3d8f553-28ca-48f6-a0cf-79ceeea58edc
   - Scouts: [10, 13, 23]
   - Registros: 3

2. Person: 10a37516-659b-4b96-a010-a479fbfd3f0d
   - Scouts: [10, 13]
   - Registros: 2

3. Person: 49877d22-cc19-4fec-a0a2-e14defffcd25
   - Scouts: [1, 20]
   - Registros: 2

4. Person: d49ce6e9-8d8d-44c1-ab3d-15e3780c3a92
   - Scouts: [19, 20]
   - Registros: 2

5. Person: d853c008-9758-4e0d-8bc4-42a5f4c392f0
   - Scouts: [9, 22]
   - Registros: 2

**Acción requerida**: Revisar manualmente estos 5 conflictos y decidir qué scout_id usar para cada person_key.

## Categorías de Personas Sin Scout

| Categoría | Cantidad | Descripción |
|-----------|----------|-------------|
| C | 1,313 | Sin events ni ledger (legacy/externo) |
| A | 193 | Tiene lead_events pero sin scout_id |
| D | 168 | Scout en events pero no en ledger |
| B | 2 | Tiene lead_ledger sin scout (attribution_rule indica unassigned/bucket) |

**Total personas sin scout**: 1,676 (de 2,033 totales)

### Análisis por Categoría

- **Categoría D (168)**: Scout en events pero no en ledger
  - **Acción**: Estos deberían haberse propagado en el backfill. Verificar por qué no se actualizaron.
  - **Posible causa**: Ya tienen attributed_scout_id en ledger pero diferente, o no cumplen la condición de scout único.

- **Categoría A (193)**: Tiene lead_events pero sin scout_id
  - **Acción**: Revisar si se puede inferir scout desde cabinet_leads con mapping 1:1.
  - **Vista de alertas**: `ops.v_cabinet_leads_missing_scout_alerts`

- **Categoría C (1,313)**: Legacy/externo
  - **Acción**: Estos son registros que no tienen eventos ni ledger. Pueden ser drivers legacy o externos que no pasaron por el pipeline normal.

## Vistas Creadas

Todas las vistas se crearon exitosamente:

### Vistas de Atribución
- `ops.v_scout_attribution_raw` - Vista RAW con todas las fuentes
- `ops.v_scout_attribution` - Vista canónica (1 fila por person_key)
- `ops.v_scout_attribution_conflicts` - Vista de conflictos

### Vistas de Diagnóstico
- `ops.v_persons_without_scout_categorized` - Categorización de personas sin scout
- `ops.v_cabinet_leads_missing_scout_alerts` - Alertas de cabinet_leads sin scout

### Vistas de Integración
- `ops.v_yango_collection_with_scout` - Cobranza Yango extendida con scout
- `ops.v_scout_daily_expected_base` - Base para liquidación diaria scout

## Backfills Ejecutados

### Identity Links Scouting Daily
- **Script**: `backfill_identity_links_scouting_daily.py`
- **Estado**: Completado
- **Resultado**: 0 nuevos registros creados (ya existían todos o no había candidatos)

### Lead Ledger Attributed Scout
- **Script**: `20_backfill_lead_ledger_attributed_scout.sql`
- **Estado**: Completado
- **Resultado**: 0 registros actualizados
- **Razón**: Los candidatos ya tenían attributed_scout_id o tenían múltiples scouts (conflictos)

### Cabinet Leads → Events
- **Script**: `21_backfill_lead_events_scout_from_cabinet_leads.sql`
- **Estado**: Completado
- **Resultado**: Vista de alertas creada (no se pudo inferir 1:1)

## Próximos Pasos Recomendados

### 1. Revisar y Resolver Conflictos

```sql
-- Revisar conflictos en detalle
SELECT * FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_records DESC;
```

Para cada conflicto:
- Revisar las fuentes y fechas de atribución
- Decidir qué scout_id es el correcto
- Actualizar `lead_ledger.attributed_scout_id` manualmente si es necesario

### 2. Investigar Categoría D (Scout en events pero no en ledger)

```sql
-- Ver ejemplos de categoría D
SELECT * FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'D: Scout en events pero no en ledger'
ORDER BY events_with_scout_count DESC
LIMIT 20;
```

Posibles razones por las que no se propagaron:
- Tienen múltiples scouts en eventos (conflictos)
- Ya tienen attributed_scout_id diferente en ledger
- No tienen entrada en lead_ledger

### 3. Enriquecer Categoría A (Events sin scout_id)

```sql
-- Revisar alertas de cabinet_leads sin scout
SELECT * FROM ops.v_cabinet_leads_missing_scout_alerts
ORDER BY event_date DESC;
```

Si existe mapping 1:1 `referral_link_id → scout_id`, implementar backfill.

### 4. Validar en UI

- Verificar que `ops.v_yango_collection_with_scout` se muestra correctamente en la UI de cobranza
- Verificar que los 363 claims con scout se muestran con scout_id
- Verificar buckets de calidad

### 5. Monitorear Cobertura

- Establecer alertas si la cobertura baja del 60%
- Monitorear nuevos conflictos (ejecutar verify periódicamente)

## Métricas de Éxito

✅ **Cobertura satisfactorio > 0%**: CUMPLIDO (60.26%)  
✅ **Vista de cobranza Yango con scout**: CUMPLIDA (87.05% cobertura)  
✅ **Base para liquidación scout**: LISTA  
⚠️ **Conflictos**: 5 detectados (requieren revisión manual)  
✅ **Vistas canónicas**: TODAS CREADAS  
✅ **Auditoría**: TABLAS CREADAS  

## Notas Técnicas

- Las tablas de auditoría están listas para rastrear futuros backfills
- Todas las vistas son idempotentes (se pueden recrear sin problemas)
- El proceso no rompió el flujo de cobro Yango existente
- Los backfills son segmentados y auditable

## Archivos Generados

- `backend/scripts/sql/SCOUT_ATTRIBUTION_AFTER_REPORT.md` - Reporte automático
- `backend/scripts/sql/SCOUT_ATTRIBUTION_FINAL_REPORT.md` - Este reporte detallado

## Conclusiones

El fix de Scout Attribution se completó exitosamente. La infraestructura está lista para:
1. Atribución canónica de scouts
2. Integración con cobranza Yango
3. Base para liquidación diaria scout
4. Detección y resolución de conflictos

**Recomendación**: Proceder con la revisión manual de los 5 conflictos y luego avanzar con la construcción de C2/C3 scout claims para pagos.

