'use client'

import { useEffect, useState } from 'react'
import { getCabinetPaymentEvidencePack, CabinetPaymentEvidencePackRow } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

interface ClaimsDrilldownProps {
  weekStart: string
  milestone: number
  onClose: () => void
}

export default function ClaimsDrilldown({ weekStart, milestone, onClose }: ClaimsDrilldownProps) {
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<CabinetPaymentEvidencePackRow[]>([])
  const [selectedItem, setSelectedItem] = useState<CabinetPaymentEvidencePackRow | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadItems()
  }, [weekStart, milestone])

  async function loadItems() {
    setLoading(true)
    setError(null)
    try {
      const allItems: CabinetPaymentEvidencePackRow[] = []
      let offset = 0
      const chunkLimit = 1000
      let hasMore = true

      while (hasMore) {
        const response = await getCabinetPaymentEvidencePack({
          week_start: weekStart,
          milestone_value: milestone,
          limit: chunkLimit,
          offset,
        })
        allItems.push(...response.rows)
        if (response.rows.length < chunkLimit) {
          hasMore = false
        } else {
          offset += chunkLimit
          if (offset >= 10000) {
            hasMore = false
          }
        }
      }
      setItems(allItems)
    } catch (err: any) {
      console.error('Error cargando evidence pack:', err)
      setError(err.message || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-green-100 text-green-800'
      case 'not_paid':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getEvidenceLevelColor = (level: string) => {
    switch (level) {
      case 'driver_id_exact':
        return 'bg-green-100 text-green-800'
      case 'person_key_only':
        return 'bg-yellow-100 text-yellow-800'
      case 'other_milestone':
        return 'bg-orange-100 text-orange-800'
      case 'none':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getEvidenceLevelLabel = (level: string) => {
    switch (level) {
      case 'driver_id_exact':
        return 'Driver ID Exacto'
      case 'person_key_only':
        return 'Solo Person Key'
      case 'other_milestone':
        return 'Otro Milestone'
      case 'none':
        return 'Sin Evidencia'
      default:
        return level
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // Opcional: mostrar notificación
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-[95vw] max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Claims Detallados - Evidence Pack</h2>
            <p className="text-sm text-gray-600 mt-1">
              Semana: {formatDate(weekStart)} | Milestone: {milestone} | Total: {items.length} registros
            </p>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            ✕ Cerrar
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 flex gap-4">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Cargando datos...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-600">
              <p>Error: {error}</p>
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No hay registros disponibles
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected Amount</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evidence Level</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Key</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Date</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason Code</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {items.map((item, idx) => (
                      <tr 
                        key={idx} 
                        className={`hover:bg-gray-50 cursor-pointer ${selectedItem === item ? 'bg-blue-50' : ''}`}
                        onClick={() => setSelectedItem(item)}
                      >
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-mono">
                          {item.claim_driver_id || '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          {item.claim_milestone_value}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                          {formatCurrency(item.expected_amount)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColor(item.payment_status)}`}>
                            {item.payment_status === 'paid' ? 'Paid' : 'Not Paid'}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEvidenceLevelColor(item.evidence_level)}`}>
                            {getEvidenceLevelLabel(item.evidence_level)}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-xs">
                          {item.payment_key ? (
                            <div className="flex items-center gap-2">
                              <span className="truncate max-w-[120px]">{item.payment_key}</span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(item.payment_key!)
                                }}
                                className="text-blue-600 hover:text-blue-800"
                                title="Copiar"
                              >
                                📋
                              </button>
                            </div>
                          ) : '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                          {item.pay_date ? formatDate(item.pay_date) : '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                          {item.reason_code}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Panel lateral de Evidencia */}
              {selectedItem && (
                <div className="w-96 bg-gray-50 border-l border-gray-200 p-6 overflow-y-auto">
                  <div className="mb-4 flex justify-between items-center">
                    <h3 className="text-lg font-semibold">Evidencia</h3>
                    <button
                      onClick={() => setSelectedItem(null)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="space-y-4">
                    {/* Driver ID Comparison */}
                    <div className="bg-white p-4 rounded-lg border border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Driver ID</h4>
                      <div className="space-y-2 text-sm">
                        <div>
                          <span className="text-gray-600">Claim:</span>
                          <span className="ml-2 font-mono font-medium">{selectedItem.claim_driver_id || 'NULL'}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Pago (Ledger):</span>
                          <span className={`ml-2 font-mono font-medium ${
                            selectedItem.ledger_driver_id_final === selectedItem.claim_driver_id 
                              ? 'text-green-600' 
                              : 'text-orange-600'
                          }`}>
                            {selectedItem.ledger_driver_id_final || 'NULL'}
                          </span>
                        </div>
                        {selectedItem.ledger_driver_id_final === selectedItem.claim_driver_id && (
                          <div className="text-green-600 text-xs mt-1">✓ Match exacto</div>
                        )}
                      </div>
                    </div>

                    {/* Person Key Comparison */}
                    {(selectedItem.claim_person_key || selectedItem.ledger_person_key_original) && (
                      <div className="bg-white p-4 rounded-lg border border-gray-200">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Person Key</h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-600">Claim:</span>
                            <span className="ml-2 font-mono text-xs font-medium">{selectedItem.claim_person_key || 'NULL'}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Pago (Ledger):</span>
                            <span className={`ml-2 font-mono text-xs font-medium ${
                              selectedItem.ledger_person_key_original === selectedItem.claim_person_key 
                                ? 'text-green-600' 
                                : 'text-orange-600'
                            }`}>
                              {selectedItem.ledger_person_key_original || 'NULL'}
                            </span>
                          </div>
                          {selectedItem.ledger_person_key_original === selectedItem.claim_person_key && selectedItem.claim_person_key && (
                            <div className="text-green-600 text-xs mt-1">✓ Match por Person Key</div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Matching Info */}
                    {selectedItem.payment_key && (
                      <div className="bg-white p-4 rounded-lg border border-gray-200">
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Matching</h4>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-gray-600">Match Rule:</span>
                            <span className="ml-2 font-medium">{selectedItem.match_rule || '-'}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">Match Confidence:</span>
                            <span className={`ml-2 font-medium ${
                              selectedItem.match_confidence === 'high' ? 'text-green-600' :
                              selectedItem.match_confidence === 'medium' ? 'text-yellow-600' :
                              'text-gray-600'
                            }`}>
                              {selectedItem.match_confidence || '-'}
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">Identity Status:</span>
                            <span className="ml-2 font-medium">{selectedItem.identity_status || '-'}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Milestone Info for other_milestone */}
                    {selectedItem.reason_code === 'payment_found_other_milestone' && selectedItem.milestone_paid && (
                      <div className="bg-white p-4 rounded-lg border border-orange-200 bg-orange-50">
                        <h4 className="text-sm font-medium text-orange-800 mb-2">⚠ Pago en Otro Milestone</h4>
                        <div className="text-sm">
                          <span className="text-gray-600">Claim Milestone:</span>
                          <span className="ml-2 font-medium">{selectedItem.claim_milestone_value}</span>
                        </div>
                        <div className="text-sm mt-1">
                          <span className="text-gray-600">Milestone del Pago:</span>
                          <span className="ml-2 font-medium text-orange-600">{selectedItem.milestone_paid}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

