'use client'

import { useState, useEffect, useMemo } from 'react'
import { getClaimsCabinetSummary, ClaimsCabinetSummaryRow } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import ClaimsKPIs from '@/components/payments/ClaimsKPIs'
import ClaimsDrilldown from '@/components/payments/ClaimsDrilldown'

type MilestoneType = 'all' | '1' | '5' | '25'
type PaymentStatusType = 'all' | 'paid' | 'not_paid'

export default function ClaimsCabinetPage() {
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<ClaimsCabinetSummaryRow[]>([])
  const [error, setError] = useState<string | null>(null)
  
  // Filtros
  const [weekFilter, setWeekFilter] = useState<string>('')
  const [milestoneFilter, setMilestoneFilter] = useState<MilestoneType>('all')
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<PaymentStatusType>('all')
  
  // Drilldown
  const [showDrilldown, setShowDrilldown] = useState(false)
  const [selectedWeek, setSelectedWeek] = useState<string>('')
  const [selectedMilestone, setSelectedMilestone] = useState<number | null>(null)

  useEffect(() => {
    loadSummary()
  }, [weekFilter, milestoneFilter, paymentStatusFilter])

  async function loadSummary() {
    setLoading(true)
    setError(null)
    try {
      const params: {
        week_start?: string
        milestone_value?: number
        payment_status?: 'paid' | 'not_paid'
        limit: number
      } = {
        limit: 1000,
      }
      
      if (weekFilter) params.week_start = weekFilter
      if (milestoneFilter !== 'all') params.milestone_value = parseInt(milestoneFilter)
      if (paymentStatusFilter !== 'all') params.payment_status = paymentStatusFilter

      const response = await getClaimsCabinetSummary(params)
      setSummary(response.rows)
    } catch (err: any) {
      console.error('Error cargando resumen claims cabinet:', err)
      setError(err.message || 'Error al cargar datos del resumen.')
    } finally {
      setLoading(false)
    }
  }

  // Calcular KPIs desde summary
  const kpis = useMemo(() => {
    const totals = summary.reduce(
      (acc, row) => ({
        expected: acc.expected + row.expected_amount_sum,
        paid: acc.paid + row.paid_amount_sum,
        notPaid: acc.notPaid + row.not_paid_amount_sum,
        expectedCount: acc.expectedCount + row.expected_count,
        paidCount: acc.paidCount + row.paid_count,
        notPaidCount: acc.notPaidCount + row.not_paid_count,
      }),
      {
        expected: 0,
        paid: 0,
        notPaid: 0,
        expectedCount: 0,
        paidCount: 0,
        notPaidCount: 0,
      }
    )
    return totals
  }, [summary])

  const handleViewDetail = (weekStart: string, milestone: number) => {
    setSelectedWeek(weekStart)
    setSelectedMilestone(milestone)
    setShowDrilldown(true)
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6 text-red-600">
        <h1 className="text-3xl font-bold mb-6">Claims Cabinet</h1>
        <p>Error: {error}</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Claims Cabinet</h1>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="weekFilter" className="block text-sm font-medium text-gray-700">
              Semana (Lunes)
            </label>
            <input
              type="date"
              id="weekFilter"
              value={weekFilter}
              onChange={(e) => setWeekFilter(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
            />
          </div>
          <div>
            <label htmlFor="milestoneFilter" className="block text-sm font-medium text-gray-700">
              Milestone
            </label>
            <select
              id="milestoneFilter"
              value={milestoneFilter}
              onChange={(e) => setMilestoneFilter(e.target.value as MilestoneType)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
            >
              <option value="all">Todos</option>
              <option value="1">1</option>
              <option value="5">5</option>
              <option value="25">25</option>
            </select>
          </div>
          <div>
            <label htmlFor="paymentStatusFilter" className="block text-sm font-medium text-gray-700">
              Payment Status
            </label>
            <select
              id="paymentStatusFilter"
              value={paymentStatusFilter}
              onChange={(e) => setPaymentStatusFilter(e.target.value as PaymentStatusType)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
            >
              <option value="all">Todos</option>
              <option value="paid">Paid</option>
              <option value="not_paid">Not Paid</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando datos...</div>
      ) : summary.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No hay datos disponibles para los filtros aplicados.</div>
      ) : (
        <>
          {/* KPIs */}
          <ClaimsKPIs kpis={kpis} />

          {/* Tabla Agregada */}
          <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">Resumen por Semana y Milestone</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Semana
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Milestone
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Expected
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Paid
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Not Paid
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Count Expected
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Count Paid
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Count Not Paid
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {summary.map((row, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatDate(row.pay_week_start_monday)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {row.milestone_value}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                        {formatCurrency(row.expected_amount_sum)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                        {formatCurrency(row.paid_amount_sum)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">
                        {formatCurrency(row.not_paid_amount_sum)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                        {row.expected_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                        {row.paid_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">
                        {row.not_paid_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleViewDetail(row.pay_week_start_monday, row.milestone_value)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Ver Detalle
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {showDrilldown && selectedWeek && selectedMilestone !== null && (
        <ClaimsDrilldown
          weekStart={selectedWeek}
          milestone={selectedMilestone}
          onClose={() => {
            setShowDrilldown(false)
            setSelectedWeek('')
            setSelectedMilestone(null)
          }}
        />
      )}
    </div>
  )
}

