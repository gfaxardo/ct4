/**
 * Scout Attribution Health - Observabilidad de Atribución de Scouts
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  getScoutAttributionMetrics,
  getScoutAttributionMetricsDaily,
  getScoutAttributionBacklog,
  getScoutAttributionJobStatus,
  runScoutAttributionNow,
  ApiError,
} from '@/lib/api';
import type {
  ScoutAttributionMetrics,
  ScoutAttributionMetricsDaily,
  ScoutAttributionBacklogResponse,
  ScoutAttributionJobStatus,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import Link from 'next/link';
import { PageLoadingOverlay } from '@/components/Skeleton';

const POLL_INTERVAL_MS = 12000;

// Icons
const Icons = {
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  alert: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

export default function ScoutAttributionHealthPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<ScoutAttributionMetrics | null>(null);
  const [dailyMetrics, setDailyMetrics] = useState<ScoutAttributionMetricsDaily | null>(null);
  const [backlog, setBacklog] = useState<ScoutAttributionBacklogResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<ScoutAttributionJobStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastUpdatedRef = useRef<Date | null>(null);

  const loadData = useCallback(async () => {
    try {
      setError(null);
      
      const [metricsData, dailyData, backlogData, jobData] = await Promise.all([
        getScoutAttributionMetrics(),
        getScoutAttributionMetricsDaily({ days: 30 }),
        getScoutAttributionBacklog({ category: categoryFilter || undefined, page: 1, page_size: 10 }),
        getScoutAttributionJobStatus(),
      ]);

      setMetrics(metricsData);
      setDailyMetrics(dailyData);
      setBacklog(backlogData);
      setJobStatus(jobData);
      lastUpdatedRef.current = new Date();
      setLastUpdated(lastUpdatedRef.current);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido');
      }
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  useEffect(() => {
    loadData();
    if (autoRefresh) {
      intervalRef.current = setInterval(loadData, POLL_INTERVAL_MS);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [autoRefresh, loadData]);

  const handleRunNow = async () => {
    try {
      setIsRunning(true);
      setError(null);
      await runScoutAttributionNow();
      setTimeout(loadData, 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ejecutando refresh: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido');
      }
    } finally {
      setIsRunning(false);
    }
  };

  const getTimeAgo = () => {
    if (!lastUpdated) return '';
    const seconds = Math.floor((new Date().getTime() - lastUpdated.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    return `${Math.floor(seconds / 3600)}h`;
  };

  const getHealthStatus = (): 'OK' | 'WARN' | 'FAIL' => {
    if (!metrics) return 'OK';
    if (metrics.last_job.status === 'FAILED') return 'FAIL';
    if (metrics.pct_scout_satisfactory < 50) return 'FAIL';
    if (metrics.conflicts_count > 100 || metrics.persons_missing_scout > metrics.total_persons * 0.3) return 'WARN';
    return 'OK';
  };

  if (loading && !metrics) {
    return <PageLoadingOverlay title="Atribución de Scouts" subtitle="Cargando métricas de salud..." />;
  }

  const healthStatus = getHealthStatus();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Salud de Atribución de Scouts</h1>
          <p className="text-slate-600">Observabilidad en tiempo real del sistema de atribución</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              autoRefresh
                ? 'bg-green-100 text-green-700 border border-green-200'
                : 'bg-slate-100 text-slate-600 border border-slate-200'
            }`}
          >
            {Icons.refresh}
            {autoRefresh ? 'Auto' : 'Pausado'}
          </button>
          {lastUpdated && (
            <span className="text-sm text-slate-500">hace {getTimeAgo()}</span>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-[#ef0000] text-white rounded-lg hover:bg-[#cc0000] transition-colors text-sm font-medium disabled:opacity-50"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : Icons.refresh}
            Actualizar
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="text-red-500">{Icons.alert}</div>
            <div>
              <p className="font-medium text-red-800">Error</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Health Status Banner */}
      <div className={`rounded-xl p-4 flex items-center gap-4 ${
        healthStatus === 'OK' ? 'bg-green-50 border border-green-200' :
        healthStatus === 'WARN' ? 'bg-amber-50 border border-amber-200' :
        'bg-red-50 border border-red-200'
      }`}>
        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
          healthStatus === 'OK' ? 'bg-green-100 text-green-600' :
          healthStatus === 'WARN' ? 'bg-amber-100 text-amber-600' :
          'bg-red-100 text-red-600'
        }`}>
          {healthStatus === 'OK' ? Icons.check : Icons.alert}
        </div>
        <div>
          <h2 className={`text-lg font-semibold ${
            healthStatus === 'OK' ? 'text-green-800' :
            healthStatus === 'WARN' ? 'text-amber-800' : 'text-red-800'
          }`}>
            Pipeline: {healthStatus === 'OK' ? 'Operativo' : healthStatus === 'WARN' ? 'Atención Requerida' : 'Problemas Críticos'}
          </h2>
          <p className={`text-sm ${
            healthStatus === 'OK' ? 'text-green-600' :
            healthStatus === 'WARN' ? 'text-amber-600' : 'text-red-600'
          }`}>
            {healthStatus === 'OK' && 'Sistema funcionando correctamente'}
            {healthStatus === 'WARN' && 'Algunas métricas fuera de rango'}
            {healthStatus === 'FAIL' && 'Acción requerida: revisar métricas'}
          </p>
        </div>
      </div>

      {/* Job Status */}
      {jobStatus && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-slate-900">Estado del Job de Atribución</h3>
              {jobStatus.last_run ? (
                <div className="mt-2 space-y-1 text-sm">
                  <p className="text-slate-600">
                    Última ejecución: <span className="font-medium text-slate-900">
                      {jobStatus.last_run.ended_at
                        ? new Date(jobStatus.last_run.ended_at).toLocaleString('es-ES')
                        : 'En curso'}
                    </span>
                  </p>
                  {jobStatus.last_run.duration_seconds && (
                    <p className="text-slate-600">
                      Duración: <span className="font-medium">{jobStatus.last_run.duration_seconds}s</span>
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-slate-600">Estado:</span>
                    <Badge variant={
                      jobStatus.last_run.status === 'COMPLETED' ? 'success' :
                      jobStatus.last_run.status === 'FAILED' ? 'error' : 'default'
                    }>
                      {jobStatus.last_run.status}
                    </Badge>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500 mt-2">Nunca ejecutado</p>
              )}
            </div>
            <button
              onClick={handleRunNow}
              disabled={isRunning || jobStatus.last_run?.status === 'RUNNING'}
              className="px-4 py-2 bg-[#ef0000] text-white rounded-lg hover:bg-[#cc0000] transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? 'Ejecutando...' : 'Ejecutar Ahora'}
            </button>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Scout Satisfactorio"
            value={`${metrics.pct_scout_satisfactory.toFixed(1)}%`}
            subtitle={`${metrics.persons_with_scout_satisfactory.toLocaleString()} de ${metrics.total_persons.toLocaleString()}`}
            icon={Icons.check}
            variant={metrics.pct_scout_satisfactory >= 80 ? 'success' : metrics.pct_scout_satisfactory >= 50 ? 'warning' : 'error'}
          />
          <StatCard
            title="Missing Scout"
            value={metrics.persons_missing_scout.toLocaleString()}
            subtitle={`${((metrics.persons_missing_scout / metrics.total_persons) * 100).toFixed(1)}% del total`}
            icon={Icons.users}
            variant={metrics.persons_missing_scout < metrics.total_persons * 0.2 ? 'success' : metrics.persons_missing_scout < metrics.total_persons * 0.4 ? 'warning' : 'error'}
          />
          <StatCard
            title="Conflictos"
            value={metrics.conflicts_count.toLocaleString()}
            subtitle="múltiples scouts por persona"
            icon={Icons.alert}
            variant={metrics.conflicts_count === 0 ? 'success' : metrics.conflicts_count < 50 ? 'warning' : 'error'}
          />
          <StatCard
            title="Backlog Total"
            value={(
              metrics.backlog.a_events_without_scout +
              metrics.backlog.d_scout_in_events_not_in_ledger +
              metrics.backlog.c_legacy
            ).toLocaleString()}
            subtitle="pendientes por resolver"
            icon={Icons.clock}
            variant="info"
          />
        </div>
      )}

      {/* Backlog by Category */}
      {metrics && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Backlog por Categoría</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-slate-200 rounded-lg p-4 hover:border-orange-300 transition-colors">
              <h3 className="font-medium text-slate-700 mb-2">A: Eventos sin Scout</h3>
              <p className="text-3xl font-bold text-orange-600 mb-1">
                {metrics.backlog.a_events_without_scout.toLocaleString()}
              </p>
              <p className="text-sm text-slate-500 mb-3">Lead events sin scout_id</p>
              <Link href="/scouts/backlog?category=A" className="text-sm text-[#ef0000] hover:underline font-medium">
                Ver registros →
              </Link>
            </div>
            
            <div className="border border-slate-200 rounded-lg p-4 hover:border-slate-400 transition-colors">
              <h3 className="font-medium text-slate-700 mb-2">C: Legacy</h3>
              <p className="text-3xl font-bold text-slate-600 mb-1">
                {metrics.backlog.c_legacy.toLocaleString()}
              </p>
              <p className="text-sm text-slate-500 mb-3">Sin eventos ni scout</p>
              <Link href="/scouts/backlog?category=C" className="text-sm text-[#ef0000] hover:underline font-medium">
                Ver registros →
              </Link>
            </div>
            
            <div className="border border-slate-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
              <h3 className="font-medium text-slate-700 mb-2">D: Scout no Propagado</h3>
              <p className="text-3xl font-bold text-blue-600 mb-1">
                {metrics.backlog.d_scout_in_events_not_in_ledger.toLocaleString()}
              </p>
              <p className="text-sm text-slate-500 mb-3">Scout en eventos no en ledger</p>
              <Link href="/scouts/backlog?category=D" className="text-sm text-[#ef0000] hover:underline font-medium">
                Ver registros →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Trends Chart */}
      {dailyMetrics && dailyMetrics.daily_metrics.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Tendencias (Últimos 30 días)</h2>
          <div className="h-48 flex items-end gap-1">
            {dailyMetrics.daily_metrics.slice(0, 30).reverse().map((metric, idx) => (
              <div
                key={metric.date}
                className="flex-1 bg-[#ef0000] hover:bg-[#ef0000] rounded-t transition-colors relative group cursor-pointer"
                style={{ height: `${Math.max(5, (metric.pct_satisfactory / 100) * 100)}%` }}
              >
                <div className="hidden group-hover:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-slate-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                  {new Date(metric.date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })}: {metric.pct_satisfactory.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-sm text-slate-500 text-center">
            % Scout Satisfactorio por día
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/scouts/conflicts"
          className="bg-white rounded-xl border border-slate-200 p-5 hover:border-cyan-300 hover:shadow-sm transition-all group"
        >
          <h3 className="font-semibold text-slate-900 mb-1 group-hover:text-[#ef0000]">Ver Conflictos</h3>
          <p className="text-sm text-slate-500">Personas con múltiples scouts asignados</p>
        </Link>
        
        <Link
          href="/pagos/cobranza-yango"
          className="bg-white rounded-xl border border-slate-200 p-5 hover:border-cyan-300 hover:shadow-sm transition-all group"
        >
          <h3 className="font-semibold text-slate-900 mb-1 group-hover:text-[#ef0000]">Cobranza Yango</h3>
          <p className="text-sm text-slate-500">Claims con información de scout</p>
        </Link>
        
        <Link
          href="/scouts/liquidation"
          className="bg-white rounded-xl border border-slate-200 p-5 hover:border-cyan-300 hover:shadow-sm transition-all group"
        >
          <h3 className="font-semibold text-slate-900 mb-1 group-hover:text-[#ef0000]">Liquidación Scouts</h3>
          <p className="text-sm text-slate-500">Vista base para liquidación diaria</p>
        </Link>
      </div>

      {/* Glossary */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-5">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Glosario</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h3 className="font-medium text-slate-700 mb-1">Scout Satisfactorio</h3>
            <p className="text-slate-500">
              Scout asignado en <code className="bg-slate-200 px-1 rounded text-xs">lead_ledger.attributed_scout_id</code>
            </p>
          </div>
          <div>
            <h3 className="font-medium text-slate-700 mb-1">Conflicto</h3>
            <p className="text-slate-500">Persona con múltiples scouts distintos. Requiere revisión manual.</p>
          </div>
          <div>
            <h3 className="font-medium text-slate-700 mb-1">Legacy</h3>
            <p className="text-slate-500">Personas sin eventos ni scout asignado. Registros antiguos.</p>
          </div>
          <div>
            <h3 className="font-medium text-slate-700 mb-1">Falta Identidad</h3>
            <p className="text-slate-500">
              Registros de <code className="bg-slate-200 px-1 rounded text-xs">scouting_daily</code> sin <code className="bg-slate-200 px-1 rounded text-xs">identity_links</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
