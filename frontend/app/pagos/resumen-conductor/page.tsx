/**
 * Resumen por Conductor - Matriz de drivers con milestones M1/M5/M25
 * Diseño moderno consistente con el resto del sistema
 * 
 * Objetivo: "¿Qué estado tienen los pagos por conductor y milestone?"
 */

'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getDriverMatrix, exportDriverMatrix, ApiError } from '@/lib/api';
import type { DriverMatrixResponse, DriverMatrixRow } from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import PaymentsLegend from '@/components/payments/PaymentsLegend';
import MilestoneCell from '@/components/payments/MilestoneCell';
import { PageLoadingOverlay } from '@/components/Skeleton';

// ============================================================================
// ICONS
// ============================================================================

const Icons = {
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  money: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
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
  download: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
};

function ResumenConductorPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<DriverMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filtros desde URL o defaults
  const [filters, setFilters] = useState({
    week_from: searchParams.get('week_from') || '',
    week_to: searchParams.get('week_to') || '',
    search: searchParams.get('search') || '',
    only_pending: searchParams.get('only_pending') === 'true',
  });
  
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '50', 10));
  
  // Debounce para search
  const [searchDebounce, setSearchDebounce] = useState<NodeJS.Timeout | null>(null);

  // Actualizar URL cuando cambian filtros
  const updateURL = useCallback((newFilters: typeof filters, newPage: number, newLimit: number) => {
    const params = new URLSearchParams();
    if (newFilters.week_from) params.set('week_from', newFilters.week_from);
    if (newFilters.week_to) params.set('week_to', newFilters.week_to);
    if (newFilters.search) params.set('search', newFilters.search);
    if (newFilters.only_pending) params.set('only_pending', 'true');
    if (newPage > 1) params.set('page', newPage.toString());
    if (newLimit !== 50) params.set('limit', newLimit.toString());
    
    router.push(`/pagos/resumen-conductor?${params.toString()}`);
  }, [router]);

  // Cargar datos
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await getDriverMatrix({
          week_from: filters.week_from || undefined,
          week_to: filters.week_to || undefined,
          search: filters.search || undefined,
          only_pending: filters.only_pending || undefined,
          page,
          limit,
        });

        setData(response);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Error ${err.status}: ${err.detail || err.message}`);
        } else {
          setError('Error desconocido al cargar datos');
        }
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [filters, page, limit]);

  // Handler para cambios en filtros con debounce en search
  const handleFilterChange = useCallback((name: string, value: string | boolean) => {
    const newFilters = { ...filters, [name]: value };
    setFilters(newFilters);
    setPage(1);
    
    if (name === 'search') {
      if (searchDebounce) clearTimeout(searchDebounce);
      const timeout = setTimeout(() => {
        updateURL(newFilters, 1, limit);
      }, 300);
      setSearchDebounce(timeout);
    } else {
      updateURL(newFilters, 1, limit);
    }
  }, [filters, limit, updateURL, searchDebounce]);

  // Handler para limpiar filtros
  const handleResetFilters = useCallback(() => {
    const emptyFilters = {
      week_from: '',
      week_to: '',
      search: '',
      only_pending: false,
    };
    setFilters(emptyFilters);
    setPage(1);
    updateURL(emptyFilters, 1, limit);
  }, [limit, updateURL]);

  // Handler para export CSV
  const handleExportCSV = useCallback(async () => {
    try {
      const blob = await exportDriverMatrix({
        week_from: filters.week_from || undefined,
        week_to: filters.week_to || undefined,
        search: filters.search || undefined,
        only_pending: filters.only_pending || undefined,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `driver_matrix_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Error al exportar: ${err.detail || err.message}`);
      } else {
        alert('Error desconocido al exportar');
      }
    }
  }, [filters]);

  // Loading inicial
  if (loading && !data) {
    return <PageLoadingOverlay title="Resumen Conductor" subtitle="Cargando matriz de conductores..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Resumen por Conductor</h1>
          <p className="text-slate-600">Matriz de drivers con milestones M1/M5/M25 y estados de pago</p>
        </div>
        <div className="flex items-center gap-3">
          <PaymentsLegend />
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors text-sm font-medium"
          >
            {Icons.download}
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="text-red-500">{Icons.alert}</div>
            <div>
              <p className="font-medium text-red-800">Error al cargar datos</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* KPIs */}
      {data && (
        <div className="space-y-6">
          {/* KPIs de Claims */}
          <div>
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
              📊 KPIs de Claims (C3/C4)
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <StatCard
                title="Drivers"
                value={data.totals.drivers.toLocaleString()}
                icon={Icons.users}
                variant="default"
              />
              <StatCard
                title="Expected Yango"
                value={`S/ ${(Number(data.totals.expected_yango_sum) || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
                subtitle="donde existe claim"
                icon={Icons.money}
                variant="info"
              />
              <StatCard
                title="Paid"
                value={`S/ ${(Number(data.totals.paid_sum) || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
                subtitle="PAID/PAID_MISAPPLIED"
                icon={Icons.check}
                variant="success"
              />
              <StatCard
                title="Receivable"
                value={`S/ ${(Number(data.totals.receivable_sum) || 0).toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
                subtitle="Expected - Paid"
                icon={Icons.money}
                variant="warning"
              />
              <StatCard
                title="Expired"
                value={data.totals.expired_count.toLocaleString()}
                subtitle="claims vencidos"
                icon={Icons.clock}
                variant="error"
              />
              <StatCard
                title="In Window"
                value={data.totals.in_window_count.toLocaleString()}
                subtitle="claims en ventana"
                icon={Icons.clock}
                variant="success"
              />
            </div>
          </div>

          {/* KPIs de Actividad */}
          <div>
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
              🚗 KPIs de Actividad (C1 - Trips)
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <StatCard
                title="Achieved M1"
                value={(data.totals.achieved_m1_count || 0).toLocaleString()}
                subtitle="drivers con M1"
                icon={Icons.check}
                variant="info"
              />
              <StatCard
                title="Achieved M5"
                value={(data.totals.achieved_m5_count || 0).toLocaleString()}
                subtitle="drivers con M5"
                icon={Icons.check}
                variant="info"
              />
              <StatCard
                title="Achieved M25"
                value={(data.totals.achieved_m25_count || 0).toLocaleString()}
                subtitle="drivers con M25"
                icon={Icons.check}
                variant="success"
              />
              <StatCard
                title="M1 sin Claim"
                value={(data.totals.achieved_m1_without_claim_count || 0).toLocaleString()}
                subtitle="achieved sin claim"
                icon={Icons.alert}
                variant="warning"
              />
              <StatCard
                title="M5 sin Claim"
                value={(data.totals.achieved_m5_without_claim_count || 0).toLocaleString()}
                subtitle="achieved sin claim"
                icon={Icons.alert}
                variant="warning"
              />
              <StatCard
                title="M25 sin Claim"
                value={(data.totals.achieved_m25_without_claim_count || 0).toLocaleString()}
                subtitle="achieved sin claim"
                icon={Icons.alert}
                variant="warning"
              />
            </div>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Semana Desde</label>
            <input
              type="date"
              value={filters.week_from}
              onChange={(e) => handleFilterChange('week_from', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Semana Hasta</label>
            <input
              type="date"
              value={filters.week_to}
              onChange={(e) => handleFilterChange('week_to', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Buscar</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="driver_id, person_key, nombre"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Solo Pendientes</label>
            <div className="flex items-center h-[38px]">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.only_pending}
                  onChange={(e) => handleFilterChange('only_pending', e.target.checked)}
                  className="h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-slate-300 rounded"
                />
                <span className="text-sm text-slate-600">Mostrar solo pendientes</span>
              </label>
            </div>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleResetFilters}
              className="w-full px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
            >
              Limpiar
            </button>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading && data && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Driver</th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Origen</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Conectado</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">M1</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">M5</th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">M25</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(!data?.rows || data.rows.length === 0) ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                        {Icons.users}
                      </div>
                      <p className="text-slate-500 font-medium">Sin datos</p>
                      <p className="text-sm text-slate-400">No hay drivers que coincidan con los filtros</p>
                    </div>
                  </td>
                </tr>
              ) : (
                data.rows.map((row: DriverMatrixRow, idx: number) => (
                  <tr key={`${row.driver_id}-${idx}`} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-900">{row.driver_name || 'Sin nombre'}</div>
                      <div className="text-xs text-slate-500 font-mono">
                        {row.driver_id ? row.driver_id.substring(0, 16) + '...' : '—'}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={row.origin_tag === 'cabinet' ? 'info' : 'default'}>
                        {row.origin_tag || '—'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {row.connected_flag ? (
                        <div className="flex items-center justify-center gap-1.5">
                          <span className="text-green-500">✓</span>
                          {row.connected_date && (
                            <span className="text-xs text-slate-500">
                              {new Date(row.connected_date).toLocaleDateString('es-ES')}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <MilestoneCell
                        achieved_flag={row.m1_achieved_flag}
                        achieved_date={row.m1_achieved_date}
                        expected_amount_yango={row.m1_expected_amount_yango}
                        yango_payment_status={row.m1_yango_payment_status}
                        window_status={row.m1_window_status}
                        overdue_days={row.m1_overdue_days}
                      />
                    </td>
                    <td className="py-3 px-4">
                      <MilestoneCell
                        achieved_flag={row.m5_achieved_flag}
                        achieved_date={row.m5_achieved_date}
                        expected_amount_yango={row.m5_expected_amount_yango}
                        yango_payment_status={row.m5_yango_payment_status}
                        window_status={row.m5_window_status}
                        overdue_days={row.m5_overdue_days}
                      />
                    </td>
                    <td className="py-3 px-4">
                      <MilestoneCell
                        achieved_flag={row.m25_achieved_flag}
                        achieved_date={row.m25_achieved_date}
                        expected_amount_yango={row.m25_expected_amount_yango}
                        yango_payment_status={row.m25_yango_payment_status}
                        window_status={row.m25_window_status}
                        overdue_days={row.m25_overdue_days}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.rows.length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-600">
                Mostrando {((page - 1) * limit) + 1} - {Math.min(page * limit, data.meta.total_rows)} de {data.meta.total_rows}
              </span>
              <select
                value={limit}
                onChange={(e) => {
                  const newLimit = parseInt(e.target.value, 10);
                  setLimit(newLimit);
                  setPage(1);
                  updateURL(filters, 1, newLimit);
                }}
                className="px-2 py-1 text-sm border border-slate-200 rounded-lg"
              >
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
                <option value="500">500</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const newPage = Math.max(1, page - 1);
                  setPage(newPage);
                  updateURL(filters, newPage, limit);
                }}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                ← Anterior
              </button>
              <span className="text-sm text-slate-600">
                Página {page} de {Math.ceil(data.meta.total_rows / limit)}
              </span>
              <button
                onClick={() => {
                  const newPage = Math.min(Math.ceil(data.meta.total_rows / limit), page + 1);
                  setPage(newPage);
                  updateURL(filters, newPage, limit);
                }}
                disabled={page >= Math.ceil(data.meta.total_rows / limit)}
                className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ResumenConductorPage() {
  return (
    <Suspense fallback={<PageLoadingOverlay title="Resumen Conductor" subtitle="Cargando..." />}>
      <ResumenConductorPageContent />
    </Suspense>
  );
}
