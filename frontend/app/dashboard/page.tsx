/**
 * Dashboard - Página principal
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado general del sistema de identidad?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getIdentityStats, getGlobalMetrics, getRunReport, getPersonsBySource, getDriversWithoutLeadsAnalysis, ApiError } from '@/lib/api';
import type { IdentityStats, MetricsResponse, RunReportResponse, PersonsBySourceResponse, DriversWithoutLeadsAnalysis } from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState<IdentityStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [runReport, setRunReport] = useState<RunReportResponse | null>(null);
  const [personsBySource, setPersonsBySource] = useState<PersonsBySourceResponse | null>(null);
  const [driversWithoutLeads, setDriversWithoutLeads] = useState<DriversWithoutLeadsAnalysis | null>(null);
  const [mode, setMode] = useState<'summary' | 'weekly' | 'breakdowns'>('breakdowns');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [statsData, metricsData, personsBySourceData, driversWithoutLeadsData] = await Promise.all([
          getIdentityStats(),
          getGlobalMetrics({ mode }),
          getPersonsBySource(),
          getDriversWithoutLeadsAnalysis(),
        ]);

        setStats(statsData);
        setMetrics(metricsData);
        setPersonsBySource(personsBySourceData);
        setDriversWithoutLeads(driversWithoutLeadsData);

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

      {/* Análisis de Drivers sin Leads */}
      {driversWithoutLeads && driversWithoutLeads.total_drivers_without_leads > 0 && (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4 text-red-800">⚠️ Drivers sin Leads Detectados</h2>
          <div className="mb-4">
            <p className="text-red-700 mb-2">
              <strong>Problema:</strong> Se encontraron <strong>{driversWithoutLeads.total_drivers_without_leads}</strong> drivers en el sistema 
              que NO tienen un lead asociado (ni cabinet, ni scouting, ni migrations).
            </p>
            <p className="text-sm text-red-600 mb-4">
              Estos drivers NO deberían estar en el sistema según el diseño. Los drivers solo deberían agregarse cuando matchean con un lead.
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
            <div>
              <h3 className="text-md font-medium mb-3 text-red-700">Por Regla de Creación</h3>
              <div className="space-y-2">
                {Object.entries(driversWithoutLeads.by_match_rule).map(([rule, count]) => (
                  <div key={rule} className="flex justify-between items-center">
                    <span className="text-sm text-red-600">{rule}</span>
                    <span className="font-medium text-red-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-md font-medium mb-3 text-red-700">Análisis de Lead Events</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-red-600">Con lead_events</span>
                  <span className="font-medium text-green-700">{driversWithoutLeads.drivers_with_lead_events}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-red-600">Sin lead_events</span>
                  <span className="font-medium text-red-800">{driversWithoutLeads.drivers_without_lead_events}</span>
                </div>
              </div>
              {Object.keys(driversWithoutLeads.missing_links_by_source).length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2 text-red-700">Links Faltantes por Fuente:</h4>
                  <div className="space-y-1">
                    {Object.entries(driversWithoutLeads.missing_links_by_source).map(([source, count]) => (
                      <div key={source} className="flex justify-between items-center text-sm">
                        <span className="text-red-600">{source}</span>
                        <span className="font-medium text-red-800">{count} drivers</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {driversWithoutLeads.sample_drivers.length > 0 && (
            <div className="mt-4 pt-4 border-t border-red-200">
              <h3 className="text-sm font-medium mb-2 text-red-700">Muestra de Casos (Top 10):</h3>
              <div className="space-y-2 text-sm">
                {driversWithoutLeads.sample_drivers.slice(0, 5).map((driver, idx) => (
                  <div key={idx} className="bg-white rounded p-2 border border-red-200">
                    <div className="flex justify-between">
                      <span className="font-medium">Driver: {driver.driver_id}</span>
                      <span className="text-gray-600">Regla: {driver.match_rule}</span>
                    </div>
                    <div className="text-gray-600 mt-1">
                      {driver.lead_events_count > 0 ? (
                        <span className="text-green-700">✓ {driver.lead_events_count} lead_events encontrados</span>
                      ) : (
                        <span className="text-red-700">✗ Sin lead_events</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <div className="mt-4 pt-4 border-t border-red-200">
            <p className="text-sm text-red-600">
              <strong>Acción recomendada:</strong> Ejecutar el script de limpieza para corregir estos casos:
              <code className="block mt-2 bg-red-100 p-2 rounded text-xs">
                python backend/scripts/fix_drivers_without_leads.py --execute
              </code>
            </p>
          </div>
        </div>
      )}

      {/* Desglose por Fuente */}
      {personsBySource && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">Desglose de Personas por Fuente</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-md font-medium mb-3 text-gray-700">Links por Fuente</h3>
              <div className="space-y-2">
                {Object.entries(personsBySource.links_by_source).map(([source, count]) => (
                  <div key={source} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">
                      {source === 'module_ct_cabinet_leads' ? 'Cabinet Leads' : 
                       source === 'module_ct_scouting_daily' ? 'Scouting Daily' : 
                       source === 'drivers' ? 'Drivers' : source}
                    </span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-md font-medium mb-3 text-gray-700">Personas por Fuente</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Con Cabinet Leads</span>
                  <span className="font-medium">{personsBySource.persons_with_cabinet_leads}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Con Scouting Daily</span>
                  <span className="font-medium">{personsBySource.persons_with_scouting_daily}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Con Drivers</span>
                  <span className="font-medium">{personsBySource.persons_with_drivers}</span>
                </div>
                <div className="flex justify-between items-center pt-2 border-t border-gray-200">
                  <span className="text-sm font-medium text-gray-800">Solo Drivers (sin leads)</span>
                  <span className="font-bold text-blue-600">{personsBySource.persons_only_drivers}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-800">Con Cabinet o Scouting</span>
                  <span className="font-bold text-green-600">{personsBySource.persons_with_cabinet_or_scouting}</span>
                </div>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              <strong>Explicación:</strong> El total de {personsBySource.total_persons} personas incluye todas las fuentes. 
              {personsBySource.persons_only_drivers > 0 && (
                <> {personsBySource.persons_only_drivers} personas solo tienen links de drivers (están en el parque pero no vinieron de leads).</>
              )}
            </p>
          </div>
        </div>
      )}

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
