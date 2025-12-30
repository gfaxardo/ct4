'use client'

import { useState, useEffect } from 'react'
import {
  getYangoCabinetClaimsForCollection,
  getYangoCabinetClaimsForCollectionCSVUrl,
  YangoCabinetClaimsForCollectionRow
} from '@/lib/api'
import { formatCurrency, formatDate } from '@/lib/utils'

type PaymentStatusType = 'UNPAID' | 'PAID_MISAPPLIED' | 'PAID'

export default function YangoCabinetPage() {
  const [loading, setLoading] = useState(true)
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

  // Filtros
  const [paymentStatus, setPaymentStatus] = useState<string>('UNPAID,PAID_MISAPPLIED') // Default
  const [overdueBucket, setOverdueBucket] = useState<string>('')
  const [milestone, setMilestone] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [search, setSearch] = useState<string>('')

  useEffect(() => {
    loadClaims()
  }, [paymentStatus, overdueBucket, milestone, dateFrom, dateTo, search])

  async function loadClaims() {
    setLoading(true)
    setError(null)
    try {
      const params: any = {}
      
      if (paymentStatus) params.payment_status = paymentStatus
      if (overdueBucket) params.overdue_bucket = overdueBucket
      if (milestone) params.milestone_value = parseInt(milestone)
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (search) params.search = search

      const response = await getYangoCabinetClaimsForCollection(params)
      setClaims(response.rows)
      setAggregates(response.aggregates)
    } catch (err: any) {
      console.error('Error cargando claims:', err)
      setError(err.message || 'Error al cargar datos.')
    } finally {
      setLoading(false)
    }
  }

  function handleExportCSV() {
    const params: any = {}
    if (paymentStatus) params.payment_status = paymentStatus
    if (overdueBucket) params.overdue_bucket = overdueBucket
    if (milestone) params.milestone_value = parseInt(milestone)
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    if (search) params.search = search

    const url = getYangoCabinetClaimsForCollectionCSVUrl(params)
    window.open(url, '_blank')
  }

  const getPaymentStatusColor = (status: string) => {
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

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6 text-red-600">
        <h1 className="text-3xl font-bold mb-6">Cobro Yango — Cabinet</h1>
        <p>Error: {error}</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Cobro Yango — Cabinet</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Total Amount</h3>
          <div className="text-2xl font-bold text-blue-600">{formatCurrency(aggregates.total_amount)}</div>
          <div className="text-sm text-gray-500 mt-1">{aggregates.total_rows} rows</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Unpaid Amount</h3>
          <div className="text-2xl font-bold text-red-600">{formatCurrency(aggregates.unpaid_amount)}</div>
          <div className="text-sm text-gray-500 mt-1">{aggregates.unpaid_rows} rows</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Misapplied Amount</h3>
          <div className="text-2xl font-bold text-yellow-600">{formatCurrency(aggregates.misapplied_amount)}</div>
          <div className="text-sm text-gray-500 mt-1">{aggregates.misapplied_rows} rows</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-600 mb-2">Paid Amount</h3>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(aggregates.paid_amount)}</div>
          <div className="text-sm text-gray-500 mt-1">{aggregates.paid_rows} rows</div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div>
            <label htmlFor="paymentStatus" className="block text-sm font-medium text-gray-700 mb-1">
              Payment Status
            </label>
            <input
              type="text"
              id="paymentStatus"
              value={paymentStatus}
              onChange={(e) => setPaymentStatus(e.target.value)}
              placeholder="UNPAID,PAID_MISAPPLIED"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">Comma-separated</p>
          </div>
          <div>
            <label htmlFor="overdueBucket" className="block text-sm font-medium text-gray-700 mb-1">
              Overdue Bucket
            </label>
            <select
              id="overdueBucket"
              value={overdueBucket}
              onChange={(e) => setOverdueBucket(e.target.value)}
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
            <label htmlFor="milestone" className="block text-sm font-medium text-gray-700 mb-1">
              Milestone
            </label>
            <select
              id="milestone"
              value={milestone}
              onChange={(e) => setMilestone(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todos</option>
              <option value="1">1</option>
              <option value="5">5</option>
              <option value="25">25</option>
            </select>
          </div>
          <div>
            <label htmlFor="dateFrom" className="block text-sm font-medium text-gray-700 mb-1">
              Date From
            </label>
            <input
              type="date"
              id="dateFrom"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label htmlFor="dateTo" className="block text-sm font-medium text-gray-700 mb-1">
              Date To
            </label>
            <input
              type="date"
              id="dateTo"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <input
              type="text"
              id="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="driver name or ID"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium"
          >
            Export CSV
          </button>
        </div>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Cargando datos...</div>
      ) : claims.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No hay datos disponibles para los filtros aplicados.</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
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
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPaymentStatusColor(claim.yango_payment_status)}`}>
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
    </div>
  )
}

