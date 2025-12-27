'use client'

import { useState } from 'react'

interface DebugPanelProps {
  filtersSent?: Record<string, any>
  filtersReceived?: Record<string, any>
  mode?: string
  itemCounts?: {
    total?: number
    loaded?: number
    filtered?: number
  }
  summaryData?: any
  paidStatusDistribution?: {
    paid?: number
    pending_active?: number
    pending_expired?: number
  }
  ledgerCount?: number
}

export default function DebugPanel({
  filtersSent,
  filtersReceived,
  mode,
  itemCounts,
  summaryData
}: DebugPanelProps) {
  // Solo mostrar en desarrollo
  if (process.env.NODE_ENV !== 'development') {
    return null
  }

  const [isOpen, setIsOpen] = useState(false)

  if (!isOpen) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <button
          onClick={() => setIsOpen(true)}
          className="px-3 py-2 bg-gray-800 text-white text-xs rounded-md hover:bg-gray-700"
          title="Mostrar panel de debug"
        >
          🐛 Debug
        </button>
      </div>
    )
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-h-[80vh] bg-gray-900 text-white rounded-lg shadow-2xl overflow-hidden border border-gray-700">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-2 flex justify-between items-center border-b border-gray-700">
        <h3 className="text-sm font-semibold">🐛 Debug Panel</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-white text-lg"
          title="Cerrar"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="p-4 overflow-y-auto max-h-[calc(80vh-3rem)] space-y-4 text-xs">
        {/* Mode */}
        {mode && (
          <div>
            <div className="text-gray-400 mb-1">Mode:</div>
            <div className="bg-gray-800 px-2 py-1 rounded font-mono">{mode}</div>
          </div>
        )}

        {/* Filters Sent */}
        {filtersSent && Object.keys(filtersSent).length > 0 && (
          <div>
            <div className="text-gray-400 mb-1">Filtros Enviados:</div>
            <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto">
              {JSON.stringify(filtersSent, null, 2)}
            </pre>
          </div>
        )}

        {/* Filters Received */}
        {filtersReceived && Object.keys(filtersReceived).length > 0 && (
          <div>
            <div className="text-gray-400 mb-1">Filtros Recibidos (Backend):</div>
            <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto">
              {JSON.stringify(filtersReceived, null, 2)}
            </pre>
          </div>
        )}

        {/* Item Counts */}
        {itemCounts && (
          <div>
            <div className="text-gray-400 mb-1">Counts:</div>
            <div className="bg-gray-800 px-2 py-1 rounded">
              <div>Total: {itemCounts.total ?? 'N/A'}</div>
              {itemCounts.loaded !== undefined && <div>Loaded: {itemCounts.loaded}</div>}
              {itemCounts.filtered !== undefined && <div>Filtered: {itemCounts.filtered}</div>}
            </div>
          </div>
        )}

        {/* Summary Data (sample) */}
        {summaryData && (
          <div>
            <div className="text-gray-400 mb-1">Summary Data (Sample):</div>
            <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto text-xs">
              {JSON.stringify(
                {
                  expected_sum: summaryData.amount_expected_sum,
                  paid_sum: summaryData.amount_paid_sum,
                  paid_assumed: summaryData.amount_paid_assumed,
                  diff: summaryData.amount_diff,
                  diff_assumed: summaryData.amount_diff_assumed,
                  anomalies_total: summaryData.anomalies_total,
                  count_paid: summaryData.count_paid,
                  count_pending_active: summaryData.count_pending_active,
                  count_pending_expired: summaryData.count_pending_expired
                },
                null,
                2
              )}
            </pre>
          </div>
        )}

        {/* Paid Status Distribution */}
        {paidStatusDistribution && (
          <div>
            <div className="text-gray-400 mb-1">Paid Status Distribution (from summary):</div>
            <div className="bg-gray-800 px-2 py-1 rounded text-xs">
              <div>paid: {paidStatusDistribution.paid ?? 0}</div>
              <div>pending_active: {paidStatusDistribution.pending_active ?? 0}</div>
              <div>pending_expired: {paidStatusDistribution.pending_expired ?? 0}</div>
            </div>
          </div>
        )}

        {/* Ledger Count */}
        {ledgerCount !== undefined && (
          <div>
            <div className="text-gray-400 mb-1">Ledger Rows Count:</div>
            <div className="bg-gray-800 px-2 py-1 rounded text-xs">
              {ledgerCount}
              {ledgerCount === 0 && (
                <div className="text-yellow-400 mt-1">⚠️ No hay registros en ledger</div>
              )}
              {ledgerCount > 0 && (
                <div className="text-gray-400 mt-1 text-xs">
                  {ledgerCount > 0 ? 'Ledger tiene datos, pero puede no matchear con claims' : ''}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Validation Info (from backend) */}
        {filtersReceived && filtersReceived._validation && (
          <div>
            <div className="text-gray-400 mb-1">Validation (Backend):</div>
            <div className="bg-gray-800 px-2 py-1 rounded text-xs">
              <div>Paid Total: {filtersReceived._validation.paid_total ?? 0}</div>
              <div>Count Paid: {filtersReceived._validation.count_paid ?? 0}</div>
              <div>Ledger Count: {filtersReceived._validation.ledger_count ?? 'N/A'}</div>
              {filtersReceived._validation.ledger_count !== undefined && filtersReceived._validation.ledger_count > 0 && filtersReceived._validation.count_paid === 0 && (
                <div className="text-yellow-400 mt-1">⚠️ Ledger tiene datos pero count_paid=0 (posible problema de matching)</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

