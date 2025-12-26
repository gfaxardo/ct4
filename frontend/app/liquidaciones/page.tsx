'use client'

import { useEffect, useState } from 'react'
import {
  getScoutSummary,
  scoutLiquidationPreview,
  scoutLiquidationMarkPaid,
  ScoutSummary,
  ScoutPreview
} from '@/lib/api'

export default function LiquidacionesPage() {
  const [scoutSummary, setScoutSummary] = useState<ScoutSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedScoutId, setSelectedScoutId] = useState<number | null>(null)
  const [cutoffDate, setCutoffDate] = useState(new Date().toISOString().split('T')[0])
  const [preview, setPreview] = useState<ScoutPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  
  // Modal state
  const [showMarkPaidModal, setShowMarkPaidModal] = useState(false)
  const [paidBy, setPaidBy] = useState('finanzas')
  const [paymentRef, setPaymentRef] = useState('')
  const [notes, setNotes] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [markPaidLoading, setMarkPaidLoading] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  useEffect(() => {
    loadScoutSummary()
  }, [])

  async function loadScoutSummary() {
    setLoading(true)
    try {
      const summary = await getScoutSummary({})
      setScoutSummary(summary)
    } catch (error) {
      console.error('Error cargando resumen scout:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handlePreview() {
    if (!selectedScoutId) {
      setToast({ message: 'Debe seleccionar un scout', type: 'error' })
      return
    }

    setPreviewLoading(true)
    try {
      const previewData = await scoutLiquidationPreview(selectedScoutId, cutoffDate)
      setPreview(previewData)
      if (previewData.preview_items === 0) {
        setToast({ message: 'No hay items para marcar como pagados con estos criterios', type: 'error' })
      }
    } catch (error: any) {
      setToast({ message: error.message || 'Error obteniendo preview', type: 'error' })
      setPreview(null)
    } finally {
      setPreviewLoading(false)
    }
  }

  async function handleMarkPaid() {
    if (!selectedScoutId) {
      setToast({ message: 'Debe seleccionar un scout', type: 'error' })
      return
    }
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
        setToast({ 
          message: 'Token de administrador no encontrado. Configurelo en localStorage con clave "admin_token"', 
          type: 'error' 
        })
        setMarkPaidLoading(false)
        return
      }

      const result = await scoutLiquidationMarkPaid(
        {
          scout_id: selectedScoutId,
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

      // Refrescar preview
      await handlePreview()

      // Cerrar modal después de un delay
      setTimeout(() => {
        setShowMarkPaidModal(false)
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
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  const topScouts = scoutSummary?.top_scouts || []
  const selectedScout = topScouts.find(s => s.acquisition_scout_id === selectedScoutId)

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">LIQUIDACIONES ✅ V2</h1>

      {loading ? (
        <div className="text-center py-12">Cargando...</div>
      ) : (
        <div className="space-y-6">
          {/* Selectores */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Configuración de Liquidación</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Scout *</label>
                <select
                  value={selectedScoutId || ''}
                  onChange={(e) => {
                    setSelectedScoutId(e.target.value ? parseInt(e.target.value) : null)
                    setPreview(null)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                >
                  <option value="">Seleccionar scout...</option>
                  {topScouts.map((scout) => (
                    <option key={scout.acquisition_scout_id} value={scout.acquisition_scout_id}>
                      {scout.acquisition_scout_name || `Scout ${scout.acquisition_scout_id}`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Fecha de Corte *</label>
                <input
                  type="date"
                  value={cutoffDate}
                  onChange={(e) => {
                    setCutoffDate(e.target.value)
                    setPreview(null)
                  }}
                  className="w-full px-4 py-2 border rounded-md"
                />
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={handlePreview}
                disabled={!selectedScoutId || previewLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {previewLoading ? 'Cargando...' : 'Previsualizar'}
              </button>
            </div>
          </div>

          {/* Preview Results */}
          {preview && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Previsualización</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Items</p>
                  <p className="text-2xl font-bold">{preview.preview_items}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Monto Total</p>
                  <p className="text-2xl font-bold">{formatCurrency(preview.preview_amount)}</p>
                </div>
              </div>
              {preview.preview_items > 0 && (
                <button
                  onClick={() => setShowMarkPaidModal(true)}
                  className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  Marcar Pagado
                </button>
              )}
            </div>
          )}

          {/* Instrucciones */}
          {!preview && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                Seleccione un scout y una fecha de corte, luego haga clic en "Previsualizar" para ver los items que serán marcados como pagados.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Modal Marcar Pagado */}
      {showMarkPaidModal && selectedScoutId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Marcar Items como Pagados</h2>
                <button
                  onClick={() => {
                    setShowMarkPaidModal(false)
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
                    Scout: {selectedScout?.acquisition_scout_name || `Scout ${selectedScoutId}`}
                  </label>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Fecha de Corte</label>
                  <input
                    type="date"
                    value={cutoffDate}
                    disabled
                    className="w-full px-4 py-2 border rounded-md bg-gray-100"
                  />
                </div>

                {preview && (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <h3 className="font-semibold mb-2">Resumen</h3>
                    <div className="space-y-1">
                      <div>Items: <strong>{preview.preview_items}</strong></div>
                      <div>Monto: <strong>{formatCurrency(preview.preview_amount)}</strong></div>
                    </div>
                  </div>
                )}

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

                <div className="flex justify-end space-x-4 pt-4 border-t">
                  <button
                    onClick={() => {
                      setShowMarkPaidModal(false)
                      setConfirmed(false)
                      setPaymentRef('')
                      setNotes('')
                    }}
                    className="px-4 py-2 border rounded-md hover:bg-gray-50"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleMarkPaid}
                    disabled={markPaidLoading || !paymentRef.trim() || !confirmed}
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

