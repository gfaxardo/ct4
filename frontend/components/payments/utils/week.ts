/**
 * Utilidades para calcular semana efectiva (lunes ISO)
 */

/**
 * Calcula el lunes de la semana ISO para una fecha dada
 * Retorna YYYY-MM-DD en UTC-safe
 */
export function weekStartMonday(dateLike: string | Date | null | undefined): string | null {
  if (!dateLike) return null

  let date: Date
  if (typeof dateLike === 'string') {
    // Parsear string ISO (puede venir con hora o solo fecha)
    date = new Date(dateLike)
    if (isNaN(date.getTime())) {
      return null
    }
  } else {
    date = dateLike
  }

  // Usar UTC para evitar problemas de timezone
  const year = date.getUTCFullYear()
  const month = date.getUTCMonth()
  const day = date.getUTCDate()
  
  // Crear fecha en UTC
  const utcDate = new Date(Date.UTC(year, month, day))
  
  // Obtener día de la semana (0=domingo, 1=lunes, ..., 6=sábado)
  const dayOfWeek = utcDate.getUTCDay()
  
  // Calcular offset hacia lunes: (d.getDay() + 6) % 7
  // domingo (0) -> 6 días atrás, lunes (1) -> 0 días, etc.
  const daysToMonday = (dayOfWeek + 6) % 7
  
  // Restar días para llegar al lunes
  const mondayDate = new Date(utcDate)
  mondayDate.setUTCDate(utcDate.getUTCDate() - daysToMonday)
  
  // Formatear como YYYY-MM-DD
  const yearStr = String(mondayDate.getUTCFullYear())
  const monthStr = String(mondayDate.getUTCMonth() + 1).padStart(2, '0')
  const dayStr = String(mondayDate.getUTCDate()).padStart(2, '0')
  
  return `${yearStr}-${monthStr}-${dayStr}`
}

/**
 * Calcula la semana efectiva para un item de reconciliación
 * Usa pay_week_start_monday si existe, sino calcula desde sort_date o fechas alternativas
 */
export function effectiveWeekStartMonday(item: {
  pay_week_start_monday?: string | null
  sort_date?: string | null
  paid_snapshot_at?: string | null
  paid_date?: string | null
  payable_date?: string | null
}): string | null {
  // Si ya tiene pay_week_start_monday, usarlo
  if (item.pay_week_start_monday) {
    return item.pay_week_start_monday
  }

  // Intentar calcular desde sort_date
  if (item.sort_date) {
    const week = weekStartMonday(item.sort_date)
    if (week) return week
  }

  // Intentar desde paid_snapshot_at
  if (item.paid_snapshot_at) {
    const week = weekStartMonday(item.paid_snapshot_at)
    if (week) return week
  }

  // Intentar desde paid_date
  if (item.paid_date) {
    const week = weekStartMonday(item.paid_date)
    if (week) return week
  }

  // Intentar desde payable_date
  if (item.payable_date) {
    const week = weekStartMonday(item.payable_date)
    if (week) return week
  }

  return null
}













