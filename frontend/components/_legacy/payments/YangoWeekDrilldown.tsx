'use client'

import { useEffect, useState, useMemo } from 'react'
// Componente legacy - funciones movidas a lib/api.ts
import { getYangoReconciliationItems } from '@/lib/api'
import type { YangoReconciliationItemRow } from '@/lib/types'
import { computeAnomalyReason, getSeverityColor, isAnomaly } from './utils/reasons'
import { effectiveWeekStartMonday } from './utils/week'
import { exportToCSV } from './utils/csv'

interface YangoWeekDrilldownProps {
  weekStart: string
  onClose: () => void
  initialReasonFilter?: string
}

type TabType = 'resumen' | 'anomalias' | 'pendientes' | 'pagados'

export default function YangoWeekDrilldown({
  weekStart,
  onClose,
  initialReasonFilter
}: YangoWeekDrilldownProps) {
  const [activeTab, setActiveTab] = useState<TabType>('resumen')
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<YangoReconciliationItemRow[]>([])
  const [allItems, setAllItems] = useState<YangoReconciliationItemRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [filterReason, setFilterReason] = useState<string>(initialReasonFilter || 'all')
  const [filterSeverity, setFilterSeverity] = useState<string>('all')
  const [filterMilestone, setFilterMilestone] = useState<string>('all')
  const [filterConfidence, setFilterConfidence] = useState<string>('all')
  const [page, setPage] = useState(0)
  const limit = 50

  // Si hay filtro inicial de motivo, cambiar a tab anomalías
  useEffect(() => {
    if (initialReasonFilter) {
      setActiveTab('anomalias')
    }
  }, [initialReasonFilter])

  useEffect(() => {
    loadItems()
  }, [weekStart, activeTab])

  async function loadItems() {
    setLoading(true)
    setError(null)
    try {
      let status: 'paid' | 'pending' | 'anomaly_paid_without_expected' | undefined
      
      if (activeTab === 'anomalias') {
        status = 'anomaly_paid_without_expected'
      } else if (activeTab === 'pendientes') {
        status = 'pending'
      } else if (activeTab === 'pagados') {
        status = 'paid'
      }

      // Cargar todos los items de la semana con paginación (backend limita a 1000)
      const allItemsLoaded: YangoReconciliationItemRow[] = []
      let offset = 0
      const chunkLimit = 1000
      let hasMore = true
      
      while (hasMore) {
        const response = await getYangoReconciliationItems({
          week_start: weekStart,
          paid_status: status,
          limit: chunkLimit,
          offset
        })
        
        allItemsLoaded.push(...response.rows)
        
        if (response.rows.length < chunkLimit) {
          hasMore = false
        } else {
          offset += chunkLimit
          if (offset >= 10000) { // Safety limit
            hasMore = false
          }
        }
      }
      
      // Filtrar items por effective_week (no confiar solo en week_start del backend)
      const weekItems = allItemsLoaded.filter(item => {
        const effectiveWeek = effectiveWeekStartMonday(item)
        return effectiveWeek === weekStart
      })
      
      setAllItems(weekItems)
      setItems(weekItems)
    } catch (err) {
      console.error('Error cargando items Yango:', err)
      setError('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  // Items con campos derivados
  const itemsWithDerived = useMemo(() => {
    return allItems.map(item => {
      const reason = computeAnomalyReason(item as any)
      const effectiveWeek = effectiveWeekStartMonday(item)
      return {
        ...item,
        reason,
        isAnomaly: isAnomaly(item as any),
        effectiveWeek
      }
    })
  }, [allItems])

  // Filtrar items según búsqueda y filtros
  const filteredItems = useMemo(() => {
    let filtered = [...itemsWithDerived]

    // Filtro por texto (driver name)
    if (searchText) {
      const searchLower = searchText.toLowerCase()
      filtered = filtered.filter(item =>
        ((item as any).paid_raw_driver_name || '').toLowerCase().includes(searchLower) ||
        (item.driver_id || '').toLowerCase().includes(searchLower)
      )
    }

    // Filtro por motivo (reason)
    if (filterReason !== 'all') {
      filtered = filtered.filter(item => item.reason.code === filterReason)
    }

    // Filtro por severidad
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(item => item.reason.severity === filterSeverity)
    }

    // Filtro por milestone
    if (filterMilestone !== 'all') {
      filtered = filtered.filter(item => 
        item.milestone_value?.toString() === filterMilestone
      )
    }

    // Filtro por match confidence
    if (filterConfidence !== 'all') {
      filtered = filtered.filter(item => 
        (item as any).paid_match_confidence === filterConfidence
      )
    }

    // En tab Anomalías, solo mostrar items con isAnomaly = true
    if (activeTab === 'anomalias') {
      filtered = filtered.filter(item => item.isAnomaly)
    }

    return filtered
  }, [itemsWithDerived, searchText, filterReason, filterSeverity, filterMilestone, filterConfidence, activeTab])

  // Paginación
  const paginatedItems = filteredItems.slice(page * limit, (page + 1) * limit)
  const totalPages = Math.ceil(filteredItems.length / limit)

  // Obtener motivos únicos para filtro (solo anomalías)
  const uniqueReasons = useMemo(() => {
    const reasonsMap = new Map<string, { label: string; severity: 'high' | 'medium' | 'low' }>()
    itemsWithDerived
      .filter(item => item.isAnomaly)
      .forEach(item => {
        if (!reasonsMap.has(item.reason.code)) {
          reasonsMap.set(item.reason.code, {
            label: item.reason.label,
            severity: item.reason.severity
          })
        }
      })
    return Array.from(reasonsMap.entries())
      .map(([code, data]) => ({ code, ...data }))
      .sort((a, b) => {
        const severityOrder = { high: 0, medium: 1, low: 2 }
        return severityOrder[a.severity] - severityOrder[b.severity]
      })
  }, [itemsWithDerived])

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return '-'
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  const handleExportCSV = () => {
    const csvData = filteredItems.map(item => ({
      'Semana Efectiva': item.effectiveWeek || '',
      'Semana Original': item.pay_week_start_monday || '',
      'Fecha': item.sort_date || item.payable_date || item.paid_date || '',
      'Driver': (item as any).paid_raw_driver_name || '',
      'Milestone': item.milestone_value || '',
      'Expected Amount': item.expected_amount || 0,
      'Paid': item.paid_is_paid ? 'Sí' : 'No',
      'Status': item.reconciliation_status || '',
      'Reason Code': item.reason.code,
      'Reason Label': item.reason.label,
      'Severity': item.reason.severity,
      'Is Anomaly': item.isAnomaly ? 'Sí' : 'No',
      'Match Rule': item.paid_match_rule || '',
      'Match Confidence': (item as any).paid_match_confidence || '',
      'Driver ID': item.driver_id || '',
      'Person Key': item.person_key || ''
    }))

    const filename = `yango_reconciliation_${weekStart}_${new Date().toISOString().split('T')[0]}.csv`
    exportToCSV(csvData, filename)
  }

  // Calcular resumen por tab usando items con campos derivados
  const summary = useMemo(() => {
    const realAnomalies = itemsWithDerived.filter(i => i.isAnomaly).length
    const statusCounts = {
      paid: itemsWithDerived.filter(i => i.reconciliation_status === 'paid').length,
      pending: itemsWithDerived.filter(i => i.reconciliation_status === 'pending').length,
      anomaly: realAnomalies
    }
    const totalExpected = itemsWithDerived.reduce((sum, i) => sum + (i.expected_amount || 0), 0)
    // Para paid: sumar expected_amount de items donde paid_is_paid = true Y expected_amount != null
    const totalPaid = itemsWithDerived
      .filter(i => (i.paid_is_paid === true || i.paid_payment_key != null) && i.expected_amount != null)
      .reduce((sum, i) => sum + (i.expected_amount || 0), 0)
    
    return {
      total: itemsWithDerived.length,
      ...statusCounts,
      totalExpected,
      totalPaid,
      totalDiff: totalExpected - totalPaid
    }
  }, [itemsWithDerived])

  // Items para mostrar según tab activo
  // En resumen: mostrar todos (limitado a primeros 200 para performance)
  // En otros tabs: mostrar paginados
  const displayItems = useMemo(() => {
    const items = activeTab === 'resumen' 
      ? filteredItems.slice(0, 200) // Limitar resumen a 200 items
      : paginatedItems // Mostrar paginados en otros tabs
    
    // #region agent log
    // Detect duplicate keys using NEW unique key generation logic (same as render)
    const uniqueKeys = items.map((item, idx) => {
      return item.paid_payment_key || 
        `${item.person_key || 'no-person'}_${item.milestone_value ?? 'no-milestone'}_${item.sort_date || item.payable_date || item.paid_date || 'no-date'}_${idx}`
    })
    const keyCounts = new Map<string, number>()
    uniqueKeys.forEach(key => {
      keyCounts.set(key, (keyCounts.get(key) || 0) + 1)
    })
    const duplicates = Array.from(keyCounts.entries()).filter(([_, count]) => count > 1)
    if (duplicates.length > 0) {
      fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoWeekDrilldown.tsx:displayItems-duplicate-keys-NEW',message:'Found duplicate UNIQUE keys in displayItems',data:{totalItems:items.length,duplicateKeys:duplicates,duplicateCount:duplicates.length,sampleDuplicate:duplicates[0],itemsWithDuplicateKey:items.filter((item,idx)=>uniqueKeys[idx]===duplicates[0]?.[0]).slice(0,5).map((item,idx)=>({idx,uniqueKey:uniqueKeys[items.indexOf(item)],paid_payment_key:item.paid_payment_key,person_key:item.person_key,milestone_value:item.milestone_value,sort_date:item.sort_date}))},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'D'})}).catch(()=>{});
    } else {
      fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoWeekDrilldown.tsx:displayItems-no-duplicates',message:'No duplicate unique keys found',data:{totalItems:items.length,uniqueKeysCount:uniqueKeys.length,allKeysUnique:uniqueKeys.length===new Set(uniqueKeys).size},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'D'})}).catch(()=>{});
    }
    // #endregion
    
    return items
  }, [activeTab, filteredItems, paginatedItems])

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Cargando datos...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Detalle Semana: {formatDate(weekStart)}</h2>
            <p className="text-sm text-gray-600 mt-1">
              Total: {summary.total} items | Expected: {formatCurrency(summary.totalExpected)} | 
              Paid: {formatCurrency(summary.totalPaid)} | Diff: {formatCurrency(summary.totalDiff)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            ✕ Cerrar
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <div className="flex space-x-4 px-6">
            <button
              onClick={() => {
                setActiveTab('resumen')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'resumen'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Resumen ({summary.total})
            </button>
            <button
              onClick={() => {
                setActiveTab('anomalias')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'anomalias'
                  ? 'border-orange-500 text-orange-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Anomalías ({summary.anomaly})
            </button>
            <button
              onClick={() => {
                setActiveTab('pendientes')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'pendientes'
                  ? 'border-yellow-500 text-yellow-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pendientes ({summary.pending})
            </button>
            <button
              onClick={() => {
                setActiveTab('pagados')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'pagados'
                  ? 'border-green-500 text-green-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pagados ({summary.paid})
            </button>
          </div>
        </div>

        {/* Filtros y Búsqueda */}
        <div className="px-6 py-4 bg-gray-50 border-b">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Búsqueda (Driver)</label>
              <input
                type="text"
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value)
                  setPage(0)
                }}
                placeholder="Buscar por nombre..."
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
            {activeTab === 'anomalias' && (
              <>
                <div>
                  <label className="block text-sm font-medium mb-1">Motivo</label>
                  <select
                    value={filterReason}
                    onChange={(e) => {
                      setFilterReason(e.target.value)
                      setPage(0)
                    }}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="all">Todos</option>
                    {uniqueReasons.map(reason => (
                      <option key={reason.code} value={reason.code}>{reason.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Severidad</label>
                  <select
                    value={filterSeverity}
                    onChange={(e) => {
                      setFilterSeverity(e.target.value)
                      setPage(0)
                    }}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="all">Todas</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </>
            )}
            <div>
              <label className="block text-sm font-medium mb-1">Milestone</label>
              <select
                value={filterMilestone}
                onChange={(e) => {
                  setFilterMilestone(e.target.value)
                  setPage(0)
                }}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="all">Todos</option>
                <option value="1">1</option>
                <option value="5">5</option>
                <option value="25">25</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Match Confidence</label>
              <select
                value={filterConfidence}
                onChange={(e) => {
                  setFilterConfidence(e.target.value)
                  setPage(0)
                }}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="all">Todos</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
          </div>
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Mostrando {filteredItems.length} de {allItems.length} items
            </div>
            <button
              onClick={handleExportCSV}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
            >
              📥 Exportar CSV
            </button>
          </div>
        </div>

        {/* Tabla */}
        <div className="flex-1 overflow-auto">
          {error ? (
            <div className="px-6 py-12 text-center text-red-600">{error}</div>
          ) : filteredItems.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              No hay items para mostrar con los filtros aplicados
            </div>
          ) : displayItems.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected</th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Paid</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    {(activeTab === 'anomalias' || activeTab === 'resumen') && (
                      <>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Motivo</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rule</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
                      </>
                    )}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {displayItems.map((item, idx) => {
                    // #region agent log
                    const oldKey = `${item.paid_payment_key || item.person_key || idx}`
                    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoWeekDrilldown.tsx:table-row-key',message:'Generating key for table row',data:{idx,oldKey,paid_payment_key:item.paid_payment_key,person_key:item.person_key,milestone_value:item.milestone_value,sort_date:item.sort_date,payable_date:item.payable_date,paid_date:item.paid_date,hasPaidPaymentKey:!!item.paid_payment_key,hasPersonKey:!!item.person_key},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'A,B,C'})}).catch(()=>{});
                    // #endregion
                    // Generate unique key combining multiple fields to ensure uniqueness
                    // Priority: paid_payment_key (if exists) > person_key + milestone + date + idx
                    const uniqueKey = item.paid_payment_key || 
                      `${item.person_key || 'no-person'}_${item.milestone_value ?? 'no-milestone'}_${item.sort_date || item.payable_date || item.paid_date || 'no-date'}_${idx}`
                    // #region agent log
                    fetch('http://127.0.0.1:7243/ingest/baceb9d4-bf74-4f4f-b924-f2a8877afe92',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'YangoWeekDrilldown.tsx:table-row-key-unique',message:'Generated unique key',data:{idx,uniqueKey,oldKey,isDifferent:uniqueKey!==oldKey},timestamp:Date.now(),sessionId:'debug-session',runId:'post-fix',hypothesisId:'C'})}).catch(()=>{});
                    // #endregion
                    return (
                      <tr key={uniqueKey} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {(item as any).paid_raw_driver_name || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {formatDate(item.sort_date || item.payable_date || item.paid_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.milestone_value || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                          {formatCurrency(item.expected_amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            item.paid_is_paid ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {item.paid_is_paid ? 'Sí' : 'No'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            item.reconciliation_status === 'paid' ? 'bg-green-100 text-green-800' :
                            item.reconciliation_status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                        {item.reconciliation_status || '-'}
                      </span>
                    </td>
                    {(activeTab === 'anomalias' || activeTab === 'resumen') && (
                      <>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <div className="flex flex-col gap-1">
                            <span
                              className={`px-2 py-1 rounded-full text-xs border ${getSeverityColor(item.reason.severity)}`}
                              title={item.reason.code}
                            >
                              {item.reason.label}
                            </span>
                            {item.isAnomaly && (
                              <span className="text-xs text-gray-500">({item.reason.severity})</span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.paid_match_rule || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {(item as any).paid_match_confidence || '-'}
                        </td>
                      </>
                    )}
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                          {item.driver_id || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-gray-500">
              No hay items para mostrar
            </div>
          )}
        </div>

        {/* Paginación */}
        {activeTab !== 'resumen' && totalPages > 1 && (
          <div className="px-6 py-4 border-t flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Mostrando {page * limit + 1} - {Math.min((page + 1) * limit, filteredItems.length)} de {filteredItems.length}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="px-4 py-2 border rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="px-4 py-2 border rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
        {activeTab === 'resumen' && filteredItems.length > 200 && (
          <div className="px-6 py-4 border-t">
            <div className="text-sm text-gray-600">
              Mostrando primeros 200 de {filteredItems.length} items. Usa los tabs específicos para ver todos.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

