# CT4 Ops Health — Reporte de Auditoría Automática
**Fecha:** 2026-01-01 22:26:38
**Estado:** CRITICAL

---
## Resumen Ejecutivo
- **Estado Global:** ERROR
- **Errores:** 2
- **Advertencias:** 3
- **OK:** 3
- **Objetos Descubiertos:** 170
- **Objetos Registrados:** 170
- **Objetos No Registrados:** 0
- **Objetos Faltantes:** 0

---
## Checks Fallidos

| Check | Severidad | Estado | Mensaje |
|-------|-----------|--------|----------|
| `raw_data_critical_stale` | 🔴 error | ERROR | Fuentes RAW con retraso crítico > 5 días: module_ct_scouting_daily, module_ct_scouts_list, yango_pay... |
| `raw_data_health_errors` | 🔴 error | ERROR | Fuentes RAW con estado de error: module_ct_scout_drivers, module_ct_scouting_daily, summary_daily... |
| `mv_refresh_stale` | 🟡 warning | WARN | MVs sin refrescar > 24h: mv_driver_name_index, mv_drivers_park_08e20910d81d42658d4334d3f6d10ac0, mv_... |
| `raw_data_health_warnings` | 🟡 warning | WARN | Fuentes RAW con advertencias: yango_payment_ledger... |
| `raw_data_stale` | 🟡 warning | WARN | Fuentes RAW con retraso > 2 días: module_ct_scouting_daily, module_ct_scouts_list, yango_payment_led... |

---
## Recomendaciones Automáticas

### Acciones Inmediatas:

- **raw_data_critical_stale**: Fuentes RAW con retraso crítico > 5 días: module_ct_scouting_daily, module_ct_scouts_list, yango_payment_ledger
  - Ver detalles: /ops/health?tab=raw
- **raw_data_health_errors**: Fuentes RAW con estado de error: module_ct_scout_drivers, module_ct_scouting_daily, summary_daily
  - Ver detalles: /ops/health?tab=raw


---

*Reporte generado automáticamente el 2026-01-01 22:26:38*
