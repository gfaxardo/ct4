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
  summaryData,
  paidStatusDistribution,
  ledgerCount
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
        {(() => {
          const filtersSentSafe =
            (filtersSent && typeof filtersSent === "object" && Object.keys(filtersSent).length > 0)
              ? filtersSent
              : null;
          
          return filtersSentSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Filtros Enviados:</div>
              <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto">
                {JSON.stringify(filtersSentSafe, null, 2)}
              </pre>
            </div>
          ) : null;
        })()}

        {/* Filters Received */}
        {(() => {
          const filtersReceivedSafe =
            (filtersReceived && typeof filtersReceived === "object" && Object.keys(filtersReceived).length > 0)
              ? filtersReceived
              : null;
          
          return filtersReceivedSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Filtros Recibidos (Backend):</div>
              <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto">
                {JSON.stringify(filtersReceivedSafe, null, 2)}
              </pre>
            </div>
          ) : null;
        })()}

        {/* Item Counts */}
        {(() => {
          const itemCountsSafe =
            (itemCounts && typeof itemCounts === "object")
              ? itemCounts
              : null;
          
          return itemCountsSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Counts:</div>
              <div className="bg-gray-800 px-2 py-1 rounded">
                <div>Total: {itemCountsSafe.total ?? 'N/A'}</div>
                {itemCountsSafe.loaded !== undefined && <div>Loaded: {itemCountsSafe.loaded}</div>}
                {itemCountsSafe.filtered !== undefined && <div>Filtered: {itemCountsSafe.filtered}</div>}
              </div>
            </div>
          ) : null;
        })()}

        {/* Summary Data (sample) */}
        {(() => {
          const summaryDataSafe =
            (summaryData && typeof summaryData === "object")
              ? summaryData
              : null;
          
          return summaryDataSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Summary Data (Sample):</div>
              <pre className="bg-gray-800 px-2 py-1 rounded overflow-x-auto text-xs">
                {JSON.stringify(
                  {
                    expected_sum: summaryDataSafe.amount_expected_sum,
                    paid_sum: summaryDataSafe.amount_paid_sum,
                    paid_assumed: summaryDataSafe.amount_paid_assumed,
                    diff: summaryDataSafe.amount_diff,
                    diff_assumed: summaryDataSafe.amount_diff_assumed,
                    anomalies_total: summaryDataSafe.anomalies_total,
                    count_paid: summaryDataSafe.count_paid,
                    count_pending_active: summaryDataSafe.count_pending_active,
                    count_pending_expired: summaryDataSafe.count_pending_expired
                  },
                  null,
                  2
                )}
              </pre>
            </div>
          ) : (
            <div>
              <div className="text-gray-400 mb-1">Summary Data:</div>
              <div className="text-gray-400 text-xs">N/A</div>
            </div>
          );
        })()}

        {/* Paid Status Distribution */}
        {(() => {
          const paidStatusDistributionSafe =
            (paidStatusDistribution && typeof paidStatusDistribution === "object")
              ? paidStatusDistribution
              : null;
          
          return paidStatusDistributionSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Paid Status Distribution (from summary):</div>
              <div className="bg-gray-800 px-2 py-1 rounded text-xs">
                {Object.entries(paidStatusDistributionSafe).map(([key, value]) => (
                  <div key={key}>
                    {key}: {value ?? 0}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-gray-400 mb-1">Paid Status Distribution:</div>
              <div className="text-gray-400 text-xs">N/A</div>
            </div>
          );
        })()}

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
        {(() => {
          const validationSafe =
            (filtersReceived && 
             typeof filtersReceived === "object" &&
             filtersReceived._validation &&
             typeof filtersReceived._validation === "object")
              ? filtersReceived._validation
              : null;
          
          return validationSafe ? (
            <div>
              <div className="text-gray-400 mb-1">Validation (Backend):</div>
              <div className="bg-gray-800 px-2 py-1 rounded text-xs">
                <div>Paid Total: {validationSafe.paid_total ?? 'N/A'}</div>
                <div>Count Paid: {validationSafe.count_paid ?? 'N/A'}</div>
                <div>Ledger Count: {validationSafe.ledger_count ?? 'N/A'}</div>
                {validationSafe.ledger_count !== undefined && 
                 validationSafe.ledger_count > 0 && 
                 validationSafe.count_paid === 0 && (
                  <div className="text-yellow-400 mt-1">⚠️ Ledger tiene datos pero count_paid=0 (posible problema de matching)</div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="text-gray-400 mb-1">Validation (Backend):</div>
              <div className="text-gray-400 text-xs">N/A</div>
            </div>
          );
        })()}
      </div>
    </div>
  )
}

