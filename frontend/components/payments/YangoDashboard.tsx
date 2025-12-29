'use client'

import { useEffect, useState, useMemo } from 'react'
import { getYangoReconciliationSummary, YangoReconciliationSummaryRow, YangoReconciliationSummaryResponse, getYangoLedgerUnmatched, YangoLedgerUnmatchedRow, getYangoLedgerMatched } from '@/lib/api'
import DebugPanel from './DebugPanel'

interface YangoDashboardProps {
  onWeekClick: (weekStart: string) => void
  weekFilter?: string
  onWeekFilterChange: (week: string) => void
  onReasonClick?: (reasonCode: string) => void
}

type WeeklyDataItem = {
  week_start: string
  amount_expected_sum: number
  amount_paid_confirmed_sum: number
  amount_paid_enriched_sum: number
  amount_paid_sum: number
  amount_diff: number
  count_expected: number
  count_paid: number
  count_pending_active: number
  count_pending_expired: number
  rows_count: number
  anomalies_total: number
}

// Función auxiliar para calcular datos semanales
function calculateWeeklyData(summary: YangoReconciliationSummaryRow[]): {
  weeklyRows: WeeklyDataItem[]
  totalsFromSummary: {
    total_expected: number
    total_paid_confirmed: number
    total_paid_enriched: number
    total_paid: number
    total_anomalies: number
    total_diff: number
    total_paid_visible: number
  }
} {
  if (!summary || summary.length === 0) {
    return {
      weeklyRows: [],
      totalsFromSummary: {
        total_expected: 0,
        total_paid_confirmed: 0,
        total_paid_enriched: 0,
        total_paid: 0,
        total_anomalies: 0,
        total_diff: 0,
        total_paid_visible: 0
      }
    };
  }
  
  // El summary ya viene agregado por semana y milestone
  // Necesitamos reagrupar solo por semana
  const weeklyData: Record<string, WeeklyDataItem> = summary.reduce((acc, row) => {
    const week: string = row.pay_week_start_monday ? String(row.pay_week_start_monday) : 'unknown'
    if (!acc[week]) {
      acc[week] = {
        week_start: week,
        amount_expected_sum: 0,
        amount_paid_confirmed_sum: 0,
        amount_paid_enriched_sum: 0,
        amount_paid_sum: 0,
        amount_diff: 0,
        count_expected: 0,
        count_paid: 0,
        count_pending_active: 0,
        count_pending_expired: 0,
        rows_count: 0,
        anomalies_total: 0
      }
    }
    
    const expectedSum = row.amount_expected_sum ?? row.sum_amount_expected ?? 0
    const paidConfirmedSum = row.amount_paid_confirmed_sum ?? 0
    const paidEnrichedSum = row.amount_paid_enriched_sum ?? 0
    const paidTotalVisible = row.amount_paid_total_visible ?? row.amount_paid_sum ?? (paidConfirmedSum + paidEnrichedSum)
    
    acc[week].amount_expected_sum += expectedSum
    acc[week].amount_paid_confirmed_sum = (acc[week].amount_paid_confirmed_sum || 0) + paidConfirmedSum
    acc[week].amount_paid_enriched_sum = (acc[week].amount_paid_enriched_sum || 0) + paidEnrichedSum
    acc[week].amount_paid_sum = (acc[week].amount_paid_sum || 0) + paidTotalVisible
    
    acc[week].count_expected += row.count_expected ?? row.count_items ?? 0
    acc[week].count_paid += row.count_paid ?? 0
    acc[week].count_pending_active += row.count_pending_active ?? 0
    acc[week].count_pending_expired += row.count_pending_expired ?? 0
    acc[week].rows_count += row.rows_count ?? row.count_items ?? 0
    acc[week].anomalies_total += row.anomalies_total ?? row.count_pending_expired ?? 0
    
    return acc
  }, {} as Record<string, WeeklyDataItem>);

  // Calcular diff para cada semana y convertir a array
  const weeklyRows: WeeklyDataItem[] = Object.values(weeklyData)
    .map((item) => ({
      ...item,
      amount_diff: item.amount_expected_sum - item.amount_paid_sum
    }))
    .sort((a: WeeklyDataItem, b: WeeklyDataItem) => 
      b.week_start.localeCompare(a.week_start)
    );

  // Calcular KPIs totales desde summary
  const totals = weeklyRows.reduce((acc, row) => {
    acc.total_expected += row.amount_expected_sum
    acc.total_paid_confirmed += row.amount_paid_confirmed_sum
    acc.total_paid_enriched += row.amount_paid_enriched_sum
    acc.total_paid += row.amount_paid_sum
    acc.total_anomalies += row.anomalies_total
    return acc
  }, {
    total_expected: 0,
    total_paid_confirmed: 0,
    total_paid_enriched: 0,
    total_paid: 0,
    total_anomalies: 0
  })
  totals.total_diff = totals.total_expected - totals.total_paid
  totals.total_paid_visible = totals.total_paid_confirmed + totals.total_paid_enriched

  return { weeklyRows, totalsFromSummary: totals };
}

export default function YangoDashboard({
  onWeekClick,
  weekFilter,
  onWeekFilterChange,
  onReasonClick
}: YangoDashboardProps) {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<YangoReconciliationSummaryRow[]>([])
  const [response, setResponse] = useState<YangoReconciliationSummaryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'real' | 'assumed'>('real')
  const [milestoneFilter, setMilestoneFilter] = useState<string>('')
  const [sinConductor, setSinConductor] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [showUnmatchedModal, setShowUnmatchedModal] = useState(false)
  const [showMatchedModal, setShowMatchedModal] = useState(false)
  const [unmatchedLedger, setUnmatchedLedger] = useState<YangoLedgerUnmatchedRow[]>([])
  const [matchedLedger, setMatchedLedger] = useState<YangoLedgerUnmatchedRow[]>([])
  const [unmatchedLoading, setUnmatchedLoading] = useState(false)
  const [matchedLoading, setMatchedLoading] = useState(false)
  const [unmatchedTotal, setUnmatchedTotal] = useState(0)
  const [matchedTotal, setMatchedTotal] = useState(0)

  useEffect(() => {
    loadSummary()
  }, [weekFilter, mode, milestoneFilter])

  async function loadUnmatchedLedger() {
    setUnmatchedLoading(true)
    try {
      const response = await getYangoLedgerUnmatched({
        is_paid: true,  // Solo pagos pagados
        limit: 1000
      })
      setUnmatchedLedger(response.rows)
      setUnmatchedTotal(response.total)
    } catch (err) {
      console.error('Error cargando ledger sin match:', err)
    } finally {
      setUnmatchedLoading(false)
    }
  }

  async function loadMatchedLedger() {
    setMatchedLoading(true)
    try {
      const response = await getYangoLedgerMatched({
        limit: 1000
      })
      setMatchedLedger(response.rows)
      setMatchedTotal(response.total)
    } catch (err) {
      console.error('Error cargando ledger con match:', err)
    } finally {
      setMatchedLoading(false)
    }
  }

  async function loadSummary() {
    setLoading(true)
    setError(null)
    try {
      const params: {
        week_start?: string
        milestone_value?: number
        mode: 'real' | 'assumed'
        limit: number
      } = {
        mode,
        limit: 1000
      }
      
      if (weekFilter && weekFilter !== '') {
        params.week_start = weekFilter
      }
      
      if (milestoneFilter && milestoneFilter !== '' && ['1', '5', '25'].includes(milestoneFilter)) {
        params.milestone_value = parseInt(milestoneFilter)
      }

      const apiResponse = await getYangoReconciliationSummary(params)
      setResponse(apiResponse)
      setSummary(apiResponse.rows)
    } catch (err) {
      console.error('Error cargando resumen Yango:', err)
      setError('Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(amount)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  // Agregar por semana (pay_week_start_monday) y calcular KPIs
  const weeklyDataResult = useMemo(() => calculateWeeklyData(summary), [summary]);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <p className="mt-2 text-gray-600">Cargando datos...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={loadSummary}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-6">
      {/* Toggle Modo */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Modo:</label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode('real')}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  mode === 'real'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Pagos Reales
              </button>
              <button
                onClick={() => setMode('assumed')}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  mode === 'assumed'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Pagos Estimados
              </button>
            </div>
            {mode === 'assumed' && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                Estimado
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Filtros Adicionales */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Milestone</label>
            <select
              value={milestoneFilter}
              onChange={(e) => setMilestoneFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todos</option>
              <option value="1">1</option>
              <option value="5">5</option>
              <option value="25">25</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Búsqueda (Driver ID / Person Key)</label>
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Buscar por ID..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={sinConductor}
                onChange={(e) => setSinConductor(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">Solo SIN CONDUCTOR</span>
            </label>
          </div>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Nota: Los filtros de búsqueda y "Solo SIN CONDUCTOR" se aplican en el drilldown de items.
        </div>
      </div>

      {/* KPIs Totales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Expected</h3>
          <div className="text-2xl font-bold text-blue-600">{formatCurrency(weeklyDataResult.totalsFromSummary.total_expected)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-gray-600">Paid Confirmado</h3>
            <div className="group relative">
              <svg className="w-4 h-4 text-gray-400 cursor-help" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-64 z-10">
                Pagos con identidad confirmada desde upstream (driver_id/person_key original). Fuente de verdad para pagos reales contables.
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                  <div className="border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(weeklyDataResult.totalsFromSummary.total_paid_confirmed)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-gray-600">Paid Enriquecido</h3>
            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
              Probable
            </span>
            <div className="group relative">
              <svg className="w-4 h-4 text-gray-400 cursor-help" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-64 z-10">
                Pagos con identidad enriquecida por matching determinístico por nombre (match único). Informativo pero requiere confirmación para contabilidad definitiva.
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                  <div className="border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-yellow-600">{formatCurrency(weeklyDataResult.totalsFromSummary.total_paid_enriched)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-gray-600">Paid Sin Identidad</h3>
            <div className="group relative">
              <svg className="w-4 h-4 text-gray-400 cursor-help" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-64 z-10">
                Pagos pagados en ledger pero sin identidad atribuible (ambiguous/no_match). No contable hasta resolver identidad.
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                  <div className="border-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </div>
          </div>
          <div className="text-2xl font-bold text-purple-600">
            {formatCurrency(
              (response?.filters?._validation?.ledger_rows_is_paid_true ?? 0) - 
              (response?.filters?._validation?.ledger_is_paid_true_confirmed ?? 0) - 
              (response?.filters?._validation?.ledger_is_paid_true_enriched ?? 0)
            )}
          </div>
        </div>
      </div>
      
      {/* Segunda fila: Diff y Anomalías */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-sm font-medium text-gray-600">Total Diff</h3>
            {mode === 'assumed' && (
              <>
                <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs font-medium">
                  Estimado
                </span>
                <div className="group relative">
                  <svg className="w-4 h-4 text-gray-400 cursor-help" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-64 z-10">
                    Proyección basada en pagos pendientes activos dentro de ventana.
                    <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                      <div className="border-4 border-transparent border-t-gray-900"></div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
          <div className={`text-2xl font-bold ${weeklyDataResult.totalsFromSummary.total_diff >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatCurrency(Math.abs(weeklyDataResult.totalsFromSummary.total_diff))}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Anomalías</h3>
          <div className="text-2xl font-bold text-orange-600">{weeklyDataResult.totalsFromSummary.total_anomalies}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Identidad del Ledger</h3>
          <div className="space-y-2">
            <div>
              <div className="text-xs text-gray-500">Pagos pagados</div>
              <div className="text-xl font-bold text-blue-600">
                {response?.filters?._validation?.ledger_rows_is_paid_true ?? 0}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Original</div>
              <div className="text-lg font-bold text-gray-700">
                {response?.filters?._validation?.identity_original_rows ?? 0}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Enriquecidos</div>
              <div className="text-lg font-bold text-green-600">
                {response?.filters?._validation?.identity_enriched_rows ?? 0}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Sin identidad</div>
              <div className="text-lg font-bold text-purple-600">
                {response?.filters?._validation?.both_identity_null_rows ?? 0}
              </div>
            </div>
            {response?.filters?._validation?.distribution_confidence && (
              <div className="pt-2 border-t border-gray-200">
                <div className="text-xs text-gray-500 mb-1">Confianza</div>
                <div className="flex gap-2 text-xs">
                  <span className="text-green-700">High: {response.filters._validation.distribution_confidence.high ?? 0}</span>
                  <span className="text-yellow-700">Med: {response.filters._validation.distribution_confidence.medium ?? 0}</span>
                  <span className="text-gray-500">Unknown: {response.filters._validation.distribution_confidence.unknown ?? 0}</span>
                </div>
              </div>
            )}
          </div>
          <div className="mt-3 flex gap-2 flex-wrap">
            <button
              onClick={() => {
                setShowUnmatchedModal(true)
                loadUnmatchedLedger()
              }}
              className="px-3 py-1 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-xs"
            >
              Sin match
            </button>
            <button
              onClick={() => {
                setShowMatchedModal(true)
                loadMatchedLedger()
              }}
              className="px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 text-xs"
            >
              Con match
            </button>
          </div>
        </div>
      </div>

      {/* Banner Warning cuando Paid=0 pero hay ledger_paid */}
      {weeklyDataResult.totalsFromSummary.total_paid === 0 && 
       response?.filters?._validation?.ledger_rows_is_paid_true > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <p className="text-sm font-medium text-yellow-800">
                Hay pagos marcados como pagados en ledger pero sin identidad (driver/person). Paid conciliado = 0.
              </p>
              <div className="mt-2 text-sm text-yellow-700">
                <ul className="list-disc list-inside space-y-1">
                  <li>Total pagos pagados en ledger: <strong>{response?.filters?._validation?.ledger_rows_is_paid_true ?? 0}</strong></li>
                  <li>Pagos sin identidad: <strong>{response?.filters?._validation?.both_identity_null_rows ?? 0}</strong></li>
                  <li>Pagos con identidad original: <strong>{response?.filters?._validation?.identity_original_rows ?? 0}</strong></li>
                  <li>Pagos con identidad enriquecida: <strong>{response?.filters?._validation?.identity_enriched_rows ?? 0}</strong></li>
                  <li>Pagos conciliados (paid_status='paid'): <strong>{response?.filters?._validation?.matched_paid_rows ?? 0}</strong></li>
                  {response?.filters?._validation?.distribution_confidence && (
                    <li>Confianza: High={response.filters._validation.distribution_confidence.high ?? 0}, 
                        Med={response.filters._validation.distribution_confidence.medium ?? 0}, 
                        Unknown={response.filters._validation.distribution_confidence.unknown ?? 0}</li>
                  )}
                </ul>
              </div>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => {
                    setShowUnmatchedModal(true)
                    loadUnmatchedLedger()
                  }}
                  className="text-sm font-medium text-yellow-800 underline hover:text-yellow-900"
                >
                  Ver ledger sin identidad →
                </button>
                <span className="text-yellow-600">|</span>
                <button
                  onClick={() => {
                    setShowMatchedModal(true)
                    loadMatchedLedger()
                  }}
                  className="text-sm font-medium text-yellow-800 underline hover:text-yellow-900"
                >
                  Ver ledger con match →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabla Semanal */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold">Dashboard Semanal</h3>
        </div>
        {weeklyDataResult.weeklyRows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semana</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Expected</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Paid</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Diff</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Count Expected</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Count Paid</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pending Active</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Pending Expired</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Anomalías</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Anomaly %</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acción</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {weeklyDataResult.weeklyRows.map((row) => (
                  <tr
                    key={row.week_start}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => onWeekClick(row.week_start)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {formatDate(row.week_start)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {formatCurrency(row.amount_expected_sum)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                      {formatCurrency(row.amount_paid_sum)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                      row.amount_diff >= 0 ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {formatCurrency(Math.abs(row.amount_diff))}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_expected}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_paid}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_pending_active}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.count_pending_expired}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        row.anomalies_total > 0 ? 'bg-orange-100 text-orange-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {row.anomalies_total}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                      {row.rows_count > 0 ? (
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          (row.anomalies_total / row.rows_count) < 0.05 ? 'bg-green-100 text-green-800' :
                          (row.anomalies_total / row.rows_count) < 0.15 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {((row.anomalies_total / row.rows_count) * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onWeekClick(row.week_start)
                        }}
                        className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-xs"
                      >
                        Ver Detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">
            No hay datos disponibles
          </div>
        )}
      </div>

      {/* Modal: Ledger sin match */}
      {showUnmatchedModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">Ledger sin Match contra Claims</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Total: {unmatchedTotal} registros pagados en ledger que no matchean con claims
                </p>
              </div>
              <button
                onClick={() => setShowUnmatchedModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                ✕ Cerrar
              </button>
            </div>

            {/* Tabla */}
            <div className="flex-1 overflow-auto p-6">
              {unmatchedLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-2 text-gray-600">Cargando datos...</p>
                </div>
              ) : unmatchedLedger.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Key</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pay Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Identity Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rule</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Confidence</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Is Paid</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {unmatchedLedger.map((row, idx) => {
                        const identityStatus = row.identity_status || (row.identity_enriched ? 'enriched' : (row.driver_id || row.person_key ? 'confirmed' : 'no_match'))
                        const matchRule = row.match_rule || '-'
                        const matchConfidence = row.match_confidence || '-'
                        return (
                        <tr key={row.payment_key || idx} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                            {row.payment_key || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {formatDate(row.pay_date || '')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {row.milestone_value || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                            {row.driver_id || (
                              <span className="text-red-600 font-semibold">NULL</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                            {row.person_key || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {row.raw_driver_name || row.driver_name_normalized || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              identityStatus === 'confirmed' ? 'bg-green-100 text-green-800' :
                              identityStatus === 'enriched' ? 'bg-yellow-100 text-yellow-800' :
                              identityStatus === 'ambiguous' ? 'bg-orange-100 text-orange-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {identityStatus}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {matchRule}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              matchConfidence === 'high' ? 'bg-green-100 text-green-800' :
                              matchConfidence === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {matchConfidence}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                            {row.is_paid ? (
                              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">Sí</span>
                            ) : (
                              <span className="text-gray-400">No</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="px-6 py-12 text-center text-gray-500">
                  No hay registros de ledger sin match
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Ledger con match */}
      {showMatchedModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold">Ledger con Match contra Claims</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Total: {matchedTotal} registros pagados en ledger que sí matchean con claims
                </p>
              </div>
              <button
                onClick={() => setShowMatchedModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                ✕ Cerrar
              </button>
            </div>

            {/* Tabla */}
            <div className="flex-1 overflow-auto p-6">
              {matchedLoading ? (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="mt-2 text-gray-600">Cargando datos...</p>
                </div>
              ) : matchedLedger.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Payment Key</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pay Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Milestone</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Identity Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rule</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Confidence</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Is Paid</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {matchedLedger.map((row, idx) => {
                        const identityStatus = row.identity_status || (row.identity_enriched ? 'enriched' : (row.driver_id || row.person_key ? 'confirmed' : 'no_match'))
                        const matchRule = row.match_rule || '-'
                        const matchConfidence = row.match_confidence || '-'
                        return (
                        <tr key={row.payment_key || idx} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                            {row.payment_key || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {formatDate(row.pay_date || '')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {row.milestone_value || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                            {row.driver_id || (
                              <span className="text-red-600 font-semibold">NULL</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-xs">
                            {row.person_key || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {row.raw_driver_name || row.driver_name_normalized || '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              identityStatus === 'confirmed' ? 'bg-green-100 text-green-800' :
                              identityStatus === 'enriched' ? 'bg-yellow-100 text-yellow-800' :
                              identityStatus === 'ambiguous' ? 'bg-orange-100 text-orange-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {identityStatus}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {matchRule}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              matchConfidence === 'high' ? 'bg-green-100 text-green-800' :
                              matchConfidence === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {matchConfidence}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                            {row.is_paid ? (
                              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">Sí</span>
                            ) : (
                              <span className="text-gray-400">No</span>
                            )}
                          </td>
                        </tr>
                      )})}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="px-6 py-12 text-center text-gray-500">
                  No hay registros de ledger con match
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Debug Panel */}
      <DebugPanel
        filtersSent={{
          week_start: weekFilter || undefined,
          milestone_value: milestoneFilter ? parseInt(milestoneFilter) : undefined,
          mode,
          limit: 1000
        }}
        filtersReceived={response?.filters}
        mode={mode}
        summaryData={weeklyDataResult.weeklyRows[0]}
        paidStatusDistribution={{
          paid: summary.reduce((acc, row) => acc + (row.count_paid ?? 0), 0),
          pending_active: summary.reduce((acc, row) => acc + (row.count_pending_active ?? 0), 0),
          pending_expired: weeklyDataResult.totalsFromSummary.total_anomalies
        }}
        ledgerCount={response?.filters?._validation?.ledger_total_rows}
      />
    </>
  )
}
