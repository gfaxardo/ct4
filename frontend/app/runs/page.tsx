/**
 * Runs - Historial de ejecuciones de identidad
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getIdentityRuns, ApiError } from '@/lib/api';
import type { IdentityRunRow, IngestionRunStatus, IngestionJobType } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Pagination from '@/components/Pagination';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  play: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  x: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  alert: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  database: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
};

export default function RunsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<IdentityRunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    status: string;
    job_type: string;
  }>({
    status: '',
    job_type: 'identity_run',
  });
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [total, setTotal] = useState(0);

  async function loadRuns() {
    try {
      setLoading(true);
      setError(null);

      const params: {
        limit: number;
        offset: number;
        status?: IngestionRunStatus;
        job_type?: IngestionJobType;
      } = { limit, offset };

      if (filters.status) {
        params.status = filters.status as IngestionRunStatus;
      }
      if (filters.job_type) {
        params.job_type = filters.job_type as IngestionJobType;
      }

      const data = await getIdentityRuns(params);
      setRuns(data.items);
      setTotal(data.total);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido');
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  }, [filters, offset, limit]);

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setOffset(0);
  };

  const handleClearFilters = () => {
    setFilters({ status: '', job_type: 'identity_run' });
    setOffset(0);
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeVariant = (status: IngestionRunStatus): 'success' | 'warning' | 'error' | 'info' => {
    switch (status) {
      case 'COMPLETED': return 'success';
      case 'RUNNING': return 'info';
      case 'FAILED': return 'error';
      default: return 'warning';
    }
  };

  if (loading && runs.length === 0) {
    return <PageLoadingOverlay title="Auditoría" subtitle="Cargando historial de ejecuciones..." />;
  }

  // Calcular KPIs
  const completedCount = runs.filter(r => r.status === 'COMPLETED').length;
  const failedCount = runs.filter(r => r.status === 'FAILED').length;
  const runningCount = runs.filter(r => r.status === 'RUNNING').length;

  // Última corrida
  const lastRun = runs[0];
  const lastRunStats = lastRun?.stats;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Historial de Ejecuciones</h1>
          <p className="text-slate-600">Corridas del motor de identidad y matching</p>
        </div>
        <button
          onClick={loadRuns}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-[#ef0000] text-white rounded-lg hover:bg-[#cc0000] transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : Icons.refresh}
          Actualizar
        </button>
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

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Ejecuciones"
          value={total.toLocaleString()}
          subtitle="en el sistema"
          icon={Icons.database}
          variant="default"
        />
        <StatCard
          title="Completadas"
          value={completedCount.toLocaleString()}
          subtitle="en esta página"
          icon={Icons.check}
          variant="success"
        />
        <StatCard
          title="Fallidas"
          value={failedCount.toLocaleString()}
          subtitle="requieren revisión"
          icon={Icons.x}
          variant="error"
        />
        <StatCard
          title="En Ejecución"
          value={runningCount.toLocaleString()}
          subtitle="activas ahora"
          icon={Icons.play}
          variant="info"
        />
      </div>

      {/* Última corrida stats */}
      {lastRun && lastRunStats && (
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 rounded-xl p-5 text-white">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-slate-300">Última Corrida (#{lastRun.id})</p>
              <p className="text-lg font-semibold">{formatDate(lastRun.started_at)}</p>
            </div>
            <Badge variant={getStatusBadgeVariant(lastRun.status)}>
              {lastRun.status}
            </Badge>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Cabinet Procesados</p>
              <p className="text-xl font-bold">{lastRunStats.cabinet_leads?.processed ?? '—'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Cabinet Matched</p>
              <p className="text-xl font-bold text-emerald-400">{lastRunStats.cabinet_leads?.matched ?? '—'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Cabinet Unmatched</p>
              <p className="text-xl font-bold text-red-400">{lastRunStats.cabinet_leads?.unmatched ?? '—'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Scouting Procesados</p>
              <p className="text-xl font-bold">{lastRunStats.scouting_daily?.processed ?? '—'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Scouting Matched</p>
              <p className="text-xl font-bold text-emerald-400">{lastRunStats.scouting_daily?.matched ?? '—'}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Scouting Unmatched</p>
              <p className="text-xl font-bold text-red-400">{lastRunStats.scouting_daily?.unmatched ?? '—'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Estado</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="RUNNING">En Ejecución</option>
              <option value="COMPLETED">Completado</option>
              <option value="FAILED">Fallido</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Tipo de Job</label>
            <select
              value={filters.job_type}
              onChange={(e) => handleFilterChange('job_type', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="identity_run">Identity Run</option>
              <option value="drivers_index_refresh">Drivers Index Refresh</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleClearFilters}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              Limpiar filtros
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="w-8 h-8 border-3 border-[#ef0000] border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {runs.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3 text-slate-400">
              {Icons.database}
            </div>
            <p className="text-slate-600 font-medium">No hay ejecuciones registradas</p>
            <p className="text-sm text-slate-500 mt-1">Ejecuta el motor de identidad para ver registros</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-16">ID</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Inicio</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Fin</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-28">Estado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Tipo</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-20">Incr.</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Cabinet</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Scouting</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className="hover:bg-slate-50/50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/runs/${run.id}`)}
                  >
                    <td className="py-3 px-4 text-sm font-mono text-[#ef0000] hover:underline">
                      #{run.id}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {formatDate(run.started_at)}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {formatDate(run.completed_at)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={getStatusBadgeVariant(run.status)}>
                        {run.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <code className="px-1.5 py-0.5 bg-slate-100 rounded text-xs">
                        {run.job_type}
                      </code>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${
                        run.incremental 
                          ? 'bg-emerald-100 text-emerald-700' 
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {run.incremental ? '✓' : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2 text-xs font-mono">
                        <span className="text-slate-600">{run.stats?.cabinet_leads?.processed ?? '—'}</span>
                        <span className="text-emerald-600">+{run.stats?.cabinet_leads?.matched ?? 0}</span>
                        <span className="text-red-500">-{run.stats?.cabinet_leads?.unmatched ?? 0}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2 text-xs font-mono">
                        <span className="text-slate-600">{run.stats?.scouting_daily?.processed ?? '—'}</span>
                        <span className="text-emerald-600">+{run.stats?.scouting_daily?.matched ?? 0}</span>
                        <span className="text-red-500">-{run.stats?.scouting_daily?.unmatched ?? 0}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {runs.length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 bg-slate-50">
            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
