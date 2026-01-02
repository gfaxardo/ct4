/**
 * Dashboard - Página principal
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado general del sistema de identidad?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getIdentityStats, getGlobalMetrics, getRunReport, ApiError } from '@/lib/api';
import type { IdentityStats, MetricsResponse, RunReportResponse } from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState<IdentityStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [runReport, setRunReport] = useState<RunReportResponse | null>(null);
  const [mode, setMode] = useState<'summary' | 'weekly' | 'breakdowns'>('breakdowns');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [statsData, metricsData] = await Promise.all([
          getIdentityStats(),
          getGlobalMetrics({ mode }),
        ]);

        setStats(statsData);
        setMetrics(metricsData);

        // Intentar obtener última corrida (si hay runs disponibles)
        // Nota: Falta endpoint GET /api/v1/identity/runs, por ahora no cargamos runReport
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 500) {
            setError('Error al cargar estadísticas');
          } else {
            setError(`Error ${err.status}: ${err.detail || err.message}`);
          }
        } else {
          setError('Error desconocido');
        }
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [mode]);

  if (loading) {
    return <div className="text-center py-12">Cargando...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!stats) {
    return <div className="text-center py-12">No hay estadísticas disponibles</div>;
  }

  // NO recalcular conversion_rate - viene del backend
  const matchRate = stats.conversion_rate;

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {/* StatCards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Personas Identificadas"
          value={stats.total_persons}
        />
        <StatCard
          title="Sin Resolver"
          value={stats.total_unmatched}
        />
        <StatCard
          title="Tasa de Match"
          value={`${matchRate.toFixed(1)}%`}
        />
      </div>

      {/* Mode Selector */}
      <div className="mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setMode('summary')}
            className={`px-4 py-2 rounded-md ${
              mode === 'summary'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Resumen
          </button>
          <button
            onClick={() => setMode('weekly')}
            className={`px-4 py-2 rounded-md ${
              mode === 'weekly'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Semanal
          </button>
          <button
            onClick={() => setMode('breakdowns')}
            className={`px-4 py-2 rounded-md ${
              mode === 'breakdowns'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Breakdowns
          </button>
        </div>
      </div>

      {/* Breakdowns */}
      {mode === 'summary' || mode === 'breakdowns' ? (
        metrics?.breakdowns && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Matched por Regla (Global)</h2>
              <div className="space-y-2">
                {Object.entries(metrics.breakdowns.matched_by_rule).map(([rule, count]) => (
                  <div key={rule} className="flex justify-between items-center">
                    <span className="text-sm">{rule}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
                {Object.keys(metrics.breakdowns.matched_by_rule).length === 0 && (
                  <p className="text-sm text-gray-500">No hay matches</p>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Unmatched por Razón (Top 5) - Global</h2>
              <div className="space-y-2">
                {Object.entries(metrics.breakdowns.unmatched_by_reason)
                  .slice(0, 5)
                  .map(([reason, count]) => (
                    <div key={reason} className="flex justify-between items-center">
                      <span className="text-sm">{reason}</span>
                      <span className="font-medium">{count}</span>
                    </div>
                  ))}
                {Object.keys(metrics.breakdowns.unmatched_by_reason).length === 0 && (
                  <p className="text-sm text-gray-500">No hay unmatched</p>
                )}
              </div>
            </div>
          </div>
        )
      ) : null}

      {/* Weekly View */}
      {mode === 'weekly' && metrics?.weekly && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">Métricas Semanales</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Semana</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fuente</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Matched</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unmatched</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rate</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {metrics.weekly.map((week, idx) => (
                  <tr key={idx}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{week.week_label}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{week.source_table}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{week.matched}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{week.unmatched}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{week.match_rate.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Alerts Section - PENDING */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
        <p className="text-yellow-800 text-sm">
          <strong>PENDING:</strong> Sección de Alertas requiere endpoint GET /api/v1/ops/alerts
        </p>
      </div>
    </div>
  );
}
