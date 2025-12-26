'use client'

import { useEffect, useState } from 'react'
import {
  getScoutSummary,
  getScoutOpenItems,
  getYangoSummary,
  getYangoReceivableItems,
  scoutLiquidationPreview,
  scoutLiquidationMarkPaid,
  ScoutSummary,
  ScoutOpenItems,
  YangoSummary,
  YangoReceivableItems,
  ScoutPreview
} from '@/lib/api'

type TabType = 'scouts' | 'yango'

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabType>('scouts')
  
  // Scout state
  const [scoutSummary, setScoutSummary] = useState<ScoutSummary | null>(null)
  const [scoutItems, setScoutItems] = useState<ScoutOpenItems | null>(null)
  const [scoutLoading, setScoutLoading] = useState(true)
  const [scoutWeekFilter, setScoutWeekFilter] = useState<string>('')
  const [scoutIdFilter, setScoutIdFilter] = useState<number | null>(null)
  const [scoutConfidence, setScoutConfidence] = useState<'policy' | 'unknown'>('policy')
  const [scoutPage, setScoutPage] = useState(0)
  
  // Modal state
  const [showMarkPaidModal, setShowMarkPaidModal] = useState(false)
  const [cutoffDate, setCutoffDate] = useState(new Date().toISOString().split('T')[0])
  const [paidBy, setPaidBy] = useState('finanzas')
  const [paymentRef, setPaymentRef] = useState('')
  const [notes, setNotes] = useState('')
  const [preview, setPreview] = useState<ScoutPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [markPaidLoading, setMarkPaidLoading] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  
  // Yango state
  const [yangoSummary, setYangoSummary] = useState<YangoSummary | null>(null)
  const [yangoItems, setYangoItems] = useState<YangoReceivableItems | null>(null)
  const [yangoLoading, setYangoLoading] = useState(true)
  const [yangoWeekFilter, setYangoWeekFilter] = useState<string>('')
  const [yangoPage, setYangoPage] = useState(0)
  
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
    } else {
      loadYangoData()
    }
  }, [activeTab, scoutWeekFilter, scoutIdFilter, scoutConfidence, scoutPage, yangoWeekFilter, yangoPage])

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
          scout_id: scoutIdFilter || undefined,
        }),
        getScoutOpenItems({
          week_start_monday: scoutWeekFilter || undefined,
          scout_id: scoutIdFilter || undefined,
          confidence: scoutConfidence,
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

  async function loadYangoData() {
    setYangoLoading(true)
    try {
      const weekStart = yangoWeekFilter ? new Date(yangoWeekFilter) : undefined
      const weekEnd = yangoWeekFilter ? new Date(yangoWeekFilter) : undefined
      if (weekEnd) weekEnd.setDate(weekEnd.getDate() + 6)

      const [summary, items] = await Promise.all([
        getYangoSummary({
          week_start: weekStart?.toISOString().split('T')[0],
          week_end: weekEnd?.toISOString().split('T')[0],
        }),
        getYangoReceivableItems({
          week_start_monday: yangoWeekFilter || undefined,
          limit,
          offset: yangoPage * limit,
        })
      ])
      setYangoSummary(summary)
      setYangoItems(items)
    } catch (error) {
      console.error('Error cargando datos Yango:', error)
    } finally {
      setYangoLoading(false)
    }
  }

  const weeks = getLast12Weeks()
  const topScouts = scoutSummary?.top_scouts || []

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard de Pagos</h1>

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
            Liquidación Scouts
          </button>
          <button
            onClick={() => setActiveTab('yango')}
            className={`px-4 py-2 font-medium ${
              activeTab === 'yango'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Cobranza Yango
          </button>
        </div>
      </div>

      {/* Scouts Tab */}
      {activeTab === 'scouts' && (
        <div>
          {/* Filtros */}
          <div className="bg-white rounded-lg shadow mb-6 p-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Filtros</h2>
              {scoutIdFilter && (
                <button
                  onClick={() => setShowMarkPaidModal(true)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Marcar Pagado
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
              <div>
                <label className="block text-sm font-medium mb-2">Scout</label>
                <select
                  value={scoutIdFilter || ''}
                  onChange={(e) => {
                    setScoutIdFilter(e.target.value ? parseInt(e.target.value) : null)
                    setScoutPage(0)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                >
                  <option value="">Todos</option>
                  {topScouts.map((scout) => (
                    <option key={scout.acquisition_scout_id} value={scout.acquisition_scout_id}>
                      {scout.acquisition_scout_name || `Scout ${scout.acquisition_scout_id}`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Confidence</label>
                <select
                  value={scoutConfidence}
                  onChange={(e) => {
                    setScoutConfidence(e.target.value as 'policy' | 'unknown')
                    setScoutPage(0)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                >
                  <option value="policy">Policy (High+Medium)</option>
                  <option value="unknown">Unknown (Bloqueados)</option>
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
                  <h3 className="text-lg font-semibold mb-4 text-green-600">Pagable</h3>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold">{formatCurrency(scoutSummary?.totals.payable_amount || 0)}</div>
                    <div className="text-sm text-gray-600">
                      {scoutSummary?.totals.payable_items || 0} items · {scoutSummary?.totals.payable_drivers || 0} drivers · {scoutSummary?.totals.payable_scouts || 0} scouts
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4 text-red-600">Bloqueado (Unknown)</h3>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold">{formatCurrency(scoutSummary?.totals.blocked_amount || 0)}</div>
                    <div className="text-sm text-gray-600">
                      {scoutSummary?.totals.blocked_items || 0} items
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabla Items */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b">
                  <h3 className="text-lg font-semibold">
                    Items {scoutConfidence === 'policy' ? 'Pagables' : 'Bloqueados'} ({scoutItems?.total || 0})
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
                <label className="block text-sm font-medium mb-2">Semana</label>
                <select
                  value={yangoWeekFilter}
                  onChange={(e) => {
                    setYangoWeekFilter(e.target.value)
                    setYangoPage(0)
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

          {yangoLoading ? (
            <div className="text-center py-12">Cargando...</div>
          ) : (
            <>
              {/* Cards */}
              <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h3 className="text-lg font-semibold mb-4 text-blue-600">Total por Cobrar</h3>
                <div className="space-y-2">
                  <div className="text-2xl font-bold">{formatCurrency(yangoSummary?.totals.receivable_amount || 0)}</div>
                  <div className="text-sm text-gray-600">
                    {yangoSummary?.totals.receivable_items || 0} items · {yangoSummary?.totals.receivable_drivers || 0} drivers
                  </div>
                </div>
              </div>

              {/* Tabla Items */}
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b">
                  <h3 className="text-lg font-semibold">
                    Items por Cobrar ({yangoItems?.total || 0})
                  </h3>
                </div>
                {yangoItems && yangoItems.items.length > 0 ? (
                  <>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semana</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origen</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Monto</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {yangoItems.items.map((item, idx) => (
                            <tr key={`${item.person_key}-${item.payable_date}-${idx}`}>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">{item.pay_iso_year_week}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm">
                                {formatDate(new Date(item.payable_date))}
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
                        Mostrando {yangoPage * limit + 1} - {Math.min((yangoPage + 1) * limit, yangoItems.total)} de {yangoItems.total}
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setYangoPage(Math.max(0, yangoPage - 1))}
                          disabled={yangoPage === 0}
                          className="px-4 py-2 border rounded-md disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <button
                          onClick={() => setYangoPage(yangoPage + 1)}
                          disabled={(yangoPage + 1) * limit >= yangoItems.total}
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

      {/* Modal Marcar Pagado */}
      {showMarkPaidModal && scoutIdFilter && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Marcar Items como Pagados</h2>
                <button
                  onClick={() => {
                    setShowMarkPaidModal(false)
                    setPreview(null)
                    setConfirmed(false)
                    setPaymentRef('')
                    setNotes('')
                  }}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Scout: {topScouts.find(s => s.acquisition_scout_id === scoutIdFilter)?.acquisition_scout_name || `Scout ${scoutIdFilter}`}
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Fecha de Corte *</label>
                  <input
                    type="date"
                    value={cutoffDate}
                    onChange={(e) => {
                      setCutoffDate(e.target.value)
                      setPreview(null)
                      setConfirmed(false)
                    }}
                    className="w-full px-4 py-2 border rounded-md"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Pagado por *</label>
                  <input
                    type="text"
                    value={paidBy}
                    onChange={(e) => setPaidBy(e.target.value)}
                    className="w-full px-4 py-2 border rounded-md"
                    placeholder="finanzas"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Referencia de Pago *</label>
                  <input
                    type="text"
                    value={paymentRef}
                    onChange={(e) => setPaymentRef(e.target.value)}
                    className="w-full px-4 py-2 border rounded-md"
                    placeholder="TRX-2025-12-29-001"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Notas (opcional)</label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full px-4 py-2 border rounded-md"
                    rows={3}
                    placeholder="Pago semanal scout..."
                  />
                </div>

                <div className="flex space-x-4">
                  <button
                    onClick={async () => {
                      setPreviewLoading(true)
                      try {
                        const previewData = await scoutLiquidationPreview(scoutIdFilter, cutoffDate)
                        setPreview(previewData)
                      } catch (error: any) {
                        setToast({ message: error.message || 'Error obteniendo preview', type: 'error' })
                      } finally {
                        setPreviewLoading(false)
                      }
                    }}
                    disabled={previewLoading}
                    className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
                  >
                    {previewLoading ? 'Cargando...' : 'Previsualizar'}
                  </button>
                </div>

                {preview && (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <h3 className="font-semibold mb-2">Previsualización</h3>
                    <div className="space-y-1">
                      <div>Items: <strong>{preview.preview_items}</strong></div>
                      <div>Monto: <strong>{formatCurrency(preview.preview_amount)}</strong></div>
                    </div>
                  </div>
                )}

                {preview && preview.preview_items > 0 && (
                  <div>
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={confirmed}
                        onChange={(e) => setConfirmed(e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span>Confirmo que deseo marcar estos items como pagados</span>
                    </label>
                  </div>
                )}

                <div className="flex justify-end space-x-4 pt-4 border-t">
                  <button
                    onClick={() => {
                      setShowMarkPaidModal(false)
                      setPreview(null)
                      setConfirmed(false)
                      setPaymentRef('')
                      setNotes('')
                    }}
                    className="px-4 py-2 border rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={async () => {
                      if (!paymentRef.trim()) {
                        setToast({ message: 'La referencia de pago es requerida', type: 'error' })
                        return
                      }
                      if (!confirmed) {
                        setToast({ message: 'Debe confirmar la operación', type: 'error' })
                        return
                      }
                      if (!preview || preview.preview_items === 0) {
                        setToast({ message: 'No hay items para marcar como pagados', type: 'error' })
                        return
                      }

                      setMarkPaidLoading(true)
                      try {
                        const adminToken = localStorage.getItem('admin_token') || ''
                        if (!adminToken) {
                          setToast({ message: 'Token de administrador no encontrado. Configurelo en localStorage con clave "admin_token"', type: 'error' })
                          setMarkPaidLoading(false)
                          return
                        }

                        const result = await scoutLiquidationMarkPaid(
                          {
                            scout_id: scoutIdFilter,
                            cutoff_date: cutoffDate,
                            paid_by: paidBy,
                            payment_ref: paymentRef,
                            notes: notes || undefined,
                          },
                          adminToken
                        )

                        setToast({
                          message: `Se marcaron ${result.inserted_items} items como pagados por un total de ${formatCurrency(result.inserted_amount)}`,
                          type: 'success'
                        })

                        // Refrescar datos
                        await loadScoutData()

                        // Cerrar modal después de un delay
                        setTimeout(() => {
                          setShowMarkPaidModal(false)
                          setPreview(null)
                          setConfirmed(false)
                          setPaymentRef('')
                          setNotes('')
                          setToast(null)
                        }, 2000)
                      } catch (error: any) {
                        setToast({ message: error.message || 'Error marcando items como pagados', type: 'error' })
                      } finally {
                        setMarkPaidLoading(false)
                      }
                    }}
                    disabled={markPaidLoading || !paymentRef.trim() || !confirmed || !preview || preview.preview_items === 0}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {markPaidLoading ? 'Procesando...' : 'Ejecutar Pago'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 px-6 py-4 rounded-md shadow-lg z-50 ${
          toast.type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
        }`}>
          <div className="flex justify-between items-center">
            <span>{toast.message}</span>
            <button
              onClick={() => setToast(null)}
              className="ml-4 text-white hover:text-gray-200"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

