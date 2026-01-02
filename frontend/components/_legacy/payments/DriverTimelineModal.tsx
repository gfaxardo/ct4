'use client'

import { useEffect, useState } from 'react'
// PENDING: Este componente requiere funciones que no están en el contrato
// import { getDriverTimeline, DriverTimelineRow } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

// Tipo stub para compilación
type DriverTimelineRow = any;

interface DriverTimelineModalProps {
  driverId: string
  onClose: () => void
}

export default function DriverTimelineModal({ driverId, onClose }: DriverTimelineModalProps) {
  const [loading, setLoading] = useState(true)
  const [timeline, setTimeline] = useState<DriverTimelineRow[]>([])
  const [driverName, setDriverName] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [includeEvidence, setIncludeEvidence] = useState(false)

  useEffect(() => {
    loadTimeline()
  }, [driverId, includeEvidence])

  async function loadTimeline() {
    setLoading(true)
    setError(null)
    try {
      // PENDING: Función no disponible en contrato
      // const response = await getDriverTimeline(driverId, includeEvidence)
      const response = { rows: [] as any[], driver_name_display: '' }; // Stub
      setTimeline(response.rows)
      setDriverName(response.driver_name_display)
    } catch (err: any) {
      console.error('Error cargando timeline:', err)
      setError(err.message || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedRows(newExpanded)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // Opcional: mostrar notificación
    })
  }

  const getBucketColor = (bucket: string) => {
    if (bucket === '0_not_due') return 'bg-gray-100 text-gray-800'
    if (bucket.startsWith('1_')) return 'bg-green-100 text-green-800'
    if (bucket.startsWith('2_')) return 'bg-yellow-100 text-yellow-800'
    if (bucket.startsWith('3_')) return 'bg-orange-100 text-orange-800'
    if (bucket.startsWith('4_') || bucket.startsWith('5_')) return 'bg-red-100 text-red-800'
    return 'bg-gray-100 text-gray-800'
  }

  const getEvidenceLevelColor = (level?: string | null) => {
    if (!level) return 'bg-gray-100 text-gray-800'
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Driver Timeline</h2>
            <p className="text-sm text-gray-600 mt-1">
              {driverName} ({driverId})
            </p>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeEvidence}
                onChange={(e) => setIncludeEvidence(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Incluir Evidencia</span>
            </label>
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              ✕ Cerrar
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Cargando timeline...</p>
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-600">
              <p>Error: {error}</p>
            </div>
          ) : timeline.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No hay registros disponibles
            </div>
          ) : (
            <div className="space-y-4">
              {timeline.map((row, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div 
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => toggleRow(index)}
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <div className="text-sm font-medium text-gray-900 w-32">
                        {formatDate(row.lead_date)}
                      </div>
                      <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                        Milestone {row.milestone_value}
                      </div>
                      <div className="text-sm text-right w-32 font-medium">
                        {formatCurrency(row.expected_amount)}
                      </div>
                      <div className="flex items-center gap-2">
                        {row.paid_flag ? (
                          <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                            ✓ Paid
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-medium">
                            ✗ Not Paid
                          </span>
                        )}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getBucketColor(row.bucket_overdue)}`}>
                          {row.bucket_overdue}
                        </span>
                      </div>
                      {row.payment_key && (
                        <div className="text-xs text-gray-500 font-mono">
                          {row.payment_key.substring(0, 12)}...
                        </div>
                      )}
                    </div>
                    <div className="text-gray-400">
                      {expandedRows.has(index) ? '▼' : '▶'}
                    </div>
                  </div>

                  {expandedRows.has(index) && (
                    <div className="mt-4 pt-4 border-t border-gray-200 space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-600">Reason Code:</span>
                          <span className="ml-2 font-medium">{row.reason_code}</span>
                        </div>
                        {row.pay_date && (
                          <div>
                            <span className="text-gray-600">Paid Date:</span>
                            <span className="ml-2 font-medium">{formatDate(row.pay_date)}</span>
                          </div>
                        )}
                        {row.payment_key && (
                          <div className="col-span-2">
                            <span className="text-gray-600">Payment Key:</span>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                                {row.payment_key}
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  copyToClipboard(row.payment_key!)
                                }}
                                className="text-blue-600 hover:text-blue-800 text-xs"
                              >
                                📋 Copiar
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Sección de Evidencia (colapsable) */}
                      {includeEvidence && (row.evidence_level || row.match_rule) && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <h4 className="text-sm font-semibold text-gray-700 mb-3">
                            Evidencia (para Yango)
                          </h4>
                          <div className="bg-gray-50 rounded-lg p-4 space-y-3 text-sm">
                            {row.evidence_level && (
                              <div>
                                <span className="text-gray-600">Evidence Level:</span>
                                <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${getEvidenceLevelColor(row.evidence_level)}`}>
                                  {row.evidence_level}
                                </span>
                              </div>
                            )}
                            {row.match_rule && (
                              <div>
                                <span className="text-gray-600">Match Rule:</span>
                                <span className="ml-2 font-medium">{row.match_rule}</span>
                              </div>
                            )}
                            {row.match_confidence && (
                              <div>
                                <span className="text-gray-600">Match Confidence:</span>
                                <span className={`ml-2 font-medium ${
                                  row.match_confidence === 'high' ? 'text-green-600' :
                                  row.match_confidence === 'medium' ? 'text-yellow-600' :
                                  'text-gray-600'
                                }`}>
                                  {row.match_confidence}
                                </span>
                              </div>
                            )}
                            {row.identity_status && (
                              <div>
                                <span className="text-gray-600">Identity Status:</span>
                                <span className="ml-2 font-medium">{row.identity_status}</span>
                              </div>
                            )}
                            {row.ledger_driver_id_final && (
                              <div>
                                <span className="text-gray-600">Ledger Driver ID:</span>
                                <span className="ml-2 font-mono text-xs">{row.ledger_driver_id_final}</span>
                              </div>
                            )}
                            {row.ledger_person_key_original && (
                              <div>
                                <span className="text-gray-600">Ledger Person Key:</span>
                                <span className="ml-2 font-mono text-xs">{row.ledger_person_key_original}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

