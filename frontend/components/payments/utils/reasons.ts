/**
 * Utilidades para calcular motivos (reasons) de anomalías en reconciliación Yango
 */

export interface AnomalyReason {
  code: string
  label: string
  severity: 'high' | 'medium' | 'low'
  details?: string
}

export interface ReconciliationItem {
  reconciliation_status?: string | null  // Compatibilidad: mapeado desde paid_status
  paid_status?: 'paid' | 'pending_active' | 'pending_expired' | null  // Estado real del pago
  expected_amount?: number | null
  lead_date?: string | null
  paid_is_paid?: boolean | null
  paid_payment_key?: string | null
  paid_match_rule?: string | null
  paid_match_confidence?: string | null
  lead_origin?: string | null
  sort_date?: string | null
  paid_snapshot_at?: string | null
  paid_date?: string | null
  payable_date?: string | null
  pay_week_start_monday?: string | null
}

/**
 * Calcula el motivo (reason) de una anomalía basándose en los campos del item
 * Retorna OK si no hay anomalía, o un código de anomalía con severidad
 * 
 * IMPORTANTE: Esta es una función pura sin efectos secundarios.
 * NO debe contener logging, fetch, console.log, ni ninguna llamada a APIs.
 */
export function computeAnomalyReason(row: ReconciliationItem): AnomalyReason {
  // Si tiene paid_status, usarlo directamente (prioridad)
  if (row.paid_status) {
    if (row.paid_status === 'pending_expired') {
      return {
        code: 'EXPECTED_NOT_PAID',
        label: 'Expected vencido (no pagado)',
        severity: 'high',
        details: 'Expected existe pero no fue pagado y la ventana de pago expiró'
      }
    }
    if (row.paid_status === 'paid') {
      return {
        code: 'OK',
        label: 'OK',
        severity: 'low',
        details: 'Item pagado correctamente'
      }
    }
    if (row.paid_status === 'pending_active') {
      return {
        code: 'PENDING_ACTIVE',
        label: 'Pendiente (ventana activa)',
        severity: 'low',
        details: 'Expected existe pero aún está en ventana de pago activa'
      }
    }
  }

  // Fallback a lógica antigua si no hay paid_status
  const hasExpected = row.expected_amount != null
  const isPaid = row.paid_is_paid === true
  const hasPaidKey = row.paid_payment_key != null
  const matchRule = row.paid_match_rule
  const matchConfidence = row.paid_match_confidence

  // Verificar si se puede calcular semana efectiva
  const hasWeek = row.pay_week_start_monday != null || 
                  row.sort_date != null || 
                  row.paid_snapshot_at != null || 
                  row.paid_date != null || 
                  row.payable_date != null

  // WEEK_MISSING: no se puede calcular semana (raro pero posible)
  if (!hasWeek) {
    return {
      code: 'WEEK_MISSING',
      label: 'Semana no calculable',
      severity: 'high',
      details: 'No hay fechas disponibles para calcular semana efectiva'
    }
  }

  // PAID_WITHOUT_EXPECTED: pago sin expected
  // Cuando expected_amount es null y (paid_is_paid es true OR paid_payment_key no es null)
  if (!hasExpected && (isPaid || hasPaidKey)) {
    // Si además no tiene match, es más grave
    if (matchRule === 'none' || matchConfidence === 'unknown') {
      return {
        code: 'PAID_WITHOUT_EXPECTED',
        label: 'Pago sin expected (sin match)',
        severity: 'high',
        details: 'Pago registrado sin expected y sin match de driver'
      }
    }
    return {
      code: 'PAID_WITHOUT_EXPECTED',
      label: 'Pago sin expected',
      severity: 'high',
      details: 'Pago registrado pero no hay expected_amount asociado'
    }
  }

  // MATCH_NONE: items pagados sin match
  // Aplicado a items que están pagados pero no tienen match confiable
  if ((isPaid || hasPaidKey) && (matchRule === 'none' || matchConfidence === 'unknown')) {
    return {
      code: 'MATCH_NONE',
      label: 'Pago sin match confiable',
      severity: 'high',
      details: 'Pago registrado pero match_rule es "none" o match_confidence es "unknown"'
    }
  }

  // EXPECTED_NOT_PAID: expected existe pero no está pagado
  if (hasExpected && !isPaid && !hasPaidKey) {
    return {
      code: 'EXPECTED_NOT_PAID',
      label: 'Expected no pagado',
      severity: 'medium',
      details: 'Hay expected_amount pero no hay pago registrado'
    }
  }

  // OK: todo está bien
  return {
    code: 'OK',
    label: 'OK',
    severity: 'low',
    details: 'Item reconciliado correctamente'
  }
}

/**
 * Verifica si un item es una anomalía real
 * Función pura sin efectos secundarios (sin logging ni llamadas a fetch)
 */
export function isAnomaly(row: ReconciliationItem): boolean {
  const reason = computeAnomalyReason(row)
  return reason.code !== 'OK'
}

/**
 * Obtiene el color del chip según la severidad
 */
export function getSeverityColor(severity: AnomalyReason['severity']): string {
  switch (severity) {
    case 'high':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'low':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

