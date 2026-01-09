# Acciones Inmediatas: Módulo de Auditoría de Origen

## ⚠️ PROBLEMA CRÍTICO: ENUM en Backfill

### Error
```
invalid input value for enum origin_tag: "SCOUT_REGISTRATION"
```

### Causa
SQLAlchemy está usando el nombre del enum (`SCOUT_REGISTRATION`) en lugar del valor (`scout_registration`) al insertar.

### Solución Rápida

**Opción 1: Usar valores explícitos en el backfill** (RECOMENDADO)

Modificar `backend/scripts/backfill_identity_origin.py` línea 136:

```python
# ANTES:
origin_tag=origin_result.origin_tag,

# DESPUÉS:
origin_tag=OriginTag(origin_result.origin_tag.value) if isinstance(origin_result.origin_tag, str) else origin_result.origin_tag,
```

O mejor aún, asegurarse de que `origin_result.origin_tag` ya sea el enum correcto y SQLAlchemy lo maneje automáticamente.

**Opción 2: Usar native_enum=False** (Requiere migración)

Modificar el modelo para usar String en lugar de Enum nativo:

```python
origin_tag = Column(String, nullable=False)  # En lugar de Enum(OriginTag)
```

Luego convertir manualmente en el código.

**Opción 3: TypeDecorator personalizado** (Más robusto, similar a JobTypeEnum)

Crear un TypeDecorator que maneje la conversión automáticamente.

### Acción Inmediata

1. **Verificar el enum**: El enum `OriginTag` ya tiene `__str__` que devuelve `.value`, así que debería funcionar.
2. **Probar inserción directa**: Crear un registro de prueba para verificar si el problema persiste.
3. **Si persiste**: Usar Opción 1 (valores explícitos) como solución rápida.

## 📋 CHECKLIST DE ACCIONES

### ✅ Completado

- [x] Migraciones ejecutadas
- [x] Vistas SQL creadas
- [x] Modelos SQLAlchemy creados
- [x] Servicio de determinación implementado
- [x] Endpoints API creados
- [x] UI frontend implementada
- [x] Scripts de análisis creados
- [x] Documentación completa

### ⚠️ Pendiente (URGENTE)

- [ ] **Corregir problema de ENUM en backfill**
  - Tiempo estimado: 30 minutos
  - Impacto: Bloquea ejecución completa del backfill

- [ ] **Ejecutar backfill completo**
  - Tiempo estimado: 1-2 horas (depende de conexión)
  - Impacto: Crea registros de origen para 1,017 personas

- [ ] **Ejecutar script SQL para marcar legacy**
  - Tiempo estimado: 5 minutos
  - Impacto: Resuelve ~800-850 casos automáticamente
  - Script: `backend/scripts/mark_legacy_drivers.sql`

### 📅 Pendiente (Esta Semana)

- [ ] **Configurar LEAD_SYSTEM_START_DATE**
  - Verificar fecha real de arranque del sistema
  - Actualizar en `.env` y scripts SQL

- [ ] **Revisar casos restantes usando UI**
  - 902 casos de solo drivers (después de marcar legacy: ~50-100)
  - 300 casos de leads sin driver
  - 89 casos de múltiples tipos de leads
  - 628 casos otros

- [ ] **Verificar que vistas de negocio excluyan legacy/discarded**
  - Claims (C3)
  - Pagos (C4)
  - Exports

## 🔧 CORRECCIÓN DEL ENUM (Paso a Paso)

### Paso 1: Verificar el Problema

```python
# Test rápido
from app.models.canon import OriginTag
tag = OriginTag.SCOUT_REGISTRATION
print(tag)  # Debería imprimir "scout_registration"
print(tag.value)  # Debería imprimir "scout_registration"
```

### Paso 2: Si el problema persiste, modificar backfill

En `backend/scripts/backfill_identity_origin.py`, línea 136:

```python
origin = IdentityOrigin(
    person_key=person_key,
    origin_tag=OriginTag(origin_result.origin_tag.value) if hasattr(origin_result.origin_tag, 'value') else OriginTag(origin_result.origin_tag),
    # ... resto de campos
)
```

### Paso 3: Probar con un caso

```bash
python backend/scripts/backfill_identity_origin.py --execute --batch-size 1
```

## 📊 ESTADO ACTUAL DEL SISTEMA

### Base de Datos

- ✅ Tablas creadas: `canon.identity_origin`, `canon.identity_origin_history`, `ops.identity_origin_alert_state`
- ✅ Vistas creadas: `ops.v_identity_origin_audit`, `ops.v_identity_origin_alerts`
- ⚠️ Datos: Pendiente backfill completo

### Backend

- ✅ Modelos: Completos
- ✅ Servicios: `OriginDeterminationService` funcional
- ✅ Endpoints: Todos implementados
- ⚠️ Backfill: Requiere corrección de ENUM

### Frontend

- ✅ Tipos: Completos
- ✅ API Client: Completos
- ✅ UI: Páginas implementadas
- ⚠️ Testing: Pendiente verificación en navegador

## 🎯 OBJETIVOS DE ESTA SEMANA

1. **Lunes**: Corregir ENUM y ejecutar backfill completo
2. **Martes**: Ejecutar script SQL de legacy (~800 casos)
3. **Miércoles-Jueves**: Revisar casos restantes usando UI
4. **Viernes**: Configurar monitoreo y alertas

## 📝 NOTAS TÉCNICAS

### Sobre el ENUM

El problema puede estar en cómo PostgreSQL maneja los ENUMs nativos vs cómo SQLAlchemy los serializa. PostgreSQL espera valores exactos del enum, y SQLAlchemy puede estar usando el nombre del enum en lugar del valor.

**Solución temporal**: Usar `.value` explícitamente al asignar.

**Solución permanente**: Considerar usar `native_enum=False` y manejar como String, o crear TypeDecorator personalizado.

### Sobre el Backfill

El backfill procesa en lotes de 50 por defecto. Si hay problemas de conexión:
- Reducir `--batch-size` a 10 o 5
- Agregar retry logic
- Ejecutar en horarios de menor carga

### Sobre las Vistas

Las vistas `v_identity_origin_audit` y `v_identity_origin_alerts` pueden ser pesadas con muchos datos. Si el rendimiento es un problema:
- Considerar materializarlas
- Agregar índices adicionales
- Optimizar queries

## ✅ VERIFICACIÓN FINAL

Antes de considerar el módulo completamente operativo:

1. [ ] Backfill ejecutado sin errores
2. [ ] Script SQL de legacy ejecutado
3. [ ] UI accesible y funcional
4. [ ] Endpoints API respondiendo correctamente
5. [ ] Vistas SQL retornando datos correctos
6. [ ] Casos restantes < 100 (después de marcar legacy)

## 🚀 PRÓXIMOS PASOS DESPUÉS DE CORRECCIÓN

1. Ejecutar backfill completo
2. Ejecutar script SQL de legacy
3. Verificar resultados en UI
4. Configurar monitoreo continuo
5. Documentar proceso de operación

---

**Última actualización**: 2025-01-21
**Estado**: ⚠️ Requiere corrección de ENUM antes de continuar

