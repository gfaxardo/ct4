'use client'

import { WeeklyData, WeeklyTrend } from '@/lib/api'

interface WeeklyMetricsViewProps {
  weekly: WeeklyData[]
  weekly_trend?: WeeklyTrend[]
  loading?: boolean
}

export default function WeeklyMetricsView({ weekly, weekly_trend, loading }: WeeklyMetricsViewProps) {
  if (loading) {
    return (
      <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border">
        <p className="text-lg mb-2">Cargando datos semanales...</p>
      </div>
    )
  }

  if (!weekly || weekly.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border">
        <p className="text-lg mb-2">No hay datos semanales disponibles</p>
        <p className="text-sm">Asegúrate de cargar el reporte con group_by=week</p>
      </div>
    )
  }

  return (
    <>
      {weekly_trend && weekly_trend.length > 0 && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="font-semibold mb-3 text-lg">Evolución Semanal</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {weekly_trend.map((trend, idx) => (
              <div key={idx} className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm font-semibold mb-3 text-gray-700">
                  {trend.source_table || 'Total General'} - {trend.week_label}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Match Rate Actual:</span>
                    <span className="font-bold text-lg">{trend.current_match_rate.toFixed(2)}%</span>
                  </div>
                  {trend.previous_match_rate !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Match Rate Anterior:</span>
                      <span className="font-medium">{trend.previous_match_rate.toFixed(2)}%</span>
                    </div>
                  )}
                  {trend.delta_match_rate !== null && (
                    <div className={`flex justify-between items-center pt-2 border-t ${trend.delta_match_rate >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      <span className="font-medium">Δ Match Rate:</span>
                      <span className="font-bold text-lg flex items-center gap-1">
                        {trend.delta_match_rate >= 0 ? '↑' : '↓'} {trend.delta_match_rate >= 0 ? '+' : ''}{trend.delta_match_rate.toFixed(2)}%
                      </span>
                    </div>
                  )}
                  {trend.delta_matched !== null && (
                    <div className={`flex justify-between items-center ${trend.delta_matched >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      <span className="text-gray-600">Δ Matched:</span>
                      <span className="font-medium flex items-center gap-1">
                        {trend.delta_matched >= 0 ? '↑' : '↓'} {trend.delta_matched >= 0 ? '+' : ''}{trend.delta_matched}
                      </span>
                    </div>
                  )}
                  {trend.delta_unmatched !== null && (
                    <div className={`flex justify-between items-center ${trend.delta_unmatched >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                      <span className="text-gray-600">Δ Unmatched:</span>
                      <span className="font-medium flex items-center gap-1">
                        {trend.delta_unmatched >= 0 ? '↑' : '↓'} {trend.delta_unmatched >= 0 ? '+' : ''}{trend.delta_unmatched}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="mb-6">
        <h3 className="font-semibold mb-3 text-lg">KPIs Semanales</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 border border-gray-300">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Semana</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">Fuente</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Processed Total</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Matched</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Unmatched</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">Match Rate</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">Diagnóstico</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {weekly.map((week, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium">{week.week_label}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{week.source_table}</td>
                  <td className="px-4 py-3 text-sm text-right font-medium">{week.processed_total.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-right text-green-600 font-medium">{week.matched.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-right text-red-600 font-medium">{week.unmatched.toLocaleString()}</td>
                  <td className="px-4 py-3 text-sm text-right">
                    <span className={`font-bold ${week.match_rate >= 80 ? 'text-green-600' : week.match_rate >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {week.match_rate.toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-center">
                    <details className="cursor-pointer">
                      <summary className="text-blue-600 hover:text-blue-800 font-medium">Ver</summary>
                      <div className="mt-3 p-4 bg-gray-50 rounded-lg border text-xs space-y-3">
                        <div>
                          <strong className="text-gray-700">Unmatched por Razón:</strong>
                          <ul className="mt-2 space-y-1">
                            {Object.entries(week.unmatched_by_reason).length > 0 ? (
                              Object.entries(week.unmatched_by_reason).map(([reason, count]) => (
                                <li key={reason} className="flex justify-between items-center py-1">
                                  <span className="text-gray-600">{reason}:</span>
                                  <span className="font-semibold text-red-600">{count}</span>
                                </li>
                              ))
                            ) : (
                              <li className="text-gray-500">Sin unmatched</li>
                            )}
                          </ul>
                        </div>
                        {week.top_missing_keys.length > 0 && (
                          <div>
                            <strong className="text-gray-700">Top Missing Keys:</strong>
                            <ul className="mt-2 space-y-1">
                              {week.top_missing_keys.map((item, i) => (
                                <li key={i} className="flex justify-between items-center py-1">
                                  <span className="text-gray-600">{item.key}:</span>
                                  <span className="font-semibold text-orange-600">{item.count}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        <div className="pt-2 border-t">
                          <strong className="text-gray-700">Matched por Regla:</strong>
                          <ul className="mt-2 space-y-1">
                            {Object.entries(week.matched_by_rule).map(([rule, count]) => (
                              <li key={rule} className="flex justify-between items-center py-1">
                                <span className="text-gray-600">{rule}:</span>
                                <span className="font-semibold text-green-600">{count}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <strong className="text-gray-700">Matched por Confianza:</strong>
                          <ul className="mt-2 space-y-1">
                            {Object.entries(week.matched_by_confidence).map(([conf, count]) => (
                              <li key={conf} className="flex justify-between items-center py-1">
                                <span className="text-gray-600">{conf}:</span>
                                <span className="font-semibold text-green-600">{count}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}



















