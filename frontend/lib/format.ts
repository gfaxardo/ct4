/**
 * Formateo de fechas y números para la UI.
 * Locale: es-ES (unificado en toda la app).
 */

const LOCALE = 'es-ES';

export function formatDate(dateStr: string | null | undefined): string {
  if (dateStr == null) return '—';
  try {
    return new Date(dateStr).toLocaleDateString(LOCALE);
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (dateStr == null) return '—';
  try {
    return new Date(dateStr).toLocaleString(LOCALE);
  } catch {
    return dateStr;
  }
}

export function formatCurrency(amount: number, currency = 'PEN'): string {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency }).format(amount);
}
