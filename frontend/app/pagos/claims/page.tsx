'use client'

import { useState, useEffect, useMemo } from 'react'
import { getCabinetDrivers, CabinetDriverRow } from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import DriverTimelineModal from '@/components/payments/DriverTimelineModal'

type MilestoneType = 'all' | '1' | '5' | '25'
type PaymentStatusType = 'all' | 'paid' | 'partial' | 'not_paid'
type ActionPriorityType = 'all' | 'P0' | 'P1' | 'P2'

export default function ClaimsCabinetPage() {
  const [loading, setLoading] = useState(true)
  const [drivers, setDrivers] = useState<CabinetDriverRow[]>([])
  const [error, setError] = useState<string | null>(null)
  
  // Filtros
  const [weekFilter, setWeekFilter] = useState<string>('')
  const [milestoneFilter, setMilestoneFilter] = useState<MilestoneType>('all')
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<PaymentStatusType>('all')
  const [actionPriorityFilter, setActionPriorityFilter] = useState<ActionPriorityType>('all')
  
  // Modal timeline
  const [showTimeline, setShowTimeline] = useState(false)
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null)

  useEffect(() => {
    loadDrivers()
  }, [weekFilter, milestoneFilter, paymentStatusFilter, actionPriorityFilter])

  async function loadDrivers() {
    setLoading(true)
    setError(null)
    try {
      const params: {
        week_start?: string
        milestone_value?: number
        payment_status_driver?: 'paid' | 'partial' | 'not_paid'
        action_priority?: string
        limit: number
      } = {
        limit: 1000,
      }
      
      if (weekFilter) params.week_start = weekFilter
      if (milestoneFilter !== 'all') params.milestone_value = parseInt(milestoneFilter)
      if (paymentStatusFilter !== 'all') params.payment_status_driver = paymentStatusFilter
      if (actionPriorityFilter !== 'all') params.action_priority = actionPriorityFilter

      const response = await getCabinetDrivers(params)
      setDrivers(response.rows)
    } catch (err: any) {
      console.error('Error cargando drivers cabinet:', err)
      setError(err.message || 'Error al cargar datos.')
    } finally {
      setLoading(false)
    }
  }

  // Calcular KPIs desde drivers
  const kpis = useMemo(() => {
    const totals = drivers.reduce(
      (acc, driver) => ({
        expected: acc.expected + driver.expected_total,
        paid: acc.paid + driver.paid_total,
        notPaid: acc.notPaid + driver.not_paid_total,
        p0Amount: acc.p0Amount + (driver.action_priority_driver === 'P0' ? driver.not_paid_total : 0),
        p1Amount: acc.p1Amount + (driver.action_priority_driver === 'P1' ? driver.not_paid_total : 0),
        expectedCount: acc.expectedCount + driver.counts.claims_total,
        paidCount: acc.paidCount + driver.counts.claims_paid,
        notPaidCount: acc.notPaidCount + driver.counts.claims_not_paid,
      }),
      {
        expected: 0,
        paid: 0,
        notPaid: 0,
        p0Amount: 0,
        p1Amount: 0,
        expectedCount: 0,
        paidCount: 0,
        notPaidCount: 0,
      }
    )
    return totals
  }, [drivers])

  const handleViewTimeline = (driverId: string) => {
    setSelectedDriverId(driverId)
    setShowTimeline(true)
  }

  const getPaymentStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-green-100 text-green-800'
      case 'partial':
        return 'bg-yellow-100 text-yellow-800'
      case 'not_paid':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getActionPriorityColor = (priority: string) => {
    switch (priority) {
      case 'P0':
        return 'bg-red-100 text-red-800'
      case 'P1':
        return 'bg-orange-100 text-orange-800'
      case 'P2':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
              <option value="partial">Partial</option>
              <option value="not_paid">Not Paid</option>
            </select>
          </div>
          <div>
            <label htmlFor="actionPriorityFilter" className="block text-sm font-medium text-gray-700">
              Action Priority
            </label>
            <select
              id="actionPriorityFilter"
              value={actionPriorityFilter}
              onChange={(e) => setActionPriorityFilter(e.target.value as ActionPriorityType)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
            >
              <option value="all">Todos</option>
              <option value="P0">P0 - Collect Now</option>
              <option value="P1">P1 - Watch</option>
              <option value="P2">P2 - Not Due</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando datos...</div>
      ) : drivers.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No hay datos disponibles para los filtros aplicados.</div>
      ) : (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Expected Total</h3>
              <div className="text-2xl font-bold text-blue-600">{formatCurrency(kpis.expected)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpis.expectedCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Paid Total</h3>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(kpis.paid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpis.paidCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Not Paid Total</h3>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(kpis.notPaid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpis.notPaidCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">P0 Amount</h3>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(kpis.p0Amount)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">P1 Amount</h3>
              <div className="text-2xl font-bold text-orange-600">{formatCurrency(kpis.p1Amount)}</div>
            </div>
          </div>

          {/* Tabla de Drivers */}
          <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">Drivers</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Driver
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Período
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
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Milestones
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Priority
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {drivers.map((driver, index) => (
                    <tr key={driver.driver_id || driver.person_key || index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{driver.driver_name_display}</div>
                        <div className="text-sm text-gray-500 font-mono text-xs">
                          {driver.driver_id || driver.person_key}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>{formatDate(driver.lead_date_min)}</div>
                        <div className="text-xs">a {formatDate(driver.lead_date_max)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">
                        {formatCurrency(driver.expected_total)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                        {formatCurrency(driver.paid_total)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">
                        {formatCurrency(driver.not_paid_total)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className="flex gap-1 justify-center">
                          <span className={`px-2 py-1 rounded text-xs ${driver.milestones_reached.m1 ? (driver.milestones_paid.paid_m1 ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700') : 'bg-gray-100 text-gray-400'}`}>
                            M1
                          </span>
                          <span className={`px-2 py-1 rounded text-xs ${driver.milestones_reached.m5 ? (driver.milestones_paid.paid_m5 ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700') : 'bg-gray-100 text-gray-400'}`}>
                            M5
                          </span>
                          <span className={`px-2 py-1 rounded text-xs ${driver.milestones_reached.m25 ? (driver.milestones_paid.paid_m25 ? 'bg-green-100 text-green-800' : 'bg-gray-200 text-gray-700') : 'bg-gray-100 text-gray-400'}`}>
                            M25
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColor(driver.payment_status_driver)}`}>
                          {driver.payment_status_driver}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionPriorityColor(driver.action_priority_driver)}`}>
                          {driver.action_priority_driver}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => driver.driver_id && handleViewTimeline(driver.driver_id)}
                          className="text-blue-600 hover:text-blue-900"
                          disabled={!driver.driver_id}
                        >
                          Ver Timeline
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

      {showTimeline && selectedDriverId && (
        <DriverTimelineModal
          driverId={selectedDriverId}
          onClose={() => {
            setShowTimeline(false)
            setSelectedDriverId(null)
          }}
        />
      )}
    </div>
  )
}
