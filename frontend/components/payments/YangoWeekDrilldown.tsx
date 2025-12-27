'use client'

import { useEffect, useState, useMemo } from 'react'
import { getYangoReconciliationItems, YangoReconciliationItemRow } from '@/lib/api'
import { exportToCSV } from './utils/csv'
import DebugPanel from './DebugPanel'

interface YangoWeekDrilldownProps {
  weekStart: string
  onClose: () => void
  initialReasonFilter?: string
}

type TabType = 'pagados' | 'pending_active' | 'vencidos' | 'todos'

export default function YangoWeekDrilldown({
  weekStart,
  onClose,
  initialReasonFilter
}: YangoWeekDrilldownProps) {
  const [activeTab, setActiveTab] = useState<TabType>('vencidos') // Default: vencidos (pending_expired)
  const [loading, setLoading] = useState(true)
  const [allItems, setAllItems] = useState<YangoReconciliationItemRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [filterMilestone, setFilterMilestone] = useState<string>('all')
  const [sinConductor, setSinConductor] = useState(false)
  const [showDriverDetail, setShowDriverDetail] = useState(false)
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null)
  const [driverDetail, setDriverDetail] = useState<YangoDriverDetailResponse | null>(null)
  const [driverDetailLoading, setDriverDetailLoading] = useState(false)
  const [page, setPage] = useState(0)
  const limit = 50

  useEffect(() => {
    loadItems()
  }, [weekStart, activeTab])

  async function loadItems() {
    setLoading(true)
    setError(null)
    try {
      let status: 'paid' | 'pending_active' | 'pending_expired' | undefined
      
      if (activeTab === 'pagados') {
        status = 'paid'
      } else if (activeTab === 'pending_active') {
        status = 'pending_active'
      } else if (activeTab === 'vencidos') {
        status = 'pending_expired'
      }
      // 'todos' no envía status (muestra todos)

      // Cargar todos los items de la semana con paginación (backend limita a 1000)
      const allItemsLoaded: YangoReconciliationItemRow[] = []
      let offset = 0
      const chunkLimit = 1000
      let hasMore = true
      
      while (hasMore) {
        const response = await getYangoReconciliationItems({
          week_start: weekStart,
          status,
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
      
      setAllItems(allItemsLoaded)
    } catch (err) {
      console.error('Error cargando items Yango:', err)
      setError('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  // Filtrar items según búsqueda y filtros
  const filteredItems = useMemo(() => {
    let filtered = [...allItems]

    // Filtro por texto (driver_id, person_key, driver name)
    if (searchText) {
      const searchLower = searchText.toLowerCase()
      filtered = filtered.filter(item =>
        (item.driver_id || '').toLowerCase().includes(searchLower) ||
        (item.person_key || '').toLowerCase().includes(searchLower) ||
        (item.paid_raw_driver_name || '').toLowerCase().includes(searchLower)
      )
    }

    // Filtro por milestone
    if (filterMilestone !== 'all') {
      filtered = filtered.filter(item => 
        item.milestone_value?.toString() === filterMilestone
      )
    }

    // Filtro "Solo SIN CONDUCTOR"
    if (sinConductor) {
      filtered = filtered.filter(item => !item.driver_id || item.driver_id === null || item.driver_id === '')
    }

    return filtered
  }, [allItems, searchText, filterMilestone, sinConductor])

  // Paginación
  const paginatedItems = filteredItems.slice(page * limit, (page + 1) * limit)
  const totalPages = Math.ceil(filteredItems.length / limit)

  // Calcular resumen desde paid_status real
  const summary = useMemo(() => {
    const statusCounts = {
      paid: allItems.filter(i => i.paid_status === 'paid').length,
      pending_active: allItems.filter(i => i.paid_status === 'pending_active').length,
      pending_expired: allItems.filter(i => i.paid_status === 'pending_expired').length
    }
    const totalExpected = allItems.reduce((sum, i) => sum + (i.expected_amount || 0), 0)
    const totalPaid = allItems
      .filter(i => i.paid_status === 'paid')
      .reduce((sum, i) => sum + (i.expected_amount || 0), 0)
    
    return {
      total: allItems.length,
      ...statusCounts,
      totalExpected,
      totalPaid,
      totalDiff: totalExpected - totalPaid
    }
  }, [allItems])

  const formatCurrency = (amount: number | null | undefined) => {
    if (amount == null) return '-'
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  // Obtener color del chip según paid_status
  const getPaidStatusColor = (paidStatus: string | null | undefined) => {
    switch (paidStatus) {
      case 'paid':
        return 'bg-green-100 text-green-800'
      case 'pending_active':
        return 'bg-yellow-100 text-yellow-800'
      case 'pending_expired':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Obtener etiqueta según paid_status
  const getPaidStatusLabel = (paidStatus: string | null | undefined) => {
    switch (paidStatus) {
      case 'paid':
        return 'Pagado'
      case 'pending_active':
        return 'Pendiente Activo'
      case 'pending_expired':
        return 'Vencido'
      default:
        return paidStatus || '-'
    }
  }

  // Obtener color según window_status
  const getWindowStatusColor = (windowStatus: string | null | undefined) => {
    switch (windowStatus) {
      case 'active':
        return 'bg-blue-100 text-blue-800'
      case 'expired':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Obtener color del badge según identity_status
  const getIdentityStatusColor = (identityStatus: string | null | undefined) => {
    switch (identityStatus) {
      case 'confirmed':
        return 'bg-green-100 text-green-800'
      case 'enriched':
        return 'bg-yellow-100 text-yellow-800'
      case 'ambiguous':
        return 'bg-orange-100 text-orange-800'
      case 'no_match':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Obtener etiqueta según identity_status
  const getIdentityStatusLabel = (identityStatus: string | null | undefined) => {
    switch (identityStatus) {
      case 'confirmed':
        return 'Confirmado'
      case 'enriched':
        return 'Enriquecido'
      case 'ambiguous':
        return 'Ambiguo'
      case 'no_match':
        return 'Sin Match'
      default:
        return identityStatus || '-'
    }
  }

  // Obtener color del badge según match_confidence
  const getMatchConfidenceColor = (matchConfidence: string | null | undefined) => {
    switch (matchConfidence) {
      case 'high':
        return 'bg-green-100 text-green-800'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800'
      case 'low':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleExportCSV = () => {
    const csvData = filteredItems.map(item => ({
      'Semana': item.pay_week_start_monday || '',
      'Driver ID': item.driver_id || 'SIN CONDUCTOR',
      'Person Key': item.person_key || '',
      'Milestone': item.milestone_value || '',
      'Expected Amount': item.expected_amount || 0,
      'Currency': item.currency || '',
      'Lead Date': item.lead_date || '',
      'Due Date': item.due_date || '',
      'Window Status': item.window_status || '',
      'Paid Status': item.paid_status || '',
      'Paid Payment Key': item.paid_payment_key || '',
      'Paid Date': item.paid_date || '',
      'Is Paid Effective': item.is_paid_effective ? 'Sí' : 'No',
      'Identity Status': item.identity_status || '',
      'Match Method': item.match_method || '',
      'Match Rule': item.match_rule || '',
      'Match Confidence': item.match_confidence || ''
    }))

    const filename = `yango_reconciliation_${weekStart}_${new Date().toISOString().split('T')[0]}.csv`
    exportToCSV(csvData, filename)
  }

  // Items para mostrar (paginados)
  const displayItems = paginatedItems

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

  const filtersSent = {
    week_start: weekStart,
    status: activeTab === 'todos' ? undefined : activeTab === 'pagados' ? 'paid' : activeTab === 'pending_active' ? 'pending_active' : 'pending_expired',
    limit: 1000
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
            <p className="text-xs text-gray-500 mt-1">
              Pagados: {summary.paid} | Pendientes Activos: {summary.pending_active} | Vencidos: {summary.pending_expired}
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
            <button
              onClick={() => {
                setActiveTab('pending_active')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'pending_active'
                  ? 'border-yellow-500 text-yellow-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Pendientes Activos ({summary.pending_active})
            </button>
            <button
              onClick={() => {
                setActiveTab('vencidos')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'vencidos'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Vencidos ({summary.pending_expired})
            </button>
            <button
              onClick={() => {
                setActiveTab('todos')
                setPage(0)
              }}
              className={`px-4 py-2 font-medium border-b-2 ${
                activeTab === 'todos'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              Todos ({summary.total})
            </button>
          </div>
        </div>

        {/* Filtros y Búsqueda */}
        <div className="px-6 py-4 bg-gray-50 border-b">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Búsqueda (Driver ID / Person Key)</label>
              <input
                type="text"
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value)
                  setPage(0)
                }}
                placeholder="Buscar por ID..."
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
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
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sinConductor}
                  onChange={(e) => {
                    setSinConductor(e.target.checked)
                    setPage(0)
                  }}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm font-medium text-gray-700">Solo SIN CONDUCTOR</span>
              </label>
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lead Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Window Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Identity Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Payment Key</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Is Paid Effective</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Method</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rule</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Confidence</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {displayItems.map((item, idx) => {
                    const uniqueKey = item.paid_payment_key || 
                      `${item.person_key || 'no-person'}_${item.milestone_value ?? 'no-milestone'}_${item.lead_date || 'no-date'}_${idx}`
                    return (
                      <tr key={uniqueKey} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                          {item.driver_id ? (
                            <button
                              onClick={() => loadDriverDetail(item.driver_id!)}
                              className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                            >
                              {item.driver_id}
                            </button>
                          ) : (
                            <span className="text-red-600 font-semibold">SIN CONDUCTOR</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                          {item.person_key || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.milestone_value || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                          {formatCurrency(item.expected_amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.currency || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {formatDate(item.lead_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {formatDate(item.due_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.window_status ? (
                            <span className={`px-2 py-1 rounded-full text-xs ${getWindowStatusColor(item.window_status)}`}>
                              {item.window_status}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${getPaidStatusColor(item.paid_status)}`}>
                            {getPaidStatusLabel(item.paid_status)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getIdentityStatusColor(item.identity_status)}`}>
                            {getIdentityStatusLabel(item.identity_status)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                          {item.paid_payment_key || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {formatDate(item.paid_date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            item.is_paid_effective ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {item.is_paid_effective ? 'Sí' : 'No'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.match_method || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.match_rule || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {item.match_confidence ? (
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMatchConfidenceColor(item.match_confidence)}`}>
                              {item.match_confidence}
                            </span>
                          ) : '-'}
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
        {totalPages > 1 && (
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

        {/* Modal: Detalle por Conductor */}
        {showDriverDetail && selectedDriverId && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
              {/* Header */}
              <div className="px-6 py-4 border-b flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold">Detalle por Conductor</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Driver ID: <span className="font-mono">{selectedDriverId}</span>
                    {driverDetail?.person_key && (
                      <> | Person Key: <span className="font-mono text-xs">{driverDetail.person_key}</span></>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setShowDriverDetail(false)
                    setSelectedDriverId(null)
                    setDriverDetail(null)
                  }}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  ✕ Cerrar
                </button>
              </div>

              {/* Contenido */}
              <div className="flex-1 overflow-auto p-6">
                {driverDetailLoading ? (
                  <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <p className="mt-2 text-gray-600">Cargando datos...</p>
                  </div>
                ) : driverDetail ? (
                  <div className="space-y-6">
                    {/* Resumen */}
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-3">Resumen</h3>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div>
                          <div className="text-sm text-gray-600">Total Expected</div>
                          <div className="text-xl font-bold text-blue-600">
                            {new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(driverDetail.summary.total_expected)}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-600">Total Paid</div>
                          <div className="text-xl font-bold text-green-600">
                            {new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(driverDetail.summary.total_paid)}
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-600">Pagados</div>
                          <div className="text-xl font-bold">{driverDetail.summary.count_paid}</div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-600">Pendientes Activos</div>
                          <div className="text-xl font-bold text-yellow-600">{driverDetail.summary.count_pending_active}</div>
                        </div>
                        <div>
                          <div className="text-sm text-gray-600">Pendientes Vencidos</div>
                          <div className="text-xl font-bold text-red-600">{driverDetail.summary.count_pending_expired}</div>
                        </div>
                      </div>
                    </div>

                    {/* Tabla de Claims */}
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Claims</h3>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expected Amount</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Lead Date</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Status</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Method</th>
                              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Date</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {driverDetail.claims.map((claim, idx) => (
                              <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-3 whitespace-nowrap text-sm">{claim.milestone_value || '-'}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  {claim.expected_amount ? new Intl.NumberFormat('es-PE', { style: 'currency', currency: claim.currency || 'PEN' }).format(claim.expected_amount) : '-'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  {claim.lead_date ? new Date(claim.lead_date).toLocaleDateString('es-ES') : '-'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  {claim.due_date ? new Date(claim.due_date).toLocaleDateString('es-ES') : '-'}
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  <span className={`px-2 py-1 rounded-full text-xs ${
                                    claim.paid_status === 'paid' ? 'bg-green-100 text-green-800' :
                                    claim.paid_status === 'pending_active' ? 'bg-yellow-100 text-yellow-800' :
                                    claim.paid_status === 'pending_expired' ? 'bg-red-100 text-red-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {claim.paid_status || '-'}
                                  </span>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  <span className={`px-2 py-1 rounded-full text-xs ${
                                    claim.match_method === 'driver_id' ? 'bg-blue-100 text-blue-800' :
                                    claim.match_method === 'person_key' ? 'bg-purple-100 text-purple-800' :
                                    'bg-gray-100 text-gray-800'
                                  }`}>
                                    {claim.match_method || 'none'}
                                  </span>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm">
                                  {claim.paid_date ? new Date(claim.paid_date).toLocaleDateString('es-ES') : '-'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="px-6 py-12 text-center text-gray-500">
                    No se pudo cargar el detalle del conductor
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Debug Panel */}
        <DebugPanel
          filtersSent={filtersSent}
          itemCounts={{
            total: allItems.length,
            loaded: allItems.length,
            filtered: filteredItems.length
          }}
          paidStatusDistribution={{
            paid: summary.paid,
            pending_active: summary.pending_active,
            pending_expired: summary.pending_expired
          }}
        />
      </div>
    </div>
  )
}
