'use client'

import { useEffect, useState } from 'react'
import { getDataHealth, DataHealthResponse, DataHealthStatus } from '@/lib/api'

export default function DataHealthPage() {
  const [data, setData] = useState<DataHealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    loadData()
  }, [days])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const result = await getDataHealth(days)
      setData(result)
    } catch (err: any) {
      setError(err.message || 'Error cargando data health')
    } finally {
      setLoading(false)
    }
  }

  const getHealthStatusColor = (status: string) => {
    if (status === 'GREEN_OK') return 'bg-green-100 text-green-800 border-green-300'
    if (status === 'YELLOW_INGESTION_1D' || status === 'YELLOW_BUSINESS_LAG') return 'bg-yellow-100 text-yellow-800 border-yellow-300'
    return 'bg-red-100 text-red-800 border-red-300'
  }

  const getHealthStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      'GREEN_OK': '✅ OK',
      'YELLOW_INGESTION_1D': '⚠️ Sin Ingesta 1D',
      'YELLOW_BUSINESS_LAG': '⚠️ Lag Negocio',
      'RED_INGESTION_STALE': '🔴 Ingesta Antigua',
      'RED_NO_INGESTION_2D': '🔴 Sin Ingesta 2D',
      'RED_NO_DATA': '🔴 Sin Datos'
    }
    return labels[status] || status
  }

  const formatInterval = (interval: string | null | undefined) => {
    if (!interval) return '-'
    return interval
  }

  const formatDate = (date: string | null | undefined) => {
    if (!date) return '-'
    return new Date(date).toLocaleDateString('es-ES')
  }

  // Agrupar ingestion_daily por fuente para gráficos
  const groupedBySource = data?.ingestion_daily.reduce((acc, item) => {
    if (!acc[item.source_name]) {
      acc[item.source_name] = { business: [], ingestion: [] }
    }
    if (item.metric_type === 'business') {
      acc[item.source_name].business.push(item)
    } else {
      acc[item.source_name].ingestion.push(item)
    }
    return acc
  }, {} as Record<string, { business: typeof data.ingestion_daily; ingestion: typeof data.ingestion_daily }>)

  // Contar fuentes por estado
  const sourcesByStatus = data?.health_status.reduce((acc, item) => {
    acc[item.health_status] = (acc[item.health_status] || 0) + 1
    return acc
  }, {} as Record<string, number>) || {}

  const redSources = (sourcesByStatus['RED_NO_INGESTION_2D'] || 0) + (sourcesByStatus['RED_INGESTION_STALE'] || 0) + (sourcesByStatus['RED_NO_DATA'] || 0)
  const yellowSources = (sourcesByStatus['YELLOW_BUSINESS_LAG'] || 0) + (sourcesByStatus['YELLOW_INGESTION_1D'] || 0)
  const greenSources = sourcesByStatus['GREEN_OK'] || 0

  // Export CSV
  const exportToCSV = (type: 'health' | 'ingestion') => {
    if (!data) return

    let csv = ''
    let filename = ''

    if (type === 'health') {
      filename = `data-health-status-${new Date().toISOString().split('T')[0]}.csv`
      csv = 'source_name,source_type,health_status,max_business_date,business_days_lag,max_ingestion_ts,ingestion_lag_interval,rows_business_today,rows_ingested_today\n'
      data.health_status.forEach(item => {
        csv += `${item.source_name},${item.source_type || ''},${item.health_status},${item.max_business_date || ''},${item.business_days_lag || ''},${item.max_ingestion_ts || ''},${item.ingestion_lag_interval || ''},${item.rows_business_today},${item.rows_ingested_today}\n`
      })
    } else {
      filename = `data-ingestion-daily-${new Date().toISOString().split('T')[0]}.csv`
      csv = 'source_name,metric_type,metric_date,rows_count\n'
      data.ingestion_daily.forEach(item => {
        csv += `${item.source_name},${item.metric_type},${item.metric_date},${item.rows_count}\n`
      })
    }

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="px-4 py-6">
        <div className="text-center py-12">Cargando...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-800">
          Error: {error}
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Data Health - Observabilidad de Ingestas</h1>
        <div className="flex gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 border rounded-md"
          >
            <option value={7}>Últimos 7 días</option>
            <option value={30}>Últimos 30 días</option>
            <option value={60}>Últimos 60 días</option>
            <option value={90}>Últimos 90 días</option>
          </select>
        </div>
      </div>

      {/* Cards de resumen */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2 text-red-800">Fuentes Caídas</h3>
          <div className="text-3xl font-bold text-red-900">{redSources}</div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2 text-yellow-800">Fuentes con Lag</h3>
          <div className="text-3xl font-bold text-yellow-900">{yellowSources}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-2 text-green-800">Fuentes al Día</h3>
          <div className="text-3xl font-bold text-green-900">{greenSources}</div>
        </div>
      </div>

      {/* Tabla de estado de salud */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-semibold">Estado de Salud por Fuente</h2>
          <button
            onClick={() => exportToCSV('health')}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
          >
            Exportar CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fuente</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Última Fecha Negocio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lag Negocio (días)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Última Ingesta</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lag Ingesta</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rows Hoy (Negocio)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rows Hoy (Ingesta)</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.health_status.map((item) => (
                <tr key={item.source_name}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{item.source_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.source_type || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${getHealthStatusColor(item.health_status)}`}>
                      {getHealthStatusLabel(item.health_status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{formatDate(item.max_business_date)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.business_days_lag ?? '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{formatDate(item.max_ingestion_ts)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{formatInterval(item.ingestion_lag_interval)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.rows_business_today}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.rows_ingested_today}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Gráficos de ingesta diaria */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-xl font-semibold">Ingesta Diaria (últimos {days} días)</h2>
          <button
            onClick={() => exportToCSV('ingestion')}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
          >
            Exportar CSV
          </button>
        </div>
        <div className="p-6">
          {Object.entries(groupedBySource || {}).map(([sourceName, dataByType]) => (
            <div key={sourceName} className="mb-8">
              <h3 className="text-lg font-semibold mb-4">{sourceName}</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Business */}
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">Por Fecha de Negocio</h4>
                  <div className="space-y-2">
                    {dataByType.business.slice(0, 10).map((item) => (
                      <div key={`${item.source_name}-${item.metric_date}-business`} className="flex items-center">
                        <div className="w-24 text-xs text-gray-500">{formatDate(item.metric_date)}</div>
                        <div className="flex-1 bg-gray-200 rounded h-6 relative">
                          <div
                            className="bg-blue-500 h-6 rounded"
                            style={{ width: `${Math.min(100, (item.rows_count / Math.max(...dataByType.business.map(d => d.rows_count), 1)) * 100)}%` }}
                          />
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-gray-700">
                            {item.rows_count.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                    {dataByType.business.length > 10 && (
                      <div className="text-xs text-gray-500 mt-2">
                        ... y {dataByType.business.length - 10} días más
                      </div>
                    )}
                  </div>
                </div>
                {/* Ingestion */}
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">Por Fecha de Ingesta</h4>
                  <div className="space-y-2">
                    {dataByType.ingestion.slice(0, 10).map((item) => (
                      <div key={`${item.source_name}-${item.metric_date}-ingestion`} className="flex items-center">
                        <div className="w-24 text-xs text-gray-500">{formatDate(item.metric_date)}</div>
                        <div className="flex-1 bg-gray-200 rounded h-6 relative">
                          <div
                            className="bg-green-500 h-6 rounded"
                            style={{ width: `${Math.min(100, (item.rows_count / Math.max(...dataByType.ingestion.map(d => d.rows_count), 1)) * 100)}%` }}
                          />
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-gray-700">
                            {item.rows_count.toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                    {dataByType.ingestion.length > 10 && (
                      <div className="text-xs text-gray-500 mt-2">
                        ... y {dataByType.ingestion.length - 10} días más
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

