'use client'

import { formatCurrency } from '@/lib/utils'

interface ClaimsKPIsProps {
  kpis: {
    expected: number
    paid: number
    notPaid: number
    expectedCount: number
    paidCount: number
    notPaidCount: number
  }
}

export default function ClaimsKPIs({ kpis }: ClaimsKPIsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-600 mb-2">Expected Total</h3>
        <p className="text-2xl font-bold text-blue-600">{formatCurrency(kpis.expected)}</p>
        <p className="text-xs text-gray-500 mt-1">{kpis.expectedCount} claims</p>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-600 mb-2">Paid Total</h3>
        <p className="text-2xl font-bold text-green-600">{formatCurrency(kpis.paid)}</p>
        <p className="text-xs text-gray-500 mt-1">{kpis.paidCount} claims</p>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-sm font-medium text-gray-600 mb-2">Not Paid Total</h3>
        <p className="text-2xl font-bold text-red-600">{formatCurrency(kpis.notPaid)}</p>
        <p className="text-xs text-gray-500 mt-1">{kpis.notPaidCount} claims</p>
      </div>
    </div>
  )
}

