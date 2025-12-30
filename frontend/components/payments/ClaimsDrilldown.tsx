'use client'

import { useEffect, useState } from 'react'
import { getClaimsCabinet, ClaimsCabinetRow } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

interface ClaimsDrilldownProps {
  weekStart: string
  milestone: number
  onClose: () => void
}

export default function ClaimsDrilldown({ weekStart, milestone, onClose }: ClaimsDrilldownProps) {
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<ClaimsCabinetRow[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadItems()
  }, [weekStart, milestone])

  async function loadItems() {
    setLoading(true)
    setError(null)
    try {
      const allItems: ClaimsCabinetRow[] = []
      let offset = 0
      const chunkLimit = 1000
      let hasMore = true

      while (hasMore) {
        const response = await getClaimsCabinet({
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
      console.error('Error cargando items claims cabinet:', err)
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Claims Detallados</h2>
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
        <div className="flex-1 overflow-auto p-6">
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
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected Amount</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Paid Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Key</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-mono">
                        {item.driver_id || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        {item.milestone_value}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-right">
                        {formatCurrency(item.expected_amount)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColor(item.payment_status)}`}>
                          {item.payment_status === 'paid' ? 'Paid' : 'Not Paid'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {item.payment_reason === 'payment_found' ? 'Payment Found' : 'No Payment Found'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        {item.paid_date ? formatDate(item.paid_date) : '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-xs">
                        {item.payment_key || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

