/**
 * Scout Attribution Health - Observabilidad de Atribución de Scouts
 * 
 * Objetivo: "¿Cuál es la salud del sistema de atribución de scouts?"
 * 
 * Características:
 * - Auto-refresh cada 10-15s (configurable)
 * - Indicador "Actualizado hace X segundos"
 * - Botón "Actualizar ahora"
 * - Cards con métricas + tooltips explicativos
 * - Tabla de backlog por categorías
 * - Gráfico de tendencias (30 días)
 * - Estado del job + botón ejecutar
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

const POLL_INTERVAL_MS = 12000; // 12 segundos (configurable)

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
      console.error('Error cargando datos:', err);
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  useEffect(() => {
    // Carga inicial
    loadData();

    // Auto-refresh
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        loadData();
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, loadData]);

  const handleRunNow = async () => {
    try {
      setIsRunning(true);
      setError(null);
      
      await runScoutAttributionNow();
      
      // Recargar datos después de ejecutar
      setTimeout(() => {
        loadData();
      }, 2000);
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
    if (seconds < 60) return `${seconds} segundos`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutos`;
    return `${Math.floor(seconds / 3600)} horas`;
  };

  const getHealthStatus = (): 'OK' | 'WARN' | 'FAIL' => {
    if (!metrics) return 'OK';
    
    if (metrics.last_job.status === 'FAILED') return 'FAIL';
    if (metrics.pct_scout_satisfactory < 50) return 'FAIL';
    if (metrics.conflicts_count > 100 || metrics.persons_missing_scout > metrics.total_persons * 0.3) return 'WARN';
    
    return 'OK';
  };

  if (loading && !metrics) {
    return <div className="text-center py-12">Cargando...</div>;
  }

  const healthStatus = getHealthStatus();

  return (
    <div className="px-4 py-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Scouts → Salud de Atribución</h1>
          <p className="text-gray-600 mt-1">
            Observabilidad en tiempo real del sistema de atribución de scouts
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1 rounded-md text-sm ${
              autoRefresh
                ? 'bg-green-100 text-green-800 border border-green-300'
                : 'bg-gray-100 text-gray-800 border border-gray-300'
            }`}
          >
            {autoRefresh ? '🔄 Auto-actualizando' : '⏸ Pausado'}
          </button>
          
          {/* Last updated */}
          {lastUpdated && (
            <span className="text-sm text-gray-500">
              Actualizado hace {getTimeAgo()}
            </span>
          )}
          
          {/* Refresh button */}
          <button
            onClick={loadData}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Actualizando...' : 'Actualizar ahora'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Health Status */}
      <div className={`mb-6 p-4 rounded-lg ${
        healthStatus === 'OK' ? 'bg-green-50 border border-green-200' :
        healthStatus === 'WARN' ? 'bg-yellow-50 border border-yellow-200' :
        'bg-red-50 border border-red-200'
      }`}>
        <div className="flex items-center gap-2">
          <span className="text-2xl">
            {healthStatus === 'OK' ? '✅' : healthStatus === 'WARN' ? '⚠️' : '❌'}
          </span>
          <div>
            <h2 className="font-semibold">
              Estado del Pipeline: {healthStatus === 'OK' ? 'OK' : healthStatus === 'WARN' ? 'ADVERTENCIA' : 'FALLIDO'}
            </h2>
            <p className="text-sm text-gray-600">
              {healthStatus === 'OK' && 'Sistema funcionando correctamente'}
              {healthStatus === 'WARN' && 'Atención requerida: algunos métricas fuera de rango'}
              {healthStatus === 'FAIL' && 'Acción requerida: problemas críticos detectados'}
            </p>
          </div>
        </div>
      </div>

      {/* Job Status */}
      {jobStatus && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-semibold">Estado del Job</h3>
              {jobStatus.last_run ? (
                <div className="mt-2 text-sm text-gray-600">
                  <p>
                    <strong>Última ejecución:</strong>{' '}
                    {jobStatus.last_run.ended_at
                      ? new Date(jobStatus.last_run.ended_at).toLocaleString('es-ES')
                      : 'En curso'}
                  </p>
                  {jobStatus.last_run.duration_seconds && (
                    <p>
                      <strong>Duración:</strong> {jobStatus.last_run.duration_seconds} segundos
                    </p>
                  )}
                  <p>
                    <strong>Resultado:</strong>{' '}
                    <Badge
                      variant={
                        jobStatus.last_run.status === 'COMPLETED' ? 'success' :
                        jobStatus.last_run.status === 'FAILED' ? 'error' : 'default'
                      }
                    >
                      {jobStatus.last_run.status}
                    </Badge>
                  </p>
                  {jobStatus.last_run.error && (
                    <p className="text-red-600 mt-1">
                      <strong>Error:</strong> {jobStatus.last_run.error}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-600 mt-2">Nunca ejecutado</p>
              )}
            </div>
            <button
              onClick={handleRunNow}
              disabled={isRunning || jobStatus.last_run?.status === 'RUNNING'}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {isRunning ? 'Ejecutando...' : 'Ejecutar ahora'}
            </button>
          </div>
        </div>
      )}

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Scout Satisfactorio"
            value={`${metrics.pct_scout_satisfactory.toFixed(1)}%`}
            subtitle={`${metrics.persons_with_scout_satisfactory.toLocaleString()} de ${metrics.total_persons.toLocaleString()} personas`}
            variant={metrics.pct_scout_satisfactory >= 80 ? 'success' : metrics.pct_scout_satisfactory >= 50 ? 'warning' : 'error'}
          />
          <StatCard
            title="Missing Scout"
            value={metrics.persons_missing_scout.toLocaleString()}
            subtitle={`${((metrics.persons_missing_scout / metrics.total_persons) * 100).toFixed(1)}% del total`}
            variant={metrics.persons_missing_scout < metrics.total_persons * 0.2 ? 'success' : metrics.persons_missing_scout < metrics.total_persons * 0.4 ? 'warning' : 'error'}
          />
          <StatCard
            title="Conflictos"
            value={metrics.conflicts_count.toLocaleString()}
            subtitle="Múltiples scouts por persona"
            variant={metrics.conflicts_count === 0 ? 'success' : metrics.conflicts_count < 50 ? 'warning' : 'error'}
          />
          <StatCard
            title="Backlog Total"
            value={(
              metrics.backlog.a_events_without_scout +
              metrics.backlog.d_scout_in_events_not_in_ledger +
              metrics.backlog.c_legacy
            ).toLocaleString()}
            subtitle="Pendientes por resolver"
            variant="info"
          />
        </div>
      )}

      {/* Backlog by Category */}
      {metrics && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Backlog por Causa</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-lg mb-2">
                Categoría A: Eventos sin Scout
              </h3>
              <p className="text-3xl font-bold text-orange-600 mb-2">
                {metrics.backlog.a_events_without_scout.toLocaleString()}
              </p>
              <p className="text-sm text-gray-600 mb-3">
                Lead events sin scout_id asignado
              </p>
              <button
                onClick={() => {
                  setCategoryFilter('A');
                  router.push(`/scouts/backlog?category=A`);
                }}
                className="text-sm text-blue-600 hover:underline"
              >
                Ver registros →
              </button>
            </div>
            
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-lg mb-2">
                Categoría C: Legacy
              </h3>
              <p className="text-3xl font-bold text-gray-600 mb-2">
                {metrics.backlog.c_legacy.toLocaleString()}
              </p>
              <p className="text-sm text-gray-600 mb-3">
                Personas sin eventos ni scout
              </p>
              <button
                onClick={() => {
                  setCategoryFilter('C');
                  router.push(`/scouts/backlog?category=C`);
                }}
                className="text-sm text-blue-600 hover:underline"
              >
                Ver registros →
              </button>
            </div>
            
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-lg mb-2">
                Categoría D: Scout no Propagado
              </h3>
              <p className="text-3xl font-bold text-blue-600 mb-2">
                {metrics.backlog.d_scout_in_events_not_in_ledger.toLocaleString()}
              </p>
              <p className="text-sm text-gray-600 mb-3">
                Scout en eventos no en lead_ledger
              </p>
              <button
                onClick={() => {
                  setCategoryFilter('D');
                  router.push(`/scouts/backlog?category=D`);
                }}
                className="text-sm text-blue-600 hover:underline"
              >
                Ver registros →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Trends Chart (simple line) */}
      {dailyMetrics && dailyMetrics.daily_metrics.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Tendencias (Últimos 30 días)</h2>
          <div className="h-64 flex items-end gap-2">
            {dailyMetrics.daily_metrics.slice(0, 30).reverse().map((metric, idx) => (
              <div
                key={metric.date}
                className="flex-1 bg-blue-500 hover:bg-blue-600 rounded-t transition-colors relative group"
                style={{ height: `${(metric.pct_satisfactory / 100) * 100}%` }}
                title={`${metric.date}: ${metric.pct_satisfactory.toFixed(1)}%`}
              >
                <div className="hidden group-hover:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                  {new Date(metric.date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })}: {metric.pct_satisfactory.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-sm text-gray-600 text-center">
            % Scout Satisfactorio por día
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/scouts/conflicts"
          className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
        >
          <h3 className="font-semibold mb-2">Ver Conflictos</h3>
          <p className="text-sm text-gray-600">
            Personas con múltiples scouts asignados
          </p>
        </Link>
        
        <Link
          href="/scouts/cobranza-yango"
          className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
        >
          <h3 className="font-semibold mb-2">Cobranza Yango (con Scout)</h3>
          <p className="text-sm text-gray-600">
            Claims de cobranza con información de scout
          </p>
        </Link>
        
        <Link
          href="/scouts/liquidation"
          className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
        >
          <h3 className="font-semibold mb-2">Liquidación Scouts (Base)</h3>
          <p className="text-sm text-gray-600">
            Vista base para liquidación diaria
          </p>
        </Link>
      </div>

      {/* Glossary */}
      <div className="mt-8 bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Glosario</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h3 className="font-semibold mb-2">Scout Satisfactorio</h3>
            <p className="text-gray-600">
              Scout asignado en <code className="bg-gray-200 px-1 rounded">lead_ledger.attributed_scout_id</code> (source-of-truth canónico).
            </p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Conflicto</h3>
            <p className="text-gray-600">
              Persona con múltiples scouts distintos. Requiere revisión manual.
            </p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Legacy</h3>
            <p className="text-gray-600">
              Personas sin eventos ni scout asignado. Registros antiguos sin clasificar.
            </p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Falta Identidad</h3>
            <p className="text-gray-600">
              Registros de <code className="bg-gray-200 px-1 rounded">scouting_daily</code> sin <code className="bg-gray-200 px-1 rounded">identity_links</code>.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

