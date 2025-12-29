export function formatDate(date: string): string {
  return new Date(date).toLocaleString('es-ES')
}

export function formatConfidenceLevel(level: string): string {
  const levels: Record<string, string> = {
    HIGH: 'Alto',
    MEDIUM: 'Medio',
    LOW: 'Bajo',
  }
  return levels[level] || level
}

export function getConfidenceColor(level: string): string {
  const colors: Record<string, string> = {
    HIGH: 'bg-green-100 text-green-800',
    MEDIUM: 'bg-yellow-100 text-yellow-800',
    LOW: 'bg-red-100 text-red-800',
  }
  return colors[level] || 'bg-gray-100 text-gray-800'
}
















