'use client'

import { useEffect, useState } from 'react'
import { listUnmatched, IdentityUnmatched, listIngestionRuns, IngestionRun } from '@/lib/api'
import { formatDate } from '@/lib/utils'

export default function UnmatchedPage() {
  const [unmatched, setUnmatched] = useState<IdentityUnmatched[]>([])
  const [loading, setLoading] = useState(true)
  const [reasonFilter, setReasonFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [sourceTableFilter, setSourceTableFilter] = useState<string>('')
  const [runIdFilter, setRunIdFilter] = useState<string>('')
  const [runs, setRuns] = useState<IngestionRun[]>([])
  const [reasonCounts, setReasonCounts] = useState<Record<string, number>>({})

  useEffect(() => {
    loadRuns()
  }, [])

  useEffect(() => {
    loadUnmatched()
  }, [reasonFilter, statusFilter, sourceTableFilter, runIdFilter])

  async function loadRuns() {
    try {
      const data = await listIngestionRuns({ limit: 20 })
      setRuns(data)
    } catch (error) {
      console.error('Error cargando runs:', error)
    }
  }

  async function loadUnmatched() {
    setLoading(true)
    try {
      const params: any = { limit: 100 }
      if (reasonFilter) params.reason_code = reasonFilter
      if (statusFilter) params.status = statusFilter
      const data = await listUnmatched(params)
      
      let filtered = data
      if (sourceTableFilter) {
        filtered = filtered.filter(item => item.source_table === sourceTableFilter)
      }
      if (runIdFilter) {
        filtered = filtered.filter(item => item.run_id?.toString() === runIdFilter)
      }
      
      setUnmatched(filtered)
      
      const counts: Record<string, number> = {}
      filtered.forEach(item => {
        counts[item.reason_code] = (counts[item.reason_code] || 0) + 1
      })
      setReasonCounts(counts)
    } catch (error) {
      console.error('Error cargando unmatched:', error)
    } finally {
      setLoading(false)
    }
  }

  const sourceTables = Array.from(new Set(unmatched.map(item => item.source_table)))

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Registros Sin Resolver</h1>

      {Object.keys(reasonCounts).length > 0 && (
        <div className="bg-white rounded-lg shadow mb-6 p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Contadores por Razón</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(reasonCounts).map(([reason, count]) => (
              <span
                key={reason}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
              >
                {reason}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow mb-6 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <select
            value={reasonFilter}
            onChange={(e) => setReasonFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="">Todos los códigos</option>
            <option value="MISSING_KEYS">MISSING_KEYS</option>
            <option value="NO_CANDIDATES">NO_CANDIDATES</option>
            <option value="MULTIPLE_CANDIDATES">MULTIPLE_CANDIDATES</option>
            <option value="WEAK_MATCH_ONLY">WEAK_MATCH_ONLY</option>
            <option value="INVALID_DATE_FORMAT">INVALID_DATE_FORMAT</option>
            <option value="ERROR">ERROR</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="">Todos los estados</option>
            <option value="OPEN">Abierto</option>
            <option value="RESOLVED">Resuelto</option>
            <option value="IGNORED">Ignorado</option>
          </select>
          <select
            value={sourceTableFilter}
            onChange={(e) => setSourceTableFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="">Todas las fuentes</option>
            {sourceTables.map(table => (
              <option key={table} value={table}>{table}</option>
            ))}
          </select>
          <select
            value={runIdFilter}
            onChange={(e) => setRunIdFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="">Todos los runs</option>
            {runs.map(run => (
              <option key={run.id} value={run.id.toString()}>Run #{run.id}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">Cargando...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fuente</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">PK</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha Snapshot</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Detalles</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {unmatched.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.source_table}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{item.source_pk}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{item.reason_code}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      item.status === 'OPEN' ? 'bg-red-100 text-red-800' :
                      item.status === 'RESOLVED' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {item.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(item.snapshot_date)}</td>
                  <td className="px-6 py-4 text-sm">
                    <div className="space-y-2">
                      <div>
                        <span className="font-medium text-red-600">{item.reason_code}</span>
                        {item.run_id && (
                          <span className="ml-2 text-xs text-gray-500">(Run #{item.run_id})</span>
                        )}
                      </div>
                      {item.details && (
                        <details>
                          <summary className="cursor-pointer text-blue-600 hover:text-blue-800 text-xs">Detalles</summary>
                          <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                            {JSON.stringify(item.details, null, 2)}
                          </pre>
                        </details>
                      )}
                      {item.candidates_preview && (
                        <details>
                          <summary className="cursor-pointer text-green-600 hover:text-green-800 text-xs">Candidatos ({item.candidates_preview.candidates?.length || 0})</summary>
                          <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                            {JSON.stringify(item.candidates_preview, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {unmatched.length === 0 && (
            <div className="text-center py-12 text-gray-500">No se encontraron registros sin resolver</div>
          )}
        </div>
      )}
    </div>
  )
}



