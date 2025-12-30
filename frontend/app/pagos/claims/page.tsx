'use client'

import { useState, useEffect, useMemo } from 'react'
import { 
  getCabinetDrivers, 
  CabinetDriverRow,
  getYangoCabinetClaimsForCollection,
  getYangoCabinetClaimsForCollectionCSVUrl,
  YangoCabinetClaimsForCollectionRow
} from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'
import DriverTimelineModal from '@/components/payments/DriverTimelineModal'

type MilestoneType = 'all' | '1' | '5' | '25'
type PaymentStatusType = 'all' | 'paid' | 'partial' | 'not_paid'
type ActionPriorityType = 'all' | 'P0' | 'P1' | 'P2'
type ViewMode = 'driver' | 'cobranza'

export default function ClaimsCabinetPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('driver')
  const [loading, setLoading] = useState(true)
  const [drivers, setDrivers] = useState<CabinetDriverRow[]>([])
  const [claims, setClaims] = useState<YangoCabinetClaimsForCollectionRow[]>([])
  const [aggregates, setAggregates] = useState({
    total_rows: 0,
    total_amount: 0,
    unpaid_rows: 0,
    unpaid_amount: 0,
    misapplied_rows: 0,
    misapplied_amount: 0,
    paid_rows: 0,
    paid_amount: 0
  })
  const [error, setError] = useState<string | null>(null)
  
  // Filtros para modo Driver
  const [weekFilter, setWeekFilter] = useState<string>('')
  const [milestoneFilter, setMilestoneFilter] = useState<MilestoneType>('all')
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<PaymentStatusType>('all')
  const [actionPriorityFilter, setActionPriorityFilter] = useState<ActionPriorityType>('all')
  
  // Filtros para modo Cobranza
  const [cobranzaPaymentStatus, setCobranzaPaymentStatus] = useState<string>('UNPAID,PAID_MISAPPLIED')
  const [cobranzaOverdueBucket, setCobranzaOverdueBucket] = useState<string>('')
  const [cobranzaMilestone, setCobranzaMilestone] = useState<string>('')
  const [cobranzaDateFrom, setCobranzaDateFrom] = useState<string>('')
  const [cobranzaDateTo, setCobranzaDateTo] = useState<string>('')
  const [cobranzaSearch, setCobranzaSearch] = useState<string>('')
  
  // Modal timeline
  const [showTimeline, setShowTimeline] = useState(false)
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null)

  useEffect(() => {
    if (viewMode === 'driver') {
      loadDrivers()
    } else {
      loadClaims()
    }
  }, [
    viewMode,
    weekFilter, milestoneFilter, paymentStatusFilter, actionPriorityFilter,
    cobranzaPaymentStatus, cobranzaOverdueBucket, cobranzaMilestone, cobranzaDateFrom, cobranzaDateTo, cobranzaSearch
  ])

  async function loadDrivers() {
    // #region agent log
    fetch('http://127.0.0.1:7244/ingest/1f13ffc8-f707-43ff-9218-e0872113c413',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'claims/page.tsx:loadDrivers:entry',message:'loadDrivers called',data:{viewMode,weekFilter,milestoneFilter,paymentStatusFilter,actionPriorityFilter},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'H2'})}).catch(()=>{});
    // #endregion
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

      // #region agent log
      fetch('http://127.0.0.1:7244/ingest/1f13ffc8-f707-43ff-9218-e0872113c413',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'claims/page.tsx:loadDrivers:before_fetch',message:'About to call getCabinetDrivers',data:{params},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'H2,H3'})}).catch(()=>{});
      // #endregion
      const response = await getCabinetDrivers(params)
      // #region agent log
      fetch('http://127.0.0.1:7244/ingest/1f13ffc8-f707-43ff-9218-e0872113c413',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'claims/page.tsx:loadDrivers:after_fetch',message:'getCabinetDrivers response received',data:{responseCount:response?.rows?.length,responseStatus:response?.status},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'H2'})}).catch(()=>{});
      // #endregion
      setDrivers(response.rows)
    } catch (err: any) {
      // #region agent log
      fetch('http://127.0.0.1:7244/ingest/1f13ffc8-f707-43ff-9218-e0872113c413',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'claims/page.tsx:loadDrivers:catch',message:'Error in loadDrivers',data:{errorMessage:err?.message,errorStack:err?.stack?.substring(0,200)},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'H2,H4'})}).catch(()=>{});
      // #endregion
      console.error('Error cargando drivers cabinet:', err)
      setError(err.message || 'Error al cargar datos.')
    } finally {
      // #region agent log
      fetch('http://127.0.0.1:7244/ingest/1f13ffc8-f707-43ff-9218-e0872113c413',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'claims/page.tsx:loadDrivers:finally',message:'loadDrivers finally block',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'initial',hypothesisId:'H2'})}).catch(()=>{});
      // #endregion
      setLoading(false)
    }
  }

  async function loadClaims() {
    setLoading(true)
    setError(null)
    try {
      const params: any = {}
      
      if (cobranzaPaymentStatus) params.payment_status = cobranzaPaymentStatus
      if (cobranzaOverdueBucket) params.overdue_bucket = cobranzaOverdueBucket
      if (cobranzaMilestone) params.milestone_value = parseInt(cobranzaMilestone)
      if (cobranzaDateFrom) params.date_from = cobranzaDateFrom
      if (cobranzaDateTo) params.date_to = cobranzaDateTo
      if (cobranzaSearch) params.search = cobranzaSearch

      const response = await getYangoCabinetClaimsForCollection(params)
      setClaims(response.rows)
      setAggregates(response.aggregates)
    } catch (err: any) {
      console.error('Error cargando claims cobranza:', err)
      setError(err.message || 'Error al cargar datos.')
    } finally {
      setLoading(false)
    }
  }

  function handleExportCSV() {
    const params: any = {}
    if (cobranzaPaymentStatus) params.payment_status = cobranzaPaymentStatus
    if (cobranzaOverdueBucket) params.overdue_bucket = cobranzaOverdueBucket
    if (cobranzaMilestone) params.milestone_value = parseInt(cobranzaMilestone)
    if (cobranzaDateFrom) params.date_from = cobranzaDateFrom
    if (cobranzaDateTo) params.date_to = cobranzaDateTo
    if (cobranzaSearch) params.search = cobranzaSearch

    const url = getYangoCabinetClaimsForCollectionCSVUrl(params)
    window.open(url, '_blank')
  }

  // Calcular KPIs desde drivers (modo Driver)
  const kpisDriver = useMemo(() => {
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

  // KPIs para modo Cobranza (desde aggregates de claim-level)
  const kpisCobranza = useMemo(() => {
    return {
      expected: aggregates.total_amount,
      paid: aggregates.paid_amount,
      notPaid: aggregates.unpaid_amount,
      misapplied: aggregates.misapplied_amount,
      expectedCount: aggregates.total_rows,
      paidCount: aggregates.paid_rows,
      unpaidCount: aggregates.unpaid_rows,
      misappliedCount: aggregates.misapplied_rows,
    }
  }, [aggregates])

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

  const getPaymentStatusColorYango = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'bg-green-100 text-green-800'
      case 'PAID_MISAPPLIED':
        return 'bg-yellow-100 text-yellow-800'
      case 'UNPAID':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getOverdueBucketColor = (bucket: string) => {
    if (bucket === '0_not_due') return 'bg-gray-100 text-gray-800'
    if (bucket === '1_1_7') return 'bg-blue-100 text-blue-800'
    if (bucket === '2_8_14') return 'bg-yellow-100 text-yellow-800'
    if (bucket === '3_15_30') return 'bg-orange-100 text-orange-800'
    if (bucket === '4_30_plus') return 'bg-red-100 text-red-800'
    return 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Claims Cabinet</h1>
        
        {/* Toggle Modo */}
        <div className="flex items-center space-x-2 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('driver')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              viewMode === 'driver'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Modo Operativo (Driver)
          </button>
          <button
            onClick={() => setViewMode('cobranza')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              viewMode === 'cobranza'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Modo Cobranza Yango (Claim)
          </button>
        </div>
      </div>

      {/* Filtros - Modo Driver */}
      {viewMode === 'driver' && (
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
      )}

      {/* Filtros - Modo Cobranza */}
      {viewMode === 'cobranza' && (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-4">
          <div>
            <label htmlFor="cobranzaPaymentStatus" className="block text-sm font-medium text-gray-700 mb-1">
              Payment Status
            </label>
            <input
              type="text"
              id="cobranzaPaymentStatus"
              value={cobranzaPaymentStatus}
              onChange={(e) => setCobranzaPaymentStatus(e.target.value)}
              placeholder="UNPAID,PAID_MISAPPLIED"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Comma-separated</p>
          </div>
          <div>
            <label htmlFor="cobranzaOverdueBucket" className="block text-sm font-medium text-gray-700 mb-1">
              Overdue Bucket
            </label>
            <select
              id="cobranzaOverdueBucket"
              value={cobranzaOverdueBucket}
              onChange={(e) => setCobranzaOverdueBucket(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todos</option>
              <option value="0_not_due">0_not_due</option>
              <option value="1_1_7">1_1_7</option>
              <option value="2_8_14">2_8_14</option>
              <option value="3_15_30">3_15_30</option>
              <option value="4_30_plus">4_30_plus</option>
            </select>
          </div>
          <div>
            <label htmlFor="cobranzaMilestone" className="block text-sm font-medium text-gray-700 mb-1">
              Milestone
            </label>
            <select
              id="cobranzaMilestone"
              value={cobranzaMilestone}
              onChange={(e) => setCobranzaMilestone(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todos</option>
              <option value="1">1</option>
              <option value="5">5</option>
              <option value="25">25</option>
            </select>
          </div>
          <div>
            <label htmlFor="cobranzaDateFrom" className="block text-sm font-medium text-gray-700 mb-1">
              Date From
            </label>
            <input
              type="date"
              id="cobranzaDateFrom"
              value={cobranzaDateFrom}
              onChange={(e) => setCobranzaDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label htmlFor="cobranzaDateTo" className="block text-sm font-medium text-gray-700 mb-1">
              Date To
            </label>
            <input
              type="date"
              id="cobranzaDateTo"
              value={cobranzaDateTo}
              onChange={(e) => setCobranzaDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label htmlFor="cobranzaSearch" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <input
              type="text"
              id="cobranzaSearch"
              value={cobranzaSearch}
              onChange={(e) => setCobranzaSearch(e.target.value)}
              placeholder="driver name or ID"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
        </div>
        <div>
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
          >
            Export CSV
          </button>
        </div>
      </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando datos...</div>
      ) : drivers.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No hay datos disponibles para los filtros aplicados.</div>
      ) : (
        <>
          {/* KPIs - Modo Driver */}
          {viewMode === 'driver' && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Expected Total</h3>
              <div className="text-2xl font-bold text-blue-600">{formatCurrency(kpisDriver.expected)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisDriver.expectedCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Paid Total</h3>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(kpisDriver.paid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisDriver.paidCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Not Paid Total</h3>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(kpisDriver.notPaid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisDriver.notPaidCount} claims</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">P0 Amount</h3>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(kpisDriver.p0Amount)}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">P1 Amount</h3>
              <div className="text-2xl font-bold text-orange-600">{formatCurrency(kpisDriver.p1Amount)}</div>
            </div>
          </div>
          )}

          {/* KPIs - Modo Cobranza */}
          {viewMode === 'cobranza' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Total Amount</h3>
              <div className="text-2xl font-bold text-blue-600">{formatCurrency(kpisCobranza.expected)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisCobranza.expectedCount} rows</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Unpaid Amount</h3>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(kpisCobranza.notPaid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisCobranza.unpaidCount} rows</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Misapplied Amount</h3>
              <div className="text-2xl font-bold text-yellow-600">{formatCurrency(kpisCobranza.misapplied)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisCobranza.misappliedCount} rows</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-2">Paid Amount</h3>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(kpisCobranza.paid)}</div>
              <div className="text-sm text-gray-500 mt-1">{kpisCobranza.paidCount} rows</div>
            </div>
          </div>
          )}

          {/* Tabla de Drivers - Modo Driver */}
          {viewMode === 'driver' && (
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
          )}

          {/* Tabla de Claims - Modo Cobranza */}
          {viewMode === 'cobranza' && (
          <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
            <div className="px-6 py-4 border-b">
              <h3 className="text-lg font-semibold">Claims ({claims.length})</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Driver
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Lead Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Due Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Days Overdue
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Milestone
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Amount
                    </th>
                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Reason
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Payment Key
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {claims.map((claim, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{claim.driver_name || '-'}</div>
                        <div className="text-sm text-gray-500 font-mono text-xs">
                          {claim.driver_id || claim.person_key || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(claim.lead_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(claim.yango_due_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getOverdueBucketColor(claim.overdue_bucket_yango)}`}>
                          {claim.days_overdue_yango} ({claim.overdue_bucket_yango})
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {claim.milestone_value}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                        {formatCurrency(claim.expected_amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColorYango(claim.yango_payment_status)}`}>
                          {claim.yango_payment_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {claim.reason_code}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                        {claim.payment_key || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          )}
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
