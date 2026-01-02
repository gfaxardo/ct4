'use client'

import { useEffect, useState, useMemo } from 'react'
// Componente legacy - funciones movidas a lib/api.ts
import { getYangoReconciliationSummary, getYangoReconciliationItems } from '@/lib/api'
import type { YangoReconciliationSummaryRow, YangoReconciliationItemRow } from '@/lib/types'
import { computeAnomalyReason, isAnomaly, getSeverityColor } from './utils/reasons'
import { effectiveWeekStartMonday } from './utils/week'

interface YangoDashboardProps {
  onWeekClick: (weekStart: string) => void
  weekFilter?: string
  onWeekFilterChange: (week: string) => void
  onReasonClick?: (reasonCode: string) => void
}

export default function YangoDashboard({
  onWeekClick,
  weekFilter,
  onWeekFilterChange,
  onReasonClick
}: YangoDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<YangoReconciliationSummaryRow[]>([])
  const [items, setItems] = useState<YangoReconciliationItemRow[]>([])
  const [loadingItems, setLoadingItems] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasWeekFilter = weekFilter && weekFilter !== ''

  // #region agent log
  useEffect(() => {
    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:hasWeekFilter',message:'hasWeekFilter calculated',data:{weekFilter,hasWeekFilter},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'A'})}).catch(()=>{});
  }, [weekFilter, hasWeekFilter]);
  // #endregion

  useEffect(() => {
    loadSummary()
  }, [weekFilter])

  useEffect(() => {
    // Si hay semana seleccionada, cargar items para calcular anomalías reales
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:useEffect-loadItems',message:'useEffect for loadItemsForWeek triggered',data:{hasWeekFilter,weekFilter},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    if (hasWeekFilter) {
      loadItemsForWeek()
    }
  }, [weekFilter])

  async function loadSummary() {
    setLoading(true)
    setError(null)
    try {
      const response = await getYangoReconciliationSummary({
        week_start: weekFilter || undefined,
        limit: 1000
      })
      setSummary(response.rows)
    } catch (err) {
      console.error('Error cargando resumen Yango:', err)
      setError('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  async function loadItemsForWeek() {
    if (!hasWeekFilter) return
    
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:loadItemsForWeek:entry',message:'loadItemsForWeek called',data:{weekFilter,hasWeekFilter},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    setLoadingItems(true)
    try {
      // Cargar items con paginación (backend limita a 1000 por request)
      const allItems: YangoReconciliationItemRow[] = []
      let offset = 0
      const chunkLimit = 1000
      let hasMore = true
      
      while (hasMore) {
        const response = await getYangoReconciliationItems({
          week_start: weekFilter,
          limit: chunkLimit,
          offset
        })
        
        allItems.push(...response.rows)
        
        // Si retornó menos items que el límite, no hay más
        if (response.rows.length < chunkLimit) {
          hasMore = false
        } else {
          offset += chunkLimit
          // Safety: evitar loops infinitos (máx 10 chunks = 10,000 items)
          if (offset >= 10000) {
            hasMore = false
          }
        }
      }
      
      // #region agent log
      // Comentado: propiedades no disponibles en tipo YangoReconciliationItemRow
      // fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:loadItemsForWeek:response',message:'Items loaded from API (paginated)',data:{totalItems:allItems.length,weekFilter,chunks:Math.ceil(allItems.length/chunkLimit),firstItem:allItems[0]?{expected_amount:allItems[0].expected_amount}:null,anomalyItemsCount:allItems.filter(i=>isAnomaly(i as any)).length},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'B,C'})}).catch(()=>{});
      // #endregion
      
      setItems(allItems)
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:loadItemsForWeek:error',message:'Error loading items',data:{error:String(err),weekFilter},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'B'})}).catch(()=>{});
      // #endregion
      console.error('Error cargando items Yango:', err)
    } finally {
      setLoadingItems(false)
    }
  }

  // Agregar por semana (pay_week_start_monday)
  // El summary ya viene agregado por semana, milestone y status
  // Necesitamos reagrupar solo por semana
  const weeklyData = summary.reduce((acc, row) => {
    const week = row.pay_week_start_monday || 'unknown'
    if (!acc[week]) {
      acc[week] = {
        week_start: week,
        amount_expected_sum: 0,
        amount_paid_sum: 0,
        amount_diff: 0,
        count_expected: 0,
        count_paid: 0,
        rows_count: 0,
        anomalies_count: 0
      }
    }
    // Usar amount_expected_sum de summary_ui si existe
    const expectedSum = row.amount_expected_sum ?? 0
    // Para paid_sum: usar amount_paid_sum de summary_ui si existe
    const paidSum = row.amount_paid_sum ?? 0
    
    acc[week].amount_expected_sum += expectedSum
    acc[week].amount_paid_sum += paidSum
    
    // Usar count_expected de summary_ui si existe
    acc[week].count_expected += row.count_expected ?? 0
    acc[week].count_paid += row.count_paid ?? 0
    acc[week].rows_count += (row as any).rows_count ?? (row as any).count_items ?? 0
    
    // Anomalías desde summary (puede ser 0, se recalcula en drilldown)
    // Comentado: propiedad no disponible en tipo
    // if (row.reconciliation_status === 'anomaly_paid_without_expected') {
    //   acc[week].anomalies_count += row.count_anomalies ?? row.count_items ?? row.rows_count ?? 0
    // }
    return acc
  }, {} as Record<string, {
    week_start: string
    amount_expected_sum: number
    amount_paid_sum: number
    amount_diff: number
    count_expected: number
    count_paid: number
    rows_count: number
    anomalies_count: number
  }>)

  // Calcular diff para cada semana
  Object.keys(weeklyData).forEach(week => {
    weeklyData[week].amount_diff = weeklyData[week].amount_expected_sum - weeklyData[week].amount_paid_sum
  })

  // Si hay items cargados para la semana seleccionada, recalcular anomalías reales
  if (hasWeekFilter && items.length > 0) {
    const weekItems = items.filter(item => {
      const effectiveWeek = effectiveWeekStartMonday(item)
      return effectiveWeek === weekFilter
    })
    const realAnomalies = weekItems.filter(item => isAnomaly(item as any)).length
    const weekKey = weekFilter
    if (weeklyData[weekKey]) {
      weeklyData[weekKey].anomalies_count = realAnomalies
      weeklyData[weekKey].rows_count = weekItems.length
    }
  }

  const weeklyRows = Object.values(weeklyData).sort((a, b) => 
    b.week_start.localeCompare(a.week_start)
  )

  // Calcular KPIs totales desde summary
  // Total Expected: sum expected_amount donde expected_amount != null
  // Total Paid: sum expected_amount donde paid_is_paid true OR paid_payment_key no null, y expected_amount != null
  const totalsFromSummary = useMemo(() => {
    const totals = weeklyRows.reduce((acc, row) => {
      acc.total_expected += row.amount_expected_sum
      acc.total_paid += (row as any).amount_paid_sum ?? 0
      return acc
    }, {
      total_expected: 0,
      total_paid: 0,
      total_diff: 0
    } as { total_expected: number; total_paid: number; total_diff: number })
    totals.total_diff = totals.total_expected - totals.total_paid
    return totals
  }, [weeklyRows])

  // Calcular anomalías reales desde items si hay semana seleccionada
  const realAnomaliesCount = useMemo(() => {
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:realAnomaliesCount:entry',message:'Calculating realAnomaliesCount',data:{hasWeekFilter,itemsCount:items.length},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'F'})}).catch(()=>{});
    // #endregion
    if (!hasWeekFilter || items.length === 0) {
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:realAnomaliesCount:early-return',message:'Early return from realAnomaliesCount',data:{hasWeekFilter,itemsCount:items.length},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'F'})}).catch(()=>{});
      // #endregion
      return null
    }
    
      const anomalyItems = items.filter(item => isAnomaly(item as any))
    const count = anomalyItems.length
    // #region agent log
    // Comentado: propiedades no disponibles en tipo YangoReconciliationItemRow
    // fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:realAnomaliesCount:result',message:'realAnomaliesCount calculated',data:{totalItems:items.length,anomalyCount:count,sampleItem:items[0]?{expected_amount:items[0].expected_amount,paid_payment_key:items[0].paid_payment_key}:null},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'D,F'})}).catch(()=>{});
    // #endregion
    return count
  }, [hasWeekFilter, items])

  // Calcular top motivos de anomalía (solo si hay semana seleccionada)
  const topReasons = useMemo(() => {
    if (!hasWeekFilter || items.length === 0) return []
    
      const anomalyItems = items.filter(item => isAnomaly(item as any))
    const reasonCounts: Record<string, { count: number; label: string; severity: 'high' | 'medium' | 'low' }> = {}
    
    anomalyItems.forEach(item => {
      const reason = computeAnomalyReason(item as any)
      if (!reasonCounts[reason.code]) {
        reasonCounts[reason.code] = {
          count: 0,
          label: reason.label,
          severity: reason.severity
        }
      }
      reasonCounts[reason.code].count++
    })
    
    return Object.entries(reasonCounts)
      .map(([code, data]) => ({ code, ...data }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5)
  }, [hasWeekFilter, items])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Cargando datos...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={loadSummary}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* KPIs Totales */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Expected</h3>
          <div className="text-2xl font-bold text-blue-600">{formatCurrency(totalsFromSummary.total_expected)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Paid</h3>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(totalsFromSummary.total_paid)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Diff</h3>
          <div className={`text-2xl font-bold ${totalsFromSummary.total_diff >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatCurrency(Math.abs(totalsFromSummary.total_diff))}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Anomalías</h3>
          {(() => {
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoDashboard.tsx:render:KPI-anomalies',message:'Rendering Total Anomalías KPI',data:{hasWeekFilter,realAnomaliesCount,itemsCount:items.length,loadingItems},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'F'})}).catch(()=>{});
            // #endregion
            if (hasWeekFilter && realAnomaliesCount !== null) {
              return <div className="text-2xl font-bold text-orange-600">{realAnomaliesCount}</div>
            } else if (hasWeekFilter && loadingItems) {
              return <div className="text-2xl font-bold text-gray-400">...</div>
            } else {
              return (
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-gray-400">—</span>
                  <span 
                    className="text-xs text-gray-500 cursor-help" 
                    title="Selecciona una semana para ver anomalías reales"
                  >
                    ℹ️
                  </span>
                </div>
              )
            }
          })()}
        </div>
      </div>

      {/* Tabla Semanal */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold">Dashboard Semanal</h3>
        </div>
        {weeklyRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semana</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Paid</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Diff</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Count Expected</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Count Paid</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Anomalías</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Anomaly %</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acción</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {weeklyRows.map((row) => (
                  <tr
                    key={row.week_start}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => onWeekClick(row.week_start)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {formatDate(row.week_start)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {formatCurrency(row.amount_expected_sum)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                      {formatCurrency((row as any).amount_paid_sum ?? 0)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                      row.amount_diff >= 0 ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {formatCurrency(Math.abs(row.amount_diff))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_expected}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_paid}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        row.anomalies_count > 0 ? 'bg-orange-100 text-orange-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {row.anomalies_count}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.rows_count > 0 ? (
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          (row.anomalies_count / row.rows_count) < 0.05 ? 'bg-green-100 text-green-800' :
                          (row.anomalies_count / row.rows_count) < 0.15 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {((row.anomalies_count / row.rows_count) * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onWeekClick(row.week_start)
                        }}
                        className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-xs"
                      >
                        Ver Detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">
            No hay datos disponibles
          </div>
        )}
      </div>

      {/* Top Motivos de Anomalía */}
      {hasWeekFilter && topReasons.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold">Top Motivos de Anomalía</h3>
            <p className="text-sm text-gray-600 mt-1">Semana: {formatDate(weekFilter!)}</p>
          </div>
          <div className="px-6 py-4">
            <div className="space-y-3">
              {topReasons.map((reason, idx) => {
                const totalAnomalies = items.filter(item => isAnomaly(item as any)).length
                const percentage = totalAnomalies > 0 ? (reason.count / totalAnomalies * 100).toFixed(1) : '0'
                return (
                  <div
                    key={reason.code}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    onClick={() => {
                      if (onReasonClick) {
                        onReasonClick(reason.code)
                        onWeekClick(weekFilter!)
                      }
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-500">#{idx + 1}</span>
                      <span className={`px-2 py-1 rounded-full text-xs border ${getSeverityColor(reason.severity)}`}>
                        {reason.label}
                      </span>
                      <span className="text-xs text-gray-500">({reason.code})</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold">{reason.count}</div>
                      <div className="text-xs text-gray-500">{percentage}%</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


