/**
 * Utilidades para exportar datos a CSV
 */

export interface CSVRow {
  [key: string]: string | number | boolean | null | undefined
}

/**
 * Convierte un array de objetos a CSV
 */
export function arrayToCSV(data: CSVRow[], headers?: string[]): string {
  if (data.length === 0) {
    return ''
  }

  // Obtener headers si no se proporcionan
  const csvHeaders = headers || Object.keys(data[0])

  // Función para escapar valores CSV
  const escapeCSV = (value: any): string => {
    if (value === null || value === undefined) {
      return ''
    }
    const str = String(value)
    // Si contiene comas, comillas o saltos de línea, envolver en comillas y escapar comillas
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  // Construir CSV
  const rows: string[] = []

  // Headers
  rows.push(csvHeaders.map(escapeCSV).join(','))

  // Data rows
  for (const row of data) {
    const values = csvHeaders.map(header => escapeCSV(row[header]))
    rows.push(values.join(','))
  }

  return rows.join('\n')
}

/**
 * Descarga un string CSV como archivo
 */
export function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  URL.revokeObjectURL(url)
}

/**
 * Exporta un array de objetos a CSV y lo descarga
 */
export function exportToCSV(
  data: CSVRow[],
  filename: string,
  headers?: string[]
): void {
  const csvContent = arrayToCSV(data, headers)
  downloadCSV(csvContent, filename)
}













