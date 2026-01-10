# Reporte de Conflictos de Scout Attribution

**Fecha de generación**: 2026-01-09T21:44:28.280505
**Total conflictos**: 5

## Resumen Ejecutivo

Se detectaron 5 personas con múltiples scout_ids asignados.
Estos conflictos requieren revisión manual para determinar el scout_id correcto.

## Recomendaciones

1. **Priorizar por fecha**: Usar el scout_id de la atribución más antigua (primera fecha)
2. **Priorizar por fuente**: `lead_ledger` > `lead_events` > `scouting_daily` > `migrations`
3. **Revisar evidencia**: Verificar `evidence_json` en `lead_ledger` para contexto
4. **Actualizar manualmente**: Usar SQL para actualizar `lead_ledger.attributed_scout_id`

## Detalles de Conflictos

### Conflicto 1: b3d8f553-28ca-48f6-a0cf-79ceeea58edc

**Persona**:
- Nombre: LINARES VANDERLEY
- Teléfono: 51905459777
- Licencia: DRIVERDRAFTF66C1AB9DF4245FF9EF02DBEFDB98E25
- Creada: 2025-12-23 19:57:29.855269-05:00

**Conflictos**:
- Scout IDs distintos: 3
- Scout IDs: [10, 13, 23]
- Fuentes: ['module_ct_scouting_daily']
- Primera atribución: 2025-12-13 00:00:00
- Última atribución: 2025-12-22 00:00:00
- Total registros: 3

**Estado en lead_ledger**:
- ⚠️ **NO tiene attributed_scout_id en lead_ledger**

**Detalles por fuente**:
- Scout ID: 10, Fuente: module_ct_scouting_daily, PK: 541, Fecha: 2025-12-22T00:00:00, Prioridad: 2
- Scout ID: 13, Fuente: module_ct_scouting_daily, PK: 437, Fecha: 2025-12-15T00:00:00, Prioridad: 2
- Scout ID: 23, Fuente: module_ct_scouting_daily, PK: 434, Fecha: 2025-12-13T00:00:00, Prioridad: 2

**SQL para resolver** (ejemplo - ajustar scout_id según decisión):
```sql
-- Revisar evidencia primero:
SELECT person_key, attributed_scout_id, attribution_rule, evidence_json
FROM observational.lead_ledger
WHERE person_key = 'b3d8f553-28ca-48f6-a0cf-79ceeea58edc';

-- Actualizar (reemplazar X con el scout_id correcto):
UPDATE observational.lead_ledger
SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto
    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),
    evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
        'conflict_resolution', true,
        'conflict_resolution_date', NOW(),
        'conflict_scout_ids', [10, 13, 23],
        'resolved_scout_id', X  -- Reemplazar X
    ),
    updated_at = NOW()
WHERE person_key = 'b3d8f553-28ca-48f6-a0cf-79ceeea58edc';
```

---

### Conflicto 2: 10a37516-659b-4b96-a010-a479fbfd3f0d

**Persona**:
- Nombre: N/A
- Teléfono: 998701906
- Licencia: X
- Creada: 2026-01-09 15:55:53.392573-05:00

**Conflictos**:
- Scout IDs distintos: 2
- Scout IDs: [10, 13]
- Fuentes: ['public.module_ct_scouting_daily']
- Primera atribución: 2025-11-26 00:00:00
- Última atribución: 2025-12-19 00:00:00
- Total registros: 2

**Estado en lead_ledger**:
- ⚠️ **NO tiene attributed_scout_id en lead_ledger**

**Detalles por fuente**:
- Scout ID: 10, Fuente: public.module_ct_scouting_daily, PK: 518, Fecha: 2025-12-19T00:00:00, Prioridad: 4
- Scout ID: 13, Fuente: public.module_ct_scouting_daily, PK: 143, Fecha: 2025-11-26T00:00:00, Prioridad: 4

**SQL para resolver** (ejemplo - ajustar scout_id según decisión):
```sql
-- Revisar evidencia primero:
SELECT person_key, attributed_scout_id, attribution_rule, evidence_json
FROM observational.lead_ledger
WHERE person_key = '10a37516-659b-4b96-a010-a479fbfd3f0d';

-- Actualizar (reemplazar X con el scout_id correcto):
UPDATE observational.lead_ledger
SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto
    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),
    evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
        'conflict_resolution', true,
        'conflict_resolution_date', NOW(),
        'conflict_scout_ids', [10, 13],
        'resolved_scout_id', X  -- Reemplazar X
    ),
    updated_at = NOW()
WHERE person_key = '10a37516-659b-4b96-a010-a479fbfd3f0d';
```

---

### Conflicto 3: 49877d22-cc19-4fec-a0a2-e14defffcd25

**Persona**:
- Nombre: N/A
- Teléfono: N/A
- Licencia: N/A
- Creada: 2025-12-25 21:01:00.007415-05:00

**Conflictos**:
- Scout IDs distintos: 2
- Scout IDs: [1, 20]
- Fuentes: ['module_ct_migrations', 'module_ct_scouting_daily']
- Primera atribución: 2025-12-19 00:00:00
- Última atribución: 2025-12-19 00:00:00
- Total registros: 2

**Estado en lead_ledger**:
- ⚠️ **NO tiene attributed_scout_id en lead_ledger**

**Detalles por fuente**:
- Scout ID: 1, Fuente: module_ct_scouting_daily, PK: 513, Fecha: 2025-12-19T00:00:00, Prioridad: 2
- Scout ID: 20, Fuente: module_ct_migrations, PK: 174, Fecha: 2025-12-19T00:00:00, Prioridad: 2

**SQL para resolver** (ejemplo - ajustar scout_id según decisión):
```sql
-- Revisar evidencia primero:
SELECT person_key, attributed_scout_id, attribution_rule, evidence_json
FROM observational.lead_ledger
WHERE person_key = '49877d22-cc19-4fec-a0a2-e14defffcd25';

-- Actualizar (reemplazar X con el scout_id correcto):
UPDATE observational.lead_ledger
SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto
    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),
    evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
        'conflict_resolution', true,
        'conflict_resolution_date', NOW(),
        'conflict_scout_ids', [1, 20],
        'resolved_scout_id', X  -- Reemplazar X
    ),
    updated_at = NOW()
WHERE person_key = '49877d22-cc19-4fec-a0a2-e14defffcd25';
```

---

### Conflicto 4: d49ce6e9-8d8d-44c1-ab3d-15e3780c3a92

**Persona**:
- Nombre: N/A
- Teléfono: N/A
- Licencia: N/A
- Creada: 2025-12-25 21:01:00.007415-05:00

**Conflictos**:
- Scout IDs distintos: 2
- Scout IDs: [19, 20]
- Fuentes: ['module_ct_migrations', 'module_ct_scouting_daily']
- Primera atribución: 2025-12-02 00:00:00
- Última atribución: 2025-12-23 00:00:00
- Total registros: 2

**Estado en lead_ledger**:
- ⚠️ **NO tiene attributed_scout_id en lead_ledger**

**Detalles por fuente**:
- Scout ID: 20, Fuente: module_ct_scouting_daily, PK: 592, Fecha: 2025-12-23T00:00:00, Prioridad: 2
- Scout ID: 19, Fuente: module_ct_migrations, PK: 161, Fecha: 2025-12-02T00:00:00, Prioridad: 2

**SQL para resolver** (ejemplo - ajustar scout_id según decisión):
```sql
-- Revisar evidencia primero:
SELECT person_key, attributed_scout_id, attribution_rule, evidence_json
FROM observational.lead_ledger
WHERE person_key = 'd49ce6e9-8d8d-44c1-ab3d-15e3780c3a92';

-- Actualizar (reemplazar X con el scout_id correcto):
UPDATE observational.lead_ledger
SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto
    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),
    evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
        'conflict_resolution', true,
        'conflict_resolution_date', NOW(),
        'conflict_scout_ids', [19, 20],
        'resolved_scout_id', X  -- Reemplazar X
    ),
    updated_at = NOW()
WHERE person_key = 'd49ce6e9-8d8d-44c1-ab3d-15e3780c3a92';
```

---

### Conflicto 5: d853c008-9758-4e0d-8bc4-42a5f4c392f0

**Persona**:
- Nombre: MARIN CENTENO MIGUEL ANGEL
- Teléfono: 51928138965
- Licencia: Q25498695
- Creada: 2025-12-23 19:53:05.665213-05:00

**Conflictos**:
- Scout IDs distintos: 2
- Scout IDs: [9, 22]
- Fuentes: ['module_ct_scouting_daily']
- Primera atribución: 2025-11-26 00:00:00
- Última atribución: 2025-11-26 00:00:00
- Total registros: 2

**Estado en lead_ledger**:
- ⚠️ **NO tiene attributed_scout_id en lead_ledger**

**Detalles por fuente**:
- Scout ID: 22, Fuente: module_ct_scouting_daily, PK: 157, Fecha: 2025-11-26T00:00:00, Prioridad: 2
- Scout ID: 9, Fuente: module_ct_scouting_daily, PK: 134, Fecha: 2025-11-26T00:00:00, Prioridad: 2

**SQL para resolver** (ejemplo - ajustar scout_id según decisión):
```sql
-- Revisar evidencia primero:
SELECT person_key, attributed_scout_id, attribution_rule, evidence_json
FROM observational.lead_ledger
WHERE person_key = 'd853c008-9758-4e0d-8bc4-42a5f4c392f0';

-- Actualizar (reemplazar X con el scout_id correcto):
UPDATE observational.lead_ledger
SET attributed_scout_id = X,  -- Reemplazar X con scout_id correcto
    attribution_rule = COALESCE(attribution_rule, 'RESOLVED_MANUAL_CONFLICT'),
    evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
        'conflict_resolution', true,
        'conflict_resolution_date', NOW(),
        'conflict_scout_ids', [9, 22],
        'resolved_scout_id', X  -- Reemplazar X
    ),
    updated_at = NOW()
WHERE person_key = 'd853c008-9758-4e0d-8bc4-42a5f4c392f0';
```

---

