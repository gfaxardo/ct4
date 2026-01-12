# Resumen Ejecutivo: Sistema de Cobranza Yango - Cabinet

## 📋 Propósito de este Documento

Este documento explica el **racionamiento completo de la cobranza de Yango** desde la base del funnel hasta el cálculo de deudas, de manera que cualquier persona externa (incluyendo Yango) pueda entender:

- Cómo funciona el sistema de identidad canónica
- Cómo se generan los claims (reclamos de pago)
- Cómo se calculan los milestones y montos
- Cómo se determina qué se debe cobrar

---

## 🎯 Vista Ejecutiva Principal: Cobranza Yango

**La vista "Cobranza Yango - Cabinet Financial 14d" (`/pagos/cobranza-yango`) es EL CENTRO OPERATIVO PRINCIPAL de cobranza, control y futura conciliación de Yango.**

### Características Principales:

1. **Fuente Ejecutiva Única**: Esta es la única vista de "Cobranza Yango" visible en el menú principal. Todas las demás rutas relacionadas redirigen aquí.

2. **Display-Only de Scout**: Muestra la atribución de scout (quién trajo el registro) para visibilidad y filtros, sin definir dinero ni corregir reglas.

3. **Read-Only por Defecto**: Segura, auditable y exportable. No contiene acciones destructivas.

4. **Vista Gemela de Conciliación**: Existe una vista gemela admin/operativa en `/pagos/cobranza-yango/conciliacion` para conciliación futura, sin ensuciar la vista principal.

5. **Respeto Estricto a Capas Canónicas**: 
   - Consume C3 (Claims - obligación de pago expected)
   - Consume C4 (Pagos - dinero real / conciliación)
   - NO recalcula reglas de negocio

### Objetivo Funcional:
**Responder sin ambigüedad: "¿Qué conductores generan pago de Yango, cuánto nos deben, por qué (milestone), y qué scout lo trajo?"**

---

## 🎯 Visión General: El Funnel de Cobranza

El sistema de cobranza Yango sigue este flujo:

```
1. LEAD (Registro) 
   ↓ [GAP 1: Leads sin identidad]
2. IDENTIDAD (Matching de Persona)
   ↓ [GAP 2: Sin conversión]
3. CONVERSIÓN (Conexión y Viajes)
   ↓ [GAP 3: Sin milestones]
4. MILESTONES (Hitos de Viajes)
   ↓ [GAP 4: Sin claims]
5. CLAIMS (Reclamos de Pago)
   ↓ [GAP 5: Sin pagos]
6. PAGOS (Reconciliación)
   ↓
7. DEUDA (Lo que falta por cobrar)
```

### ⚠️ El Primer Gap del Embudo: Leads Sin Identidad

**Métrica Crítica**: Leads que se registraron en `module_ct_cabinet_leads` pero **no lograron tener identidad canónica ni generar pago**.

**Definición precisa:**
Estos son leads que:
- ✅ Se registraron en `module_ct_cabinet_leads` (BASE DEL EMBUDO)
- ❌ NO tienen `identity_links` (no se pudo hacer match de identidad en la ingesta)
- ❌ NO tienen `lead_events` con `person_key` válido (no pasaron a atribución)
- ❌ NO aparecen en `v_conversion_metrics` (filtra `WHERE person_key IS NOT NULL`)
- ❌ NO aparecen en `v_cabinet_financial_14d` (vista financiera final)
- ❌ NO tienen claims generados (no generaron pago)

**¿Por qué es importante?**
- Representa la **primera pérdida del embudo** desde la base (`module_ct_cabinet_leads`)
- Indica problemas en el proceso de matching de identidad durante la ingesta
- Puede indicar datos incompletos o inconsistentes en los leads
- Impacta directamente en la tasa de conversión de leads a pagos
- **Estos leads NO aparecen en ninguna vista financiera** (son completamente invisibles para cobranza)

**Causas comunes:**
1. **Datos incompletos**: Leads sin teléfono, sin placa, sin nombre completo
2. **Datos inconsistentes**: Información que no coincide con el catálogo de conductores (`public.drivers`)
3. **Leads nuevos**: Conductores que realmente no existen en el sistema del parque
4. **Errores de matching**: El sistema no pudo hacer match por falta de evidencia suficiente (ninguna de las 4 reglas aplicó)
5. **Leads no procesados**: Leads que aún no han pasado por el proceso de ingesta de identidad

**Impacto en el sistema:**
- Un lead sin identidad **NUNCA** generará claims
- Un lead sin identidad **NUNCA** aparecerá en la vista financiera
- Un lead sin identidad es **completamente invisible** para el sistema de cobranza

---

## 1️⃣ LEAD: El Punto de Entrada

### ¿Qué es un Lead?

Un **lead** es un registro de un conductor que se registró en la plataforma Yango. Este registro contiene información básica:

- **Nombre**: `first_name`, `middle_name`, `last_name`
- **Teléfono**: `park_phone`
- **Vehículo**: `asset_plate_number` (placa), `asset_model` (modelo)
- **Fecha de registro**: `lead_created_at`

### Fuente de Datos

Los leads provienen de la tabla `public.module_ct_cabinet_leads`, que se alimenta desde el sistema de Yango.

**Ejemplo:**
```
external_id: "abc123"
first_name: "Juan"
last_name: "Pérez"
park_phone: "+51987654321"
asset_plate_number: "ABC123"
lead_created_at: "2025-12-01 10:30:00"
```

### ¿Por qué es importante?

El `lead_created_at` se convierte en el **`lead_date`**, que es la fecha base para calcular:
- La ventana de 14 días para contar viajes
- Los milestones alcanzados
- Los montos a cobrar

---

## 2️⃣ IDENTIDAD: El Sistema de Matching

### El Problema

Un mismo conductor puede aparecer en múltiples sistemas con información ligeramente diferente:
- En Yango: "Juan Pérez" con teléfono "+51987654321"
- En el parque: "Juan Carlos Pérez" con teléfono "987654321"
- En scouting: "J. Pérez" con teléfono "987654321"

**¿Cómo sabemos que es la misma persona?**

### La Solución: Sistema de Identidad Canónica

El sistema crea una **identidad única** (`person_key`) para cada persona real, independientemente de cómo aparezca en diferentes fuentes.

### Proceso de Matching

El sistema intenta hacer "match" (conciliar) cada lead con una persona existente usando **4 reglas en orden de prioridad**:

#### **Regla 1: Teléfono Exacto** (Score: 95, Confianza: ALTA)
- Si el teléfono del lead coincide exactamente con el de una persona existente → **MATCH**
- **Ejemplo**: Lead tiene "+51987654321" y existe una persona con ese mismo teléfono → Es la misma persona

#### **Regla 2: Licencia Exacta** (Score: 92, Confianza: ALTA)
- Si la licencia del lead coincide exactamente con la de una persona existente → **MATCH**
- **Ejemplo**: Lead tiene licencia "A123456" y existe una persona con esa licencia → Es la misma persona

#### **Regla 3: Placa + Nombre Similar** (Score: 85, Confianza: MEDIA)
- Si la placa coincide Y el nombre es similar (≥50% de similitud) → **MATCH**
- **Ejemplo**: Lead tiene placa "ABC123" y nombre "Juan Pérez", y existe una persona con placa "ABC123" y nombre "Juan Carlos Pérez" → Es la misma persona

#### **Regla 4: Marca+Modelo + Nombre Similar** (Score: 75, Confianza: BAJA)
- Si la marca+modelo del vehículo coinciden Y el nombre es similar (≥50% de similitud) → **MATCH**
- **Ejemplo**: Lead tiene vehículo "Toyota Yaris" y nombre "Juan Pérez", y existe una persona con vehículo "Toyota Yaris" y nombre "J. Pérez" → Es la misma persona

### Resultado del Matching

- **✅ MATCH ENCONTRADO**: El lead se vincula a una `person_key` existente → Se crea `identity_links` → **CONTINÚA en el embudo**
- **❌ SIN MATCH**: El lead NO se vincula a ninguna `person_key` → Se crea `identity_unmatched` → **NO CONTINÚA** (GAP 1)
- **⚠️ AMBIGUO**: Si múltiples personas matchean, se marca como "ambiguous" en `identity_unmatched` → **NO CONTINÚA** (GAP 1)

**IMPORTANTE**: Un lead sin `identity_links` (sin match) **NUNCA** aparecerá en:
- `lead_events` con `person_key` válido
- `v_conversion_metrics` (filtra `WHERE person_key IS NOT NULL`)
- `v_cabinet_financial_14d` (vista financiera)
- Claims generados

### ¿Por qué es crítico?

Sin identidad canónica, no podríamos:
- Saber si un conductor ya existe en el sistema
- Conciliar pagos con claims
- Calcular correctamente los milestones (un conductor podría tener múltiples cuentas)

---

## 3️⃣ CONVERSIÓN: Conexión y Viajes

### ¿Qué es la Conversión?

Una vez que tenemos un lead con identidad (desde `identity_links`), necesitamos saber:
1. **¿Se conectó el conductor?** (¿Empezó a trabajar?)
2. **¿Cuántos viajes completó?**

### Fuente de Datos: `observational.lead_events`

El sistema crea un **evento** por cada lead que tiene `identity_links`, almacenando:
- `event_date`: La fecha del lead (desde `lead_created_at`)
- `person_key`: La identidad canónica del conductor (desde `identity_links`)
- `source_table`: De dónde vino el lead (ej: "module_ct_cabinet_leads")

**⚠️ IMPORTANTE**: Solo se crean eventos para leads que tienen `identity_links`. 
Leads sin identidad NO tienen eventos con `person_key` válido.

### Fuente de Viajes: `public.summary_daily`

Esta tabla contiene el número de viajes completados por cada conductor cada día:
- `driver_id`: ID del conductor en el parque
- `date_file`: Fecha del día
- `count_orders_completed`: Número de viajes completados ese día

**⚠️ IMPORTANTE**: Para contar viajes, el sistema necesita:
1. `person_key` (desde `identity_links`)
2. `driver_id` (resuelto desde `identity_links` donde `source_table = 'drivers'`)

Si un lead tiene `person_key` pero NO tiene `driver_id` (no está en el parque), NO se pueden contar viajes y NO generará claims.

### Ventana de 14 Días

**Regla crítica**: Solo contamos viajes dentro de una **ventana de 14 días** desde el `lead_date`.

**Ejemplo:**
- Lead date: 1 de diciembre de 2025
- Ventana: 1 de diciembre a 14 de diciembre (14 días)
- Viajes del 15 de diciembre en adelante: **NO cuentan** para este lead

**¿Por qué 14 días?**
Es el acuerdo comercial con Yango: solo pagamos por conductores que se activan rápidamente (dentro de 14 días).

---

## 4️⃣ MILESTONES: Los Hitos de Pago

### ¿Qué son los Milestones?

Los **milestones** (hitos) son objetivos de viajes que, al alcanzarse, generan un pago de Yango. Son **acumulativos**:

### **M1: Primer Milestone** (1 viaje)
- **Objetivo**: Completar **1 viaje** dentro de 14 días desde el lead date
- **Pago**: **S/ 25.00**
- **Condición**: El conductor debe completar al menos 1 viaje en la ventana de 14 días

### **M5: Segundo Milestone** (5 viajes)
- **Objetivo**: Completar **5 viajes** dentro de 14 días desde el lead date
- **Pago**: **S/ 35.00 adicionales** (total acumulado: S/ 60.00)
- **Condición**: El conductor debe completar al menos 5 viajes en la ventana de 14 días
- **Nota**: Si alcanza M5, automáticamente alcanzó M1 (por eso es acumulativo)

### **M25: Tercer Milestone** (25 viajes)
- **Objetivo**: Completar **25 viajes** dentro de 14 días desde el lead date
- **Pago**: **S/ 100.00 adicionales** (total acumulado: S/ 160.00)
- **Condición**: El conductor debe completar al menos 25 viajes en la ventana de 14 días
- **Nota**: Si alcanza M25, automáticamente alcanzó M1 y M5

### Ejemplo Práctico

**Conductor: Juan Pérez**
- Lead date: 1 de diciembre de 2025
- Ventana: 1-14 de diciembre (14 días)
- Viajes completados en la ventana: 30 viajes

**Resultado:**
- ✅ Alcanzó M1 (1 viaje) → S/ 25.00
- ✅ Alcanzó M5 (5 viajes) → S/ 35.00 adicionales
- ✅ Alcanzó M25 (25 viajes) → S/ 100.00 adicionales
- **Total esperado de Yango: S/ 160.00**

### ¿Qué pasa si no alcanza un milestone?

Si un conductor no alcanza un milestone dentro de los 14 días, **no genera pago por ese milestone**.

**Ejemplo:**
- Lead date: 1 de diciembre
- Viajes en ventana (1-14 dic): 3 viajes
- **Resultado**: Solo alcanzó M1 → S/ 25.00 (NO alcanzó M5 ni M25)

---

## 5️⃣ CLAIMS: Los Reclamos de Pago

### ¿Qué es un Claim?

Un **claim** es un **reclamo formal** de que Yango debe pagar un monto específico por un milestone alcanzado.

### Estructura de un Claim

Cada claim contiene:
- `driver_id`: ID del conductor
- `person_key`: Identidad canónica del conductor
- `milestone_value`: 1, 5, o 25
- `expected_amount`: Monto esperado (S/ 25, S/ 35, o S/ 100)
- `lead_date`: Fecha base del lead
- `pay_week_start_monday`: Semana de pago (lunes de la semana)

### Generación de Claims

Los claims se generan automáticamente cuando:
1. ✅ Un lead tiene `identity_links` (pasó la ingesta de identidad) → Tiene `person_key`
2. ✅ El lead tiene `driver_id` (está en el parque) → Resuelto desde `identity_links`
3. ✅ El conductor alcanza un milestone dentro de la ventana de 14 días
4. ✅ El sistema verifica que el milestone es válido (dentro de la ventana)
5. ✅ Se crea un registro en `ops.v_claims_payment_status_cabinet`

**⚠️ REQUISITOS CRÍTICOS**:
- Sin `identity_links` → NO hay `person_key` → NO hay `lead_events` válido → NO hay claim
- Sin `driver_id` → NO se pueden contar viajes → NO hay milestones → NO hay claim

### Ejemplo de Claims Generados

**Conductor: Juan Pérez (driver_id: "12345")**
- Lead date: 1 de diciembre de 2025
- Viajes en ventana: 30 viajes

**Claims generados:**
1. Claim M1: driver_id="12345", milestone=1, expected_amount=S/ 25.00
2. Claim M5: driver_id="12345", milestone=5, expected_amount=S/ 35.00
3. Claim M25: driver_id="12345", milestone=25, expected_amount=S/ 100.00

**Total de claims: 3 claims por S/ 160.00**

---

## 6️⃣ PAGOS: La Reconciliación

### ¿Qué son los Pagos?

Los **pagos** son registros de que Yango **efectivamente pagó** un monto. Provienen de la tabla `public.module_ct_cabinet_payments`.

### Estructura de un Pago

Cada pago contiene:
- `source_pk`: ID del pago en el sistema de Yango
- `driver_name`: Nombre del conductor (puede variar)
- `trip_1`: Flag indicando si pagó M1
- `trip_5`: Flag indicando si pagó M5
- `trip_25`: Flag indicando si pagó M25
- `paid_amount`: Monto pagado
- `pay_date`: Fecha del pago

### Proceso de Reconciliación

El sistema **reconcilia** (hace match) entre:
- **Claims esperados** (lo que deberíamos recibir)
- **Pagos recibidos** (lo que Yango pagó)

### Matching de Pagos con Claims

El sistema intenta hacer match usando:
1. **Preferido**: `driver_id` + `milestone_value`
   - Si el pago tiene el mismo `driver_id` y `milestone_value` que un claim → **MATCH**
2. **Fallback**: `person_key` + `milestone_value`
   - Si no hay match por `driver_id`, intenta por `person_key` (identidad canónica)

### Estados de Reconciliación

- **✅ PAGADO**: Claim tiene match con un pago confirmado
- **⏳ PENDIENTE**: Claim existe pero no hay pago (o el pago no está confirmado)
- **⚠️ ANOMALÍA**: Pago existe pero no hay claim correspondiente

---

## 7️⃣ DEUDA: Lo que Falta por Cobrar

### ¿Qué es la Deuda?

La **deuda** es la diferencia entre:
- **Esperado**: Suma de todos los `expected_amount` de claims
- **Pagado**: Suma de todos los montos pagados confirmados

### Cálculo de Deuda

```
Deuda = Total Esperado - Total Pagado
```

**Ejemplo:**
- Total esperado (todos los claims): S/ 10,000.00
- Total pagado (pagos confirmados): S/ 6,000.00
- **Deuda: S/ 4,000.00**

### Vista Financiera: `ops.v_cabinet_financial_14d`

Esta vista es la **fuente de verdad financiera** que muestra, por cada conductor:

- `expected_total_yango`: Total esperado (suma de todos los milestones alcanzados)
- `total_paid_yango`: Total pagado (suma de pagos confirmados)
- `amount_due_yango`: Deuda pendiente (expected - paid)

### Ejemplo de Vista Financiera

**Conductor: Juan Pérez**
- Lead date: 1 de diciembre de 2025
- Viajes en ventana: 30 viajes
- Milestones alcanzados: M1, M5, M25
- Expected total: S/ 160.00
- Paid M1: S/ 25.00 ✅
- Paid M5: S/ 35.00 ✅
- Paid M25: S/ 0.00 ❌ (pendiente)
- **Total pagado: S/ 60.00**
- **Deuda: S/ 100.00** (falta el pago de M25)

---

## 📊 Flujo de Datos Completo (Base: module_ct_cabinet_leads)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. BASE DEL EMBUDO: module_ct_cabinet_leads                 │
│    ✅ Todos los leads registrados desde Yango                │
│    📊 Esta es la base de todas las métricas                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. INGESTA DE IDENTIDAD (process_cabinet_leads)              │
│    - Lee de module_ct_cabinet_leads                         │
│    - Matching con personas existentes (4 reglas)             │
│    - ✅ MATCH: Crea canon.identity_links                     │
│    - ❌ SIN MATCH: Crea canon.identity_unmatched             │
│    📊 GAP 1: Leads sin identity_links                        │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Solo leads con identity_links)
┌─────────────────────────────────────────────────────────────┐
│ 3. ATRIBUCIÓN DE LEADS (populate_events_from_cabinet)        │
│    - Lee de module_ct_cabinet_leads                         │
│    - Busca identity_links para obtener person_key           │
│    - Crea observational.lead_events                          │
│    - ⚠️ Si NO hay identity_links → person_key = NULL         │
│    📊 lead_events con person_key = NULL NO continúan        │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Solo lead_events con person_key IS NOT NULL)
┌─────────────────────────────────────────────────────────────┐
│ 4. MÉTRICAS DE CONVERSIÓN (v_conversion_metrics)            │
│    - Filtra: WHERE person_key IS NOT NULL                    │
│    - Resuelve driver_id desde identity_links                 │
│    - Calcula viajes en ventana de 14 días                   │
│    - Determina milestones alcanzados                         │
│    📊 GAP 2: Leads sin driver_id (no están en parque)       │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Solo con driver_id IS NOT NULL)
┌─────────────────────────────────────────────────────────────┐
│ 5. CÁLCULO DE PAGOS (v_payment_calculation)                 │
│    - Filtra: WHERE driver_id IS NOT NULL                    │
│    - Genera claims por milestone alcanzado                  │
│    - Calcula montos esperados (S/ 25, 35, 100)              │
│    📊 GAP 3: Leads sin milestones alcanzados                │
└─────────────────────────────────────────────────────────────┘
                        ↓ (Solo con milestones alcanzados)
┌─────────────────────────────────────────────────────────────┐
│ 6. ESTADO DE PAGOS (v_claims_payment_status_cabinet)         │
│    - Agrega claims por (driver_id, milestone_value)          │
│    - Reconciliación con pagos de Yango                      │
│    - Determinación de estado (pagado/pendiente)             │
│    📊 GAP 4: Claims sin pagos confirmados                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. VISTA FINANCIERA FINAL (v_cabinet_financial_14d)          │
│    - Consolidación de todos los datos                        │
│    - Cálculo de deuda por conductor                          │
│    - ✅ SOLO muestra leads con identidad Y driver_id         │
│    📊 NO incluye leads sin identidad (GAP 1)                 │
└─────────────────────────────────────────────────────────────┘
```

### ⚠️ Puntos Críticos del Flujo

1. **Base del Embudo**: `module_ct_cabinet_leads` es la fuente única de verdad para todos los leads
2. **Filtro de Identidad**: `v_conversion_metrics` filtra `WHERE person_key IS NOT NULL` → Solo leads con identidad continúan
3. **Filtro de Driver**: `v_payment_calculation` filtra `WHERE driver_id IS NOT NULL` → Solo leads con driver_id generan claims
4. **Vista Financiera**: Solo muestra leads que pasaron ambos filtros (identidad + driver_id)

### 📊 Gaps del Embudo (desde module_ct_cabinet_leads)

- **GAP 1 (Crítico)**: Leads sin `identity_links` → NO aparecen en `lead_events` con person_key → NO en vista financiera
- **GAP 2**: Leads con identidad pero sin `driver_id` → NO generan claims
- **GAP 3**: Leads con driver_id pero sin milestones alcanzados → NO generan claims
- **GAP 4**: Claims generados pero sin pagos → Deuda pendiente

---

## 🔑 Conceptos Clave para Entender el Sistema

### 1. **Ventana de 14 Días**
- Solo cuenta viajes dentro de 14 días desde el `lead_date`
- Viajes fuera de esta ventana NO generan milestones
- Es el acuerdo comercial con Yango

### 2. **Milestones Acumulativos**
- M1, M5, M25 son acumulativos
- Si alcanzas M25, automáticamente alcanzaste M1 y M5
- Cada milestone genera un claim separado

### 3. **Identidad Canónica**
- Un conductor puede aparecer con diferentes nombres/teléfonos
- El sistema crea una `person_key` única para cada persona real
- Permite reconciliar pagos incluso si los nombres varían

### 4. **Claims vs Pagos**
- **Claims**: Lo que esperamos recibir (basado en milestones alcanzados)
- **Pagos**: Lo que Yango efectivamente pagó
- **Deuda**: Diferencia entre claims y pagos

### 5. **Reconciliación**
- El sistema hace match entre claims y pagos
- Usa `driver_id` + `milestone_value` como preferencia
- Usa `person_key` + `milestone_value` como fallback

---

## 📈 Métricas Clave del Sistema

### Resumen Ejecutivo de Cobranza

El sistema calcula automáticamente:

1. **Total Esperado**: Suma de todos los `expected_amount` de claims
2. **Total Pagado**: Suma de todos los pagos confirmados
3. **Deuda Total**: Diferencia entre esperado y pagado
4. **% de Cobranza**: (Total Pagado / Total Esperado) × 100

### Métricas del Embudo (Funnel Metrics)

#### **Gap 1: Leads Sin Identidad ni Pago** ⚠️

**Definición**: Leads registrados que no lograron tener identidad canónica ni generar claims.

**Cálculo**:
```
Leads Sin Identidad = Total Leads - Leads con person_key - Leads con claims
```

**Interpretación**:
- **Alto**: Indica problemas en el proceso de matching o datos incompletos
- **Bajo**: Indica buen proceso de identidad y conversión

**Ejemplo**:
- Total de leads: 1,000
- Leads con identidad: 850
- Leads con claims: 800
- **Leads sin identidad ni pago: 150 (15%)**

**Acciones recomendadas si el gap es alto**:
1. Revisar calidad de datos en los leads (teléfonos, placas, nombres)
2. Verificar si hay nuevos conductores que realmente no existen en el parque
3. Revisar reglas de matching (puede necesitar ajustes)
4. Analizar leads en `canon.identity_unmatched` para identificar patrones

### Desglose por Milestone

- **Drivers con M1**: Conductores que alcanzaron al menos 1 viaje
- **Drivers con M5**: Conductores que alcanzaron al menos 5 viajes
- **Drivers con M25**: Conductores que alcanzaron al menos 25 viajes

### Desglose por Estado

- **Pendiente**: Claims que aún no tienen pago confirmado
- **Pagado**: Claims con pago confirmado
- **Sin Claim**: Pagos que no tienen claim correspondiente (anomalía)

---

## 📊 Cómo Calcular el Gap de Leads Sin Identidad

### Query SQL para Identificar Leads Sin Identidad ni Pago

```sql
-- Leads que NO tienen identidad canónica ni claims generados
SELECT 
    mcl.external_id,
    mcl.first_name,
    mcl.last_name,
    mcl.park_phone,
    mcl.asset_plate_number,
    mcl.lead_created_at,
    CASE 
        WHEN il.id IS NULL THEN 'Sin identidad'
        ELSE 'Con identidad'
    END AS tiene_identidad,
    CASE 
        WHEN c.claim_id IS NULL THEN 'Sin claims'
        ELSE 'Con claims'
    END AS tiene_claims
FROM public.module_ct_cabinet_leads mcl
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_cabinet_leads'
    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id IS NOT NULL
    AND EXISTS (
        SELECT 1 
        FROM canon.identity_links il2
        WHERE il2.source_table = 'module_ct_cabinet_leads'
        AND il2.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
        AND il2.person_key = c.person_key
    )
WHERE il.id IS NULL  -- Sin identidad
    AND c.claim_id IS NULL  -- Sin claims
ORDER BY mcl.lead_created_at DESC;
```

### Métricas Agregadas del Gap

```sql
-- Resumen del gap: Total de leads vs leads con identidad vs leads con claims
-- BASE: public.module_ct_cabinet_leads (todos los leads registrados)
SELECT 
    COUNT(*) AS total_leads,
    COUNT(DISTINCT il.person_key) AS leads_con_identidad,
    COUNT(DISTINCT c.claim_id) AS leads_con_claims,
    COUNT(*) - COUNT(DISTINCT il.person_key) AS leads_sin_identidad,
    COUNT(*) - COUNT(DISTINCT c.claim_id) AS leads_sin_claims,
    ROUND(
        (COUNT(*) - COUNT(DISTINCT il.person_key))::numeric / COUNT(*)::numeric * 100, 
        2
    ) AS porcentaje_sin_identidad,
    ROUND(
        (COUNT(*) - COUNT(DISTINCT c.claim_id))::numeric / COUNT(*)::numeric * 100, 
        2
    ) AS porcentaje_sin_claims
FROM public.module_ct_cabinet_leads mcl
LEFT JOIN canon.identity_links il 
    ON il.source_table = 'module_ct_cabinet_leads'
    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id IS NOT NULL
    AND EXISTS (
        SELECT 1 
        FROM canon.identity_links il2
        WHERE il2.source_table = 'module_ct_cabinet_leads'
        AND il2.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
        AND il2.person_key = c.person_key
    );
```

**Interpretación:**
- `total_leads`: Total en `module_ct_cabinet_leads` (BASE DEL EMBUDO)
- `leads_con_identidad`: Leads que tienen `identity_links` (pasaron ingesta)
- `leads_con_claims`: Leads que generaron claims (pasaron todo el embudo)
- `leads_sin_identidad`: **GAP 1** - Leads que NO pasaron la ingesta de identidad
- `leads_sin_claims`: Incluye GAP 1 + GAP 2 (sin driver_id) + GAP 3 (sin milestones)

---

## 🎯 Preguntas Frecuentes

### ¿Qué significa "Leads sin identidad ni pago"?

Son leads que se registraron en `module_ct_cabinet_leads` (BASE DEL EMBUDO) pero:
- ❌ No tienen `identity_links` (no se pudo hacer match en la ingesta de identidad)
- ❌ No tienen `person_key` válido (no pasaron a atribución)
- ❌ No aparecen en `v_conversion_metrics` (filtra `WHERE person_key IS NOT NULL`)
- ❌ No aparecen en `v_cabinet_financial_14d` (vista financiera)
- ❌ No generaron ningún claim (no alcanzaron milestones o no se procesaron)

Estos leads representan la **primera pérdida del embudo** (GAP 1) y deben ser monitoreados.

**Impacto**: Un lead sin identidad es **completamente invisible** para el sistema de cobranza.

### ¿Por qué un conductor no aparece en la vista financiera?

**Razones posibles (en orden de frecuencia):**

1. **No tiene `identity_links`** (GAP 1 - más común)
   - El lead no pasó la ingesta de identidad
   - No se pudo hacer match con ninguna persona existente
   - **Solución**: Revisar datos del lead, verificar si existe en `public.drivers`

2. **No tiene `driver_id`** (GAP 2)
   - Tiene identidad pero no está en el parque (`public.drivers`)
   - **Solución**: Verificar si el conductor realmente está activo en el parque

3. **No alcanzó milestones** (GAP 3)
   - Tiene identidad y driver_id pero no completó viajes suficientes
   - **Solución**: Verificar viajes en `summary_daily` dentro de ventana de 14 días

4. **No tiene `lead_date` válido**
   - El lead no tiene `lead_created_at` o no se procesó correctamente
   - **Solución**: Verificar datos en `module_ct_cabinet_leads`

### ¿Por qué hay deuda si Yango pagó?

Posibles razones:
1. El pago no se reconcilió correctamente (problema de matching)
2. El pago está pendiente de confirmación
3. Hay un desfase temporal (el pago llegará después)

### ¿Qué pasa si un conductor tiene múltiples leads?

Cada lead se procesa independientemente:
- Cada lead tiene su propia ventana de 14 días
- Cada lead puede generar sus propios milestones
- Los claims se generan por lead, no por conductor

### ¿Cómo se actualiza la información?

El sistema se actualiza mediante:
1. **Ingesta de identidad**: Procesa nuevos leads y hace matching
2. **Atribución de leads**: Crea eventos en `lead_events`
3. **Ingesta de pagos**: Procesa nuevos pagos de Yango
4. **Refresh de vistas**: Actualiza las vistas materializadas

---

## 📝 Resumen Final

El sistema de cobranza Yango funciona así:

1. **Leads** se registran desde Yango
2. **Identidad** se resuelve mediante matching inteligente
3. **Viajes** se cuentan dentro de una ventana de 14 días
4. **Milestones** se alcanzan cuando se completan 1, 5, o 25 viajes
5. **Claims** se generan automáticamente por cada milestone alcanzado
6. **Pagos** se reconcilian con claims para determinar qué se pagó
7. **Deuda** se calcula como la diferencia entre lo esperado y lo pagado

**El objetivo final**: Saber con exactitud cuánto nos debe Yango y por qué conductores/milestones.

---

**Última actualización**: Enero 2026  
**Versión**: 1.0  
**Autor**: Sistema CT4 - YEGO

