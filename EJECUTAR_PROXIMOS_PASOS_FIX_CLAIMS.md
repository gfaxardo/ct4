# Próximos Pasos: Fix Claims Cabinet 14d

## ✅ Estado Actual

- Fix aplicado exitosamente
- Vista de auditoría creada
- Verificación completada

## 📋 Próximos Pasos Recomendados

### 1. Monitorear Missing Claims

**Usar el endpoint de auditoría**:
```bash
curl http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary
```

**O consultar directamente**:
```sql
-- Resumen rápido (sin timeout)
SELECT 
    COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1,
    COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5,
    COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25
FROM ops.v_cabinet_claims_audit_14d
LIMIT 1;
```

### 2. Verificar Casos Específicos

**Drivers con trips>=5 deben tener M1 y M5**:
```sql
SELECT 
    a.driver_id,
    a.trips_in_14d,
    a.should_have_claim_m1,
    a.has_claim_m1,
    a.should_have_claim_m5,
    a.has_claim_m5
FROM ops.v_cabinet_claims_audit_14d a
WHERE a.trips_in_14d >= 5
    AND (a.should_have_claim_m1 = true OR a.should_have_claim_m5 = true)
LIMIT 10;
```

### 3. Optimizar Vista de Auditoría (Opcional)

Si la vista causa timeouts frecuentes, considerar:

**Opción A: Crear vista materializada**:
```sql
CREATE MATERIALIZED VIEW ops.mv_cabinet_claims_audit_14d AS
SELECT * FROM ops.v_cabinet_claims_audit_14d;

CREATE INDEX ON ops.mv_cabinet_claims_audit_14d(driver_id);
CREATE INDEX ON ops.mv_cabinet_claims_audit_14d(missing_claim_bucket);
```

**Opción B: Usar solo el endpoint** (ya optimizado)

### 4. Documentar en Producción

- Actualizar documentación del sistema
- Notificar al equipo de cobranza sobre el fix
- Establecer monitoreo regular de missing claims

## 🎯 Criterios de Éxito

- ✅ Missing claims < 5% del total de drivers elegibles
- ✅ Todos los drivers con trips>=5 tienen claims M1 y M5
- ✅ No hay dependencia de pago para generar claims
- ✅ Endpoint de auditoría funciona correctamente

## 📊 Métricas a Monitorear

1. **Missing Claims Rate**: % de drivers elegibles sin claims
2. **Claims Generation Rate**: % de drivers elegibles con claims generados
3. **Root Causes Distribution**: Distribución de root causes de missing claims
4. **Claims por Milestone**: Conteo de M1/M5/M25 generados

## 🔧 Scripts Disponibles

- `backend/scripts/apply_claims_fix.py` - Aplicar el fix
- `backend/scripts/verify_claims_fix_simple.py` - Verificación simple
- `backend/sql/ops/analyze_claims_audit_14d.sql` - Análisis detallado

## 📝 Notas

- La vista de auditoría puede ser costosa en queries complejas
- Usar el endpoint para consultas frecuentes
- Considerar crear índices si se usa la vista directamente
