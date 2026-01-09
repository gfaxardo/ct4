# Validación de Contrato: Cabinet Reconciliation Endpoint

**Fecha:** 2025-01-XX  
**Endpoint:** `GET /api/v1/yango/payments/cabinet/reconciliation`

---

## Validación del Contrato

### Backend (Python Pydantic Schema)

**Archivo:** `backend/app/schemas/payments.py`

```python
class CabinetReconciliationResponse(BaseModel):
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[CabinetReconciliationRow]
```

**Implementación del endpoint:** `backend/app/api/v1/yango_payments.py`

```python
return CabinetReconciliationResponse(
    status="ok",
    count=len(rows),
    total=total,
    filters={k: v for k, v in filters.items() if v is not None},
    rows=rows
)
```

**JSON real devuelto:**
```json
{
  "status": "ok",
  "count": 10,
  "total": 312,
  "filters": {
    "limit": 100,
    "offset": 0
  },
  "rows": [...]
}
```

---

### Frontend (TypeScript Types)

**Archivo:** `frontend/lib/types.ts`

```typescript
export interface CabinetReconciliationResponse {
  status: string;
  count: number;
  total: number;
  filters: Record<string, any>;
  rows: CabinetReconciliationRow[];
}
```

**Función API:** `frontend/lib/api.ts`

```typescript
export async function getCabinetReconciliation(params?: {
  driver_id?: string;
  reconciliation_status?: string;
  milestone_value?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<CabinetReconciliationResponse>
```

---

## Comparación Campo por Campo

| Campo | Backend (Pydantic) | Frontend (TypeScript) | Estado |
|-------|-------------------|----------------------|--------|
| `status` | `str` | `string` | ✅ Coincide |
| `count` | `int` | `number` | ✅ Coincide |
| `total` | `int` | `number` | ✅ Coincide |
| `filters` | `Dict[str, Any]` | `Record<string, any>` | ✅ Coincide |
| `rows` | `List[CabinetReconciliationRow]` | `CabinetReconciliationRow[]` | ✅ Coincide |

---

## Comparación de CabinetReconciliationRow

| Campo | Backend | Frontend | Estado |
|-------|---------|----------|--------|
| `driver_id` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `milestone_value` | `Optional[int]` | `number \| null` | ✅ Coincide |
| `achieved_flag` | `Optional[bool]` | `boolean \| null` | ✅ Coincide |
| `achieved_person_key` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `achieved_lead_date` | `Optional[date]` | `string \| null` | ✅ Coincide (date → string en JSON) |
| `achieved_date` | `Optional[date]` | `string \| null` | ✅ Coincide (date → string en JSON) |
| `achieved_trips_in_window` | `Optional[int]` | `number \| null` | ✅ Coincide |
| `window_days` | `Optional[int]` | `number \| null` | ✅ Coincide |
| `expected_amount` | `Optional[Decimal]` | `number \| null` | ✅ Coincide (Decimal → number en JSON) |
| `achieved_currency` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `rule_id` | `Optional[int]` | `number \| null` | ✅ Coincide |
| `paid_flag` | `Optional[bool]` | `boolean \| null` | ✅ Coincide |
| `paid_person_key` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `pay_date` | `Optional[date]` | `string \| null` | ✅ Coincide (date → string en JSON) |
| `payment_key` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `identity_status` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `match_rule` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `match_confidence` | `Optional[str]` | `string \| null` | ✅ Coincide |
| `latest_snapshot_at` | `Optional[datetime]` | `string \| null` | ✅ Coincide (datetime → string en JSON) |
| `reconciliation_status` | `Optional[str]` | `string \| null` | ✅ Coincide |

---

## Conclusión

**✅ NO HAY MISMATCH**

El contrato está correctamente alineado:

1. **Backend devuelve:** `{ status, count, total, filters, rows }`
2. **Frontend espera:** `{ status, count, total, filters, rows }`
3. **Tipos TypeScript reflejan 1:1 el schema Pydantic**

**Nota:** El usuario mencionó que el backend devuelve `{ total, items }`, pero según el código actual, el backend devuelve `{ status, count, total, filters, rows }`. No se encontró ningún endpoint que devuelva `items` en lugar de `rows`.

**Patrón consistente:** Todos los endpoints similares (`YangoCabinetClaimsResponse`, `YangoReconciliationItemsResponse`) usan `rows`, no `items`.

---

**Fin de validación**








