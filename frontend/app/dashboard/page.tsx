/**
 * Dashboard - Página principal con diseño moderno
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado general del sistema de identidad?"
 */

'use client';

import { useState, useEffect } from 'react';
import { runOrphansFix, ApiError } from '@/lib/api';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import Link from 'next/link';
import {
  useIdentityStats,
  useGlobalMetrics,
  usePersonsBySource,
  useDriversWithoutLeads,
  useOrphansMetrics,
} from '@/lib/hooks/use-dashboard';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Iconos SVG
const Icons = {
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  chart: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  arrow: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
};

// Spinner para cambio de tabs
function TabLoadingSpinner({ text }: { text: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/60 p-12 flex flex-col items-center justify-center min-h-[300px]">
      <div className="relative w-12 h-12 mb-4">
        <div className="absolute inset-0 border-4 border-slate-200 rounded-full" />
        <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <p className="text-slate-600 font-medium">{text}</p>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-center">
      <div className="mx-auto w-12 h-12 rounded-full bg-rose-100 flex items-center justify-center mb-4">
        <svg className="w-6 h-6 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p className="text-rose-800 font-medium mb-2">Error al cargar datos</p>
      <p className="text-rose-600 text-sm mb-4">{message}</p>
      <button onClick={onRetry} className="btn btn-primary">
        Reintentar
      </button>
    </div>
  );
}

export default function DashboardPage() {
  const [mode, setMode] = useState<'weekly' | 'breakdowns'>('breakdowns');
  const [fixRunning, setFixRunning] = useState(false);
  const [fixError, setFixError] = useState<string | null>(null);
  
  // Minimum loading time to ensure skeleton is visible
  const [minLoadingComplete, setMinLoadingComplete] = useState(false);
  
  useEffect(() => {
    // Show skeleton for at least 800ms on initial load for better UX
    const timer = setTimeout(() => {
      setMinLoadingComplete(true);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // React Query hooks with caching
  const { 
    data: stats, 
    isFetching: fetchingStats,
    error: statsError, 
    refetch: refetchStats 
  } = useIdentityStats();
  
  const { 
    data: metrics, 
    isFetching: fetchingMetrics 
  } = useGlobalMetrics(mode);
  
  const { 
    data: personsBySource, 
    isFetching: fetchingPersons 
  } = usePersonsBySource();
  
  const { 
    data: driversWithoutLeads, 
    isFetching: fetchingDrivers 
  } = useDriversWithoutLeads();
  
  const { 
    data: orphansMetrics, 
    isFetching: fetchingOrphans, 
    refetch: refetchOrphans 
  } = useOrphansMetrics();

  // Show skeleton when:
  // 1. We haven't passed minimum loading time yet, OR
  // 2. We're fetching and don't have stats data
  const showSkeleton = !minLoadingComplete || (!stats && fetchingStats);
  
  // Show spinner when we have data but are refetching in background
  const isRefetching = fetchingStats || fetchingMetrics || fetchingPersons || fetchingDrivers || fetchingOrphans;
  
  const error = statsError ? (statsError as Error).message : null;

  const handleRunFix = async (execute: boolean = false) => {
    try {
      setFixRunning(true);
      setFixError(null);
      const result = await runOrphansFix({ execute, limit: 100 });
      if (result && !result.dry_run) {
        // Refetch orphans data after fix
        setTimeout(() => {
          refetchOrphans();
          refetchStats();
        }, 2000);
      }
      alert(`Fix ${execute ? 'ejecutado' : 'dry-run'} completado. Ver consola para detalles.`);
    } catch (err) {
      if (err instanceof ApiError) {
        setFixError(`Error al ejecutar fix: ${err.detail || err.message}`);
      } else {
        setFixError('Error desconocido al ejecutar fix');
      }
    } finally {
      setFixRunning(false);
    }
  };

  // Show loading overlay on initial page load
  if (showSkeleton) {
    return <PageLoadingOverlay title="Dashboard" subtitle="Cargando estadísticas del sistema..." />;
  }

  if (error && !stats) {
    return <ErrorState message={error} onRetry={() => refetchStats()} />;
  }

  if (!stats) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-500">No hay estadísticas disponibles</p>
      </div>
    );
  }

  const matchRate = stats?.conversion_rate ?? 0;
  const totalPersons = stats?.total_persons ?? 0;
  const totalUnmatched = stats?.total_unmatched ?? 0;

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1">Vista general del sistema de identidad</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success" dot>Sincronizado</Badge>
        </div>
      </div>

      {/* StatCards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Personas Identificadas"
          value={totalPersons.toLocaleString()}
          subtitle="Registros únicos"
          variant="brand"
          icon={Icons.users}
        />
        <StatCard
          title="Sin Resolver"
          value={totalUnmatched.toLocaleString()}
          subtitle="Pendientes de match"
          variant={totalUnmatched > 0 ? 'warning' : 'success'}
          icon={Icons.warning}
        />
        <StatCard
          title="Tasa de Match"
          value={`${matchRate.toFixed(1)}%`}
          subtitle="Conversión general"
          variant={matchRate >= 90 ? 'success' : matchRate >= 70 ? 'info' : 'warning'}
          icon={Icons.chart}
        />
      </div>

      {/* Mode Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg w-fit">
          {(['breakdowns', 'weekly'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`
                px-4 py-2 rounded-md text-sm font-medium
                transition-all duration-200
                ${mode === m
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
                }
              `}
            >
              {m === 'weekly' ? 'Semanal' : 'Resumen'}
            </button>
          ))}
        </div>
        {isRefetching && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <svg className="animate-spin h-4 w-4 text-cyan-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Actualizando...
          </div>
        )}
      </div>

      {/* Métricas de Drivers Huérfanos (Orphans) */}
      {mode === 'breakdowns' && orphansMetrics && orphansMetrics.total_orphans > 0 && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-6">
          <div className="flex justify-between items-start mb-6">
            <div className="flex items-start gap-4">
              <div className="p-3 rounded-xl bg-amber-100">
                <svg className="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-amber-900">Drivers Huérfanos</h2>
                <p className="text-sm text-amber-700 mt-1">
                  Drivers detectados sin leads asociados. Los en cuarentena están excluidos del funnel.
                </p>
              </div>
            </div>
            <Link 
              href="/orphans" 
              className="flex items-center gap-1 text-sm font-medium text-amber-700 hover:text-amber-900 transition-colors"
            >
              Ver todos {Icons.arrow}
            </Link>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white/80 rounded-xl p-4 border border-amber-200/50">
              <div className="text-sm text-amber-600 mb-1">Total</div>
              <div className="text-2xl font-bold text-amber-900">{orphansMetrics.total_orphans.toLocaleString()}</div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-rose-200/50">
              <div className="text-sm text-rose-600 mb-1">En Cuarentena</div>
              <div className="text-2xl font-bold text-rose-800">{orphansMetrics.quarantined.toLocaleString()}</div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-emerald-200/50">
              <div className="text-sm text-emerald-600 mb-1">Resueltos</div>
              <div className="text-2xl font-bold text-emerald-800">
                {(orphansMetrics.resolved_relinked + orphansMetrics.resolved_created_lead).toLocaleString()}
              </div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-cyan-200/50">
              <div className="text-sm text-cyan-600 mb-1">Con Lead Events</div>
              <div className="text-2xl font-bold text-cyan-800">{orphansMetrics.with_lead_events.toLocaleString()}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-white/60 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-amber-800 mb-3">Por Estado</h3>
              <div className="space-y-2">
                {Object.entries(orphansMetrics.by_status).filter(([, count]) => count > 0).map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center">
                    <span className="text-sm text-amber-700 capitalize">{status.replace('_', ' ')}</span>
                    <Badge variant="warning">{count}</Badge>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white/60 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-amber-800 mb-3">Por Razón</h3>
              <div className="space-y-2">
                {Object.entries(orphansMetrics.by_reason).filter(([, count]) => count > 0).map(([reason, count]) => (
                  <div key={reason} className="flex justify-between items-center">
                    <span className="text-sm text-amber-700 capitalize">{reason.replace(/_/g, ' ')}</span>
                    <Badge variant="warning">{count}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <div className="flex items-center justify-between pt-4 border-t border-amber-200/50">
            <div className="flex gap-2">
              <button
                onClick={() => handleRunFix(false)}
                disabled={fixRunning}
                className="btn btn-secondary text-sm"
              >
                {fixRunning ? 'Ejecutando...' : 'Dry Run'}
              </button>
              <button
                onClick={() => {
                  if (confirm('¿Ejecutar el fix? Esto aplicará cambios en la base de datos.')) {
                    handleRunFix(true);
                  }
                }}
                disabled={fixRunning}
                className="btn btn-warning text-sm"
              >
                {fixRunning ? 'Ejecutando...' : 'Ejecutar Fix'}
              </button>
            </div>
            {orphansMetrics.last_updated_at && (
              <span className="text-xs text-amber-600">
                Última actualización: {new Date(orphansMetrics.last_updated_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Desglose por Fuente */}
      {personsBySource?.links_by_source && (
        <div className="card">
          <div className="card-header">
            <h2 className="text-lg font-semibold text-slate-900">Desglose de Personas por Fuente</h2>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-cyan-500" />
                  Links por Fuente
                </h3>
                <div className="space-y-3">
                  {Object.entries(personsBySource.links_by_source ?? {}).map(([source, count]) => (
                    <div key={source} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                      <span className="text-sm text-slate-600">
                        {source === 'module_ct_cabinet_leads' ? 'Cabinet Leads' : 
                         source === 'module_ct_scouting_daily' ? 'Scouting Daily' : 
                         source === 'drivers' ? 'Drivers' : source}
                      </span>
                      <span className="font-semibold text-slate-900">{(count ?? 0).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  Personas por Fuente
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                    <span className="text-sm text-slate-600">Con Cabinet Leads</span>
                    <span className="font-semibold text-slate-900">{(personsBySource.persons_with_cabinet_leads ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                    <span className="text-sm text-slate-600">Con Scouting Daily</span>
                    <span className="font-semibold text-slate-900">{(personsBySource.persons_with_scouting_daily ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                    <span className="text-sm text-slate-600">Con Drivers</span>
                    <span className="font-semibold text-slate-900">{(personsBySource.persons_with_drivers ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-cyan-50 rounded-lg border border-cyan-200">
                    <span className="text-sm font-medium text-cyan-800">Solo Drivers (sin leads)</span>
                    <Badge variant="info">{(personsBySource.persons_only_drivers ?? 0).toLocaleString()}</Badge>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                    <span className="text-sm font-medium text-emerald-800">Con Cabinet o Scouting</span>
                    <Badge variant="success">{(personsBySource.persons_with_cabinet_or_scouting ?? 0).toLocaleString()}</Badge>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-6 p-4 bg-slate-50 rounded-lg">
              <p className="text-sm text-slate-600">
                <strong className="text-slate-700">Nota:</strong> El total de {(personsBySource.total_persons ?? 0).toLocaleString()} personas incluye todas las fuentes.
                {(personsBySource.persons_only_drivers ?? 0) > 0 && (
                  <> {(personsBySource.persons_only_drivers ?? 0).toLocaleString()} personas solo tienen links de drivers (están en el parque pero no vinieron de leads).</>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Drivers Sin Leads - Análisis Detallado */}
      {driversWithoutLeads && driversWithoutLeads.total_drivers_without_leads > 0 && (
        <div className="bg-gradient-to-r from-cyan-50 to-blue-50 border border-cyan-200 rounded-xl p-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="p-3 rounded-xl bg-cyan-100">
              <svg className="w-6 h-6 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-cyan-900">Drivers Sin Leads - Análisis</h2>
              <p className="text-sm text-cyan-700 mt-1">
                Drivers en el sistema sin leads asociados. Los en cuarentena están excluidos del funnel operativo.
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white/80 rounded-xl p-4 border border-cyan-200/50">
              <div className="text-sm text-cyan-600 mb-1">Total (incl. quarantined)</div>
              <div className="text-2xl font-bold text-cyan-900">{driversWithoutLeads.total_drivers_without_leads.toLocaleString()}</div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-rose-200/50">
              <div className="text-sm text-rose-600 mb-1">En Cuarentena</div>
              <div className="text-2xl font-bold text-rose-800">{driversWithoutLeads.drivers_quarantined_count.toLocaleString()}</div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-amber-200/50">
              <div className="text-sm text-amber-600 mb-1">Operativos (sin leads)</div>
              <div className="text-2xl font-bold text-amber-800">
                {driversWithoutLeads.drivers_without_leads_operativos.toLocaleString()}
              </div>
              <div className="text-xs mt-1">
                {driversWithoutLeads.drivers_without_leads_operativos === 0 
                  ? <Badge variant="success" size="sm">OK</Badge>
                  : <Badge variant="warning" size="sm">Atención</Badge>
                }
              </div>
            </div>
            <div className="bg-white/80 rounded-xl p-4 border border-emerald-200/50">
              <div className="text-sm text-emerald-600 mb-1">Con Lead Events</div>
              <div className="text-2xl font-bold text-emerald-800">{driversWithoutLeads.drivers_with_lead_events.toLocaleString()}</div>
            </div>
          </div>

          {driversWithoutLeads.quarantine_breakdown && Object.keys(driversWithoutLeads.quarantine_breakdown).length > 0 && (
            <div className="bg-white/60 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-cyan-800 mb-3">Breakdown de Cuarentena por Razón</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(driversWithoutLeads.quarantine_breakdown).map(([reason, count]) => (
                  <div key={reason} className="bg-white rounded-lg p-3 border border-cyan-200/50">
                    <div className="text-xs text-cyan-600 mb-1 capitalize">{reason.replace(/_/g, ' ')}</div>
                    <div className="text-lg font-bold text-cyan-800">{count.toLocaleString()}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 p-4 bg-white/60 rounded-lg">
            <p className="text-sm text-cyan-700">
              <strong className="text-cyan-800">Interpretación:</strong>{' '}
              {driversWithoutLeads.drivers_without_leads_operativos === 0 ? (
                <>✅ Todos los drivers sin leads están en cuarentena. El sistema funciona correctamente.</>
              ) : (
                <>⚠️ Hay {driversWithoutLeads.drivers_without_leads_operativos.toLocaleString()} drivers operativos sin leads que requieren atención.</>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Tab Content with Loading State */}
      {/* Show spinner when fetching and current tab data is not available */}
      {(fetchingMetrics && ((mode === 'breakdowns' && !metrics?.breakdowns) || (mode === 'weekly' && !metrics?.weekly))) ? (
        <TabLoadingSpinner text={`Cargando ${mode === 'weekly' ? 'métricas semanales' : 'resumen'}...`} />
      ) : (
        <>
          {/* Breakdowns */}
          {mode === 'breakdowns' && metrics?.breakdowns && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-slate-900">Matched por Regla (Global)</h2>
                </div>
                <div className="card-body">
                  <div className="space-y-3">
                    {Object.entries(metrics.breakdowns.matched_by_rule).map(([rule, count]) => (
                      <div key={rule} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                        <span className="text-sm text-slate-700 font-medium">{rule}</span>
                        <Badge variant="success">{count.toLocaleString()}</Badge>
                      </div>
                    ))}
                    {Object.keys(metrics.breakdowns.matched_by_rule).length === 0 && (
                      <p className="text-sm text-slate-400 text-center py-4">No hay matches</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-slate-900">Unmatched por Razón (Top 5)</h2>
                </div>
                <div className="card-body">
                  <div className="space-y-3">
                    {Object.entries(metrics.breakdowns.unmatched_by_reason)
                      .slice(0, 5)
                      .map(([reason, count]) => (
                        <div key={reason} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                          <span className="text-sm text-slate-700 font-medium">{reason}</span>
                          <Badge variant="warning">{count.toLocaleString()}</Badge>
                        </div>
                      ))}
                    {Object.keys(metrics.breakdowns.unmatched_by_reason).length === 0 && (
                      <p className="text-sm text-slate-400 text-center py-4">No hay unmatched</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Weekly View */}
          {mode === 'weekly' && metrics?.weekly && (
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-slate-900">Métricas Semanales</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="table-modern">
                  <thead>
                    <tr>
                      <th>Semana</th>
                      <th>Fuente</th>
                      <th className="text-right">Matched</th>
                      <th className="text-right">Unmatched</th>
                      <th className="text-right">Match Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.weekly.map((week, idx) => (
                      <tr key={idx}>
                        <td className="font-medium">{week.week_label}</td>
                        <td>
                          <Badge variant="default" size="sm">{week.source_table}</Badge>
                        </td>
                        <td className="text-right font-semibold text-emerald-600">{week.matched.toLocaleString()}</td>
                        <td className="text-right font-semibold text-amber-600">{week.unmatched.toLocaleString()}</td>
                        <td className="text-right">
                          <Badge 
                            variant={week.match_rate >= 90 ? 'success' : week.match_rate >= 70 ? 'info' : 'warning'}
                          >
                            {week.match_rate.toFixed(1)}%
                          </Badge>
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

      {/* Alerts Section - PENDING */}
      <div className="alert alert-info">
        <svg className="w-5 h-5 text-cyan-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <p className="font-medium text-cyan-800">Próximamente</p>
          <p className="text-sm text-cyan-700">Sección de Alertas requiere endpoint GET /api/v1/ops/alerts</p>
        </div>
      </div>
    </div>
  );
}
