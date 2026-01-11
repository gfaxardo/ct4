/**
 * Dashboard - Página principal
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado general del sistema de identidad?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getIdentityStats, getGlobalMetrics, getRunReport, getPersonsBySource, getDriversWithoutLeadsAnalysis, getOrphansMetrics, runOrphansFix, ApiError } from '@/lib/api';
import type { IdentityStats, MetricsResponse, RunReportResponse, PersonsBySourceResponse, DriversWithoutLeadsAnalysis, OrphansMetricsResponse } from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState<IdentityStats | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [runReport, setRunReport] = useState<RunReportResponse | null>(null);
  const [personsBySource, setPersonsBySource] = useState<PersonsBySourceResponse | null>(null);
  const [driversWithoutLeads, setDriversWithoutLeads] = useState<DriversWithoutLeadsAnalysis | null>(null);
  const [orphansMetrics, setOrphansMetrics] = useState<OrphansMetricsResponse | null>(null);
  const [mode, setMode] = useState<'summary' | 'weekly' | 'breakdowns'>('breakdowns');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fixRunning, setFixRunning] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [statsData, metricsData, personsBySourceData, driversWithoutLeadsData, orphansMetricsData] = await Promise.all([
        getIdentityStats(),
        getGlobalMetrics({ mode }),
        getPersonsBySource(),
        getDriversWithoutLeadsAnalysis(),
        getOrphansMetrics(),
      ]);

      setStats(statsData);
      setMetrics(metricsData);
      setPersonsBySource(personsBySourceData);
      setDriversWithoutLeads(driversWithoutLeadsData);
      setOrphansMetrics(orphansMetricsData);

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
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const handleRunFix = async (execute: boolean = false) => {
    try {
      setFixRunning(true);
      setError(null);
      const result = await runOrphansFix({ execute, limit: 100 });
      // Recargar métricas después del fix
      if (result && !result.dry_run) {
        setTimeout(() => {
          loadData();
        }, 2000);
      }
      alert(`Fix ${execute ? 'ejecutado' : 'dry-run'} completado. Ver consola para detalles.`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error al ejecutar fix: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido al ejecutar fix');
      }
    } finally {
      setFixRunning(false);
    }
  };

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

      {/* Métricas de Drivers Huérfanos (Orphans) */}
      {mode === 'breakdowns' && orphansMetrics && orphansMetrics.total_orphans > 0 && (
        <div className="bg-orange-50 border-2 border-orange-300 rounded-lg p-6 mb-8">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-semibold text-orange-800 mb-2">📋 Drivers Huérfanos (Orphans)</h2>
              <p className="text-sm text-orange-600">
                Drivers detectados sin leads asociados. Los drivers en cuarentena están excluidos de funnel/claims/pagos.
              </p>
            </div>
            <Link href="/orphans" className="text-sm text-orange-700 hover:text-orange-900 underline">
              Ver Todos →
            </Link>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-white rounded p-4 border border-orange-200">
              <div className="text-sm text-orange-600 mb-1">Total</div>
              <div className="text-2xl font-bold text-orange-800">{orphansMetrics.total_orphans}</div>
            </div>
            <div className="bg-white rounded p-4 border border-red-200">
              <div className="text-sm text-red-600 mb-1">En Cuarentena</div>
              <div className="text-2xl font-bold text-red-800">{orphansMetrics.quarantined}</div>
            </div>
            <div className="bg-white rounded p-4 border border-green-200">
              <div className="text-sm text-green-600 mb-1">Resueltos</div>
              <div className="text-2xl font-bold text-green-800">{orphansMetrics.resolved_relinked + orphansMetrics.resolved_created_lead}</div>
            </div>
            <div className="bg-white rounded p-4 border border-blue-200">
              <div className="text-sm text-blue-600 mb-1">Con Lead Events</div>
              <div className="text-2xl font-bold text-blue-800">{orphansMetrics.with_lead_events}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
            <div>
              <h3 className="text-md font-medium mb-3 text-orange-700">Por Estado</h3>
              <div className="space-y-2">
                {Object.entries(orphansMetrics.by_status).filter(([status, count]) => count > 0).map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center">
                    <span className="text-sm text-orange-600 capitalize">{status.replace('_', ' ')}</span>
                    <span className="font-medium text-orange-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-md font-medium mb-3 text-orange-700">Por Razón</h3>
              <div className="space-y-2">
                {Object.entries(orphansMetrics.by_reason).filter(([reason, count]) => count > 0).map(([reason, count]) => (
                  <div key={reason} className="flex justify-between items-center">
                    <span className="text-sm text-orange-600 capitalize">{reason.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-orange-800">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-orange-200 flex gap-2">
            <button
              onClick={() => handleRunFix(false)}
              disabled={fixRunning}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              {fixRunning ? 'Ejecutando...' : 'Run Dry-Run'}
            </button>
            <button
              onClick={() => {
                if (confirm('¿Estás seguro de ejecutar el fix? Esto aplicará cambios en la base de datos.')) {
                  handleRunFix(true);
                }
              }}
              disabled={fixRunning}
              className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              {fixRunning ? 'Ejecutando...' : 'Ejecutar Fix'}
            </button>
            {orphansMetrics.last_updated_at && (
              <div className="ml-auto text-xs text-orange-600 self-center">
                Última actualización: {new Date(orphansMetrics.last_updated_at).toLocaleString()}
              </div>
            )}
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

      {/* Drivers Sin Leads - Análisis Detallado */}
      {driversWithoutLeads && driversWithoutLeads.total_drivers_without_leads > 0 && (
        <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-6 mb-8">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-lg font-semibold text-blue-800 mb-2">📊 Drivers Sin Leads - Análisis</h2>
              <p className="text-sm text-blue-600">
                Drivers que están en el sistema sin leads asociados. Los drivers en cuarentena están excluidos del funnel operativo.
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-white rounded p-4 border border-blue-200">
              <div className="text-sm text-blue-600 mb-1">Total (incluyendo quarantined)</div>
              <div className="text-2xl font-bold text-blue-800">{driversWithoutLeads.total_drivers_without_leads}</div>
            </div>
            <div className="bg-white rounded p-4 border border-red-200">
              <div className="text-sm text-red-600 mb-1">En Cuarentena</div>
              <div className="text-2xl font-bold text-red-800">{driversWithoutLeads.drivers_quarantined_count}</div>
            </div>
            <div className="bg-white rounded p-4 border border-orange-200">
              <div className="text-sm text-orange-600 mb-1">Operativos (sin leads)</div>
              <div className="text-2xl font-bold text-orange-800">{driversWithoutLeads.drivers_without_leads_operativos}</div>
              <div className="text-xs text-orange-500 mt-1">
                {driversWithoutLeads.drivers_without_leads_operativos === 0 ? '✅ OK' : '⚠️ Requiere atención'}
              </div>
            </div>
            <div className="bg-white rounded p-4 border border-green-200">
              <div className="text-sm text-green-600 mb-1">Con Lead Events</div>
              <div className="text-2xl font-bold text-green-800">{driversWithoutLeads.drivers_with_lead_events}</div>
            </div>
          </div>

          {driversWithoutLeads.quarantine_breakdown && Object.keys(driversWithoutLeads.quarantine_breakdown).length > 0 && (
            <div className="mt-4 pt-4 border-t border-blue-200">
              <h3 className="text-md font-medium mb-3 text-blue-700">Breakdown de Cuarentena por Razón</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(driversWithoutLeads.quarantine_breakdown).map(([reason, count]) => (
                  <div key={reason} className="bg-white rounded p-2 border border-blue-200">
                    <div className="text-xs text-blue-600 mb-1 capitalize">{reason.replace(/_/g, ' ')}</div>
                    <div className="text-lg font-bold text-blue-800">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-blue-200">
            <p className="text-sm text-blue-600">
              <strong>Interpretación:</strong> 
              {driversWithoutLeads.drivers_without_leads_operativos === 0 ? (
                <> ✅ Todos los drivers sin leads están en cuarentena. El sistema está funcionando correctamente.</>
              ) : (
                <> ⚠️ Hay {driversWithoutLeads.drivers_without_leads_operativos} drivers operativos sin leads que requieren atención. 
                Los {driversWithoutLeads.drivers_quarantined_count} drivers en cuarentena son legacy aislados y están excluidos del funnel/claims/pagos.</>
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
