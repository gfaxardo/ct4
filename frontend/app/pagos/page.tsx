'use client'

import { useEffect, useState } from 'react'
import {
  getScoutSummary,
  getScoutOpenItems,
  ScoutSummary,
  ScoutOpenItems
} from '@/lib/api'
import YangoDashboard from '@/components/payments/YangoDashboard'
import YangoWeekDrilldown from '@/components/payments/YangoWeekDrilldown'

type TabType = 'scouts' | 'yango'

export default function PagosPage() {
  const [activeTab, setActiveTab] = useState<TabType>('scouts')
  
  // Scout state
  const [scoutSummary, setScoutSummary] = useState<ScoutSummary | null>(null)
  const [scoutItems, setScoutItems] = useState<ScoutOpenItems | null>(null)
  const [scoutLoading, setScoutLoading] = useState(true)
  const [scoutWeekFilter, setScoutWeekFilter] = useState<string>('')
  const [scoutPage, setScoutPage] = useState(0)
  
  // Yango state
  const [yangoWeekFilter, setYangoWeekFilter] = useState<string>('')
  const [selectedWeek, setSelectedWeek] = useState<string | null>(null)
  
  const limit = 50

  // Generate last 12 weeks
  const getLast12Weeks = () => {
    const weeks: Array<{ value: string; label: string }> = [{ value: '', label: 'Todas' }]
    const today = new Date()
    for (let i = 0; i < 12; i++) {
      const date = new Date(today)
      date.setDate(date.getDate() - (i * 7))
      const weekStart = new Date(date)
      weekStart.setDate(weekStart.getDate() - weekStart.getDay() + 1) // Monday
      const weekEnd = new Date(weekStart)
      weekEnd.setDate(weekEnd.getDate() + 6)
      const isoWeek = getISOWeek(weekStart)
      weeks.push({
        value: weekStart.toISOString().split('T')[0],
        label: `${isoWeek} (${formatDate(weekStart)} - ${formatDate(weekEnd)})`
      })
    }
    return weeks
  }

  const getISOWeek = (date: Date) => {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
    const dayNum = d.getUTCDay() || 7
    d.setUTCDate(d.getUTCDate() + 4 - dayNum)
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
    const weekNo = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
    return `${d.getUTCFullYear()}-W${String(weekNo).padStart(2, '0')}`
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  useEffect(() => {
    if (activeTab === 'scouts') {
      loadScoutData()
    }
    // Yango no necesita carga automática, el dashboard se carga internamente
  }, [activeTab, scoutWeekFilter, scoutPage])

  async function loadScoutData() {
    setScoutLoading(true)
    try {
      const weekStart = scoutWeekFilter ? new Date(scoutWeekFilter) : undefined
      let weekEnd = scoutWeekFilter ? new Date(scoutWeekFilter) : undefined
      if (weekEnd) weekEnd.setDate(weekEnd.getDate() + 6)

      const [summary, items] = await Promise.all([
        getScoutSummary({
          week_start: weekStart?.toISOString().split('T')[0],
          week_end: weekEnd?.toISOString().split('T')[0],
        }),
        getScoutOpenItems({
          week_start_monday: scoutWeekFilter || undefined,
          confidence: 'policy', // Solo policy (pagables)
          limit,
          offset: scoutPage * limit,
        })
      ])
      setScoutSummary(summary)
      setScoutItems(items)
    } catch (error) {
      console.error('Error cargando datos scout:', error)
    } finally {
      setScoutLoading(false)
    }
  }


  const weeks = getLast12Weeks()

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">PAGOS ✅ V2</h1>

      {/* Tabs */}
      <div className="border-b mb-6">
        <div className="flex space-x-4">
          <button
            onClick={() => setActiveTab('scouts')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'scouts'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Scouts
          </button>
          <button
            onClick={() => setActiveTab('yango')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'yango'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Yango
          </button>
        </div>
      </div>

      {/* Scouts Tab */}
      {activeTab === 'scouts' && (
        <div>
          {/* Filtros */}
          <div className="bg-white rounded-lg shadow mb-6 p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Semana</label>
                <select
                  value={scoutWeekFilter}
                  onChange={(e) => {
                    setScoutWeekFilter(e.target.value)
                    setScoutPage(0)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                >
                  {weeks.map((week) => (
                    <option key={week.value} value={week.value}>
                      {week.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {scoutLoading ? (
            <div className="text-center py-12">Cargando...</div>
          ) : (
            <>
              {/* Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4 text-green-600">Total Pagable</h3>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold">{formatCurrency(scoutSummary?.totals.payable_amount || 0)}</div>
                    <div className="text-sm text-gray-600">
                      {scoutSummary?.totals.payable_items || 0} items · {scoutSummary?.totals.payable_drivers || 0} drivers · {scoutSummary?.totals.payable_scouts || 0} scouts
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4 text-red-600">Total Bloqueado (Unknown)</h3>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold">{formatCurrency(scoutSummary?.totals.blocked_amount || 0)}</div>
                    <div className="text-sm text-gray-600">
                      {scoutSummary?.totals.blocked_items || 0} items
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabla Items Pagables */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b">
                  <h3 className="text-lg font-semibold">
                    Items Pagables ({scoutItems?.total || 0})
                  </h3>
                </div>
                {scoutItems && scoutItems.items.length > 0 ? (
                  <>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Scout</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origen</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Monto</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {scoutItems.items.map((item) => (
                            <tr key={item.payment_item_key}>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {item.payable_date ? formatDate(new Date(item.payable_date)) : '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {item.acquisition_scout_name || '-'}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">{item.lead_origin || '-'}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {item.milestone_type} {item.milestone_value ? `(${item.milestone_value})` : ''}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                {formatCurrency(item.amount)}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">{item.driver_id || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="px-6 py-4 border-t flex justify-between items-center">
                      <div className="text-sm text-gray-600">
                        Mostrando {scoutPage * limit + 1} - {Math.min((scoutPage + 1) * limit, scoutItems.total)} de {scoutItems.total}
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setScoutPage(Math.max(0, scoutPage - 1))}
                          disabled={scoutPage === 0}
                          className="px-4 py-2 border rounded-md disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <button
                          onClick={() => setScoutPage(scoutPage + 1)}
                          disabled={(scoutPage + 1) * limit >= scoutItems.total}
                          className="px-4 py-2 border rounded-md disabled:opacity-50"
                        >
                          Siguiente
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="px-6 py-12 text-center text-gray-500">No hay items</div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Yango Tab */}
      {activeTab === 'yango' && (
        <div>
          {/* Filtros */}
          <div className="bg-white rounded-lg shadow mb-6 p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Filtrar por Semana (opcional)</label>
                <select
                  value={yangoWeekFilter}
                  onChange={(e) => {
                    setYangoWeekFilter(e.target.value)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                >
                  {weeks.map((week) => (
                    <option key={week.value} value={week.value}>
                      {week.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Dashboard Yango */}
          <YangoDashboard
            weekFilter={yangoWeekFilter && yangoWeekFilter !== '' ? yangoWeekFilter : undefined}
            onWeekFilterChange={setYangoWeekFilter}
            onWeekClick={(weekStart) => setSelectedWeek(weekStart)}
            onReasonClick={(reasonCode) => {
              // Al hacer click en un motivo, abrir drilldown con ese filtro
              setSelectedWeek(yangoWeekFilter || weekStart)
            }}
          />

          {/* Drilldown Modal */}
          {selectedWeek && (
            <YangoWeekDrilldown
              weekStart={selectedWeek}
              onClose={() => setSelectedWeek(null)}
            />
          )}
        </div>
      )}
    </div>
  )
}

