/**
 * Driver Matrix - Matriz de drivers con milestones M1/M5/M25
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getOpsDriverMatrix, ApiError } from '@/lib/api';
import type { DriverMatrixRow, OpsDriverMatrixResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import CompactMilestoneCell from '@/components/payments/CompactMilestoneCell';
import MilestoneCell from '@/components/payments/MilestoneCell';
import PaymentsLegend from '@/components/payments/PaymentsLegend';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
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
  copy: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
    </svg>
  ),
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function DriverMatrixPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<DriverMatrixRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<OpsDriverMatrixResponse['meta'] | null>(null);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  
  const getValidOriginTag = (value: string | null): string => {
    if (value === 'cabinet' || value === 'fleet_migration' || value === 'unknown') return value;
    return '';
  };

  const [filters, setFilters] = useState(() => ({
    origin_tag: getValidOriginTag(searchParams.get('origin_tag')),
    only_pending: searchParams.get('only_pending') === 'true',
    order: (searchParams.get('order') || 'week_start_desc') as 'week_start_desc' | 'week_start_asc' | 'lead_date_desc' | 'lead_date_asc',
    search: searchParams.get('search') || '',
  }));
  
  const [activeTab, setActiveTab] = useState<'tabla' | 'kpis'>(() => 
    searchParams.get('tab') === 'kpis' ? 'kpis' : 'tabla'
  );
  
  const [limit, setLimit] = useState(() => parseInt(searchParams.get('limit') || '100'));
  const [offset, setOffset] = useState(() => parseInt(searchParams.get('offset') || '0'));
  const [searchDebounced, setSearchDebounced] = useState(filters.search);
  
  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(filters.search), 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  const updateURL = useCallback((newFilters: typeof filters, newLimit: number, newOffset: number, newTab?: string) => {
    const params = new URLSearchParams();
    if (newFilters.origin_tag) params.set('origin_tag', newFilters.origin_tag);
    if (newFilters.only_pending) params.set('only_pending', 'true');
    if (newFilters.order !== 'week_start_desc') params.set('order', newFilters.order);
    if (newFilters.search) params.set('search', newFilters.search);
    if (newLimit !== 100) params.set('limit', newLimit.toString());
    if (newOffset !== 0) params.set('offset', newOffset.toString());
    if (newTab && newTab !== 'tabla') params.set('tab', newTab);
    
    const query = params.toString();
    router.push(`/pagos/driver-matrix${query ? `?${query}` : ''}`, { scroll: false });
  }, [router]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const backendFilters: Record<string, unknown> = { order: filters.order, limit, offset };
        if (filters.origin_tag) backendFilters.origin_tag = filters.origin_tag;
        if (filters.only_pending) backendFilters.only_pending = filters.only_pending;

        const response = await getOpsDriverMatrix(backendFilters);

        let filteredData = response.data;
        if (searchDebounced) {
          const searchLower = searchDebounced.toLowerCase();
          filteredData = response.data.filter((row) =>
            row.driver_name?.toLowerCase().includes(searchLower) ||
            row.driver_id?.toLowerCase().includes(searchLower) ||
            row.person_key?.toLowerCase().includes(searchLower)
          );
        }

        setData(filteredData);
        setMeta(response.meta);
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

    loadData();
  }, [filters.origin_tag, filters.only_pending, filters.order, limit, offset, searchDebounced]);

  const handleFilterChange = (key: keyof typeof filters, value: unknown) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    setOffset(0);
    updateURL(newFilters, limit, 0, activeTab);
  };
  
  const handleTabChange = (tab: 'tabla' | 'kpis') => {
    setActiveTab(tab);
    updateURL(filters, limit, offset, tab);
  };

  const handleResetFilters = () => {
    const newFilters = { origin_tag: '', only_pending: false, order: 'week_start_desc' as const, search: '' };
    setFilters(newFilters);
    setOffset(0);
    setLimit(100);
    updateURL(newFilters, 100, 0);
  };

  const handleExportCSV = () => {
    if (data.length === 0) { alert('No hay datos para exportar'); return; }
    const headers = ['driver_id', 'person_key', 'driver_name', 'lead_date', 'week_start', 'origin_tag', 'connected_flag', 'm1_achieved_flag', 'm1_yango_payment_status', 'm5_achieved_flag', 'm5_yango_payment_status', 'm25_achieved_flag', 'm25_yango_payment_status'];
    const csvRows = [headers.join(','), ...data.map((row) => headers.map((h) => { const v = (row as Record<string, unknown>)[h]; return v == null ? '' : typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v).includes(',') ? `"${v}"` : String(v); }).join(','))];
    const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `driver-matrix-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyAPIURL = () => {
    const params = new URLSearchParams();
    if (filters.origin_tag) params.set('origin_tag', filters.origin_tag);
    if (filters.only_pending) params.set('only_pending', 'true');
    const url = `${API_BASE_URL}/api/v1/ops/payments/driver-matrix${params.toString() ? `?${params}` : ''}`;
    navigator.clipboard.writeText(url);
    alert('URL copiada');
  };

  const getRowKey = (row: DriverMatrixRow): string => `${row.driver_id || row.person_key || 'u'}-${row.week_start || 'nw'}`;
  const toggleRowExpand = (row: DriverMatrixRow) => {
    const key = getRowKey(row);
    setExpandedRows((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Loading inicial
  if (loading && data.length === 0) {
    return <PageLoadingOverlay title="Driver Matrix" subtitle="Cargando matriz de conductores..." />;
  }

  // Calcular KPIs
  const totalDrivers = meta?.total || data.length;
  const m1Achieved = data.filter(r => r.m1_achieved_flag).length;
  const m5Achieved = data.filter(r => r.m5_achieved_flag).length;
  const m25Achieved = data.filter(r => r.m25_achieved_flag).length;
  const unpaidCount = data.filter(r => 
    r.m1_yango_payment_status === 'UNPAID' || 
    r.m5_yango_payment_status === 'UNPAID' || 
    r.m25_yango_payment_status === 'UNPAID'
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Driver Matrix</h1>
          <p className="text-slate-600">Vista detallada de conductores con milestones y estados de pago</p>
        </div>
        <div className="flex items-center gap-3">
          <PaymentsLegend />
          <button onClick={handleCopyAPIURL} className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors text-sm font-medium">
            {Icons.copy} API URL
          </button>
          <button onClick={handleExportCSV} className="flex items-center gap-2 px-4 py-2 bg-[#ef0000] text-white rounded-lg hover:bg-[#cc0000] transition-colors text-sm font-medium">
            {Icons.download} CSV
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
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard title="Total Drivers" value={totalDrivers.toLocaleString()} icon={Icons.users} variant="default" />
        <StatCard title="M1 Achieved" value={m1Achieved.toLocaleString()} subtitle="drivers" icon={Icons.check} variant="info" />
        <StatCard title="M5 Achieved" value={m5Achieved.toLocaleString()} subtitle="drivers" icon={Icons.check} variant="info" />
        <StatCard title="M25 Achieved" value={m25Achieved.toLocaleString()} subtitle="drivers" icon={Icons.check} variant="success" />
        <StatCard title="UNPAID" value={unpaidCount.toLocaleString()} subtitle="pendientes" icon={Icons.alert} variant="warning" />
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Origin Tag</label>
            <select value={filters.origin_tag} onChange={(e) => handleFilterChange('origin_tag', e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ef0000]">
              <option value="">Todos</option>
              <option value="cabinet">cabinet</option>
              <option value="fleet_migration">fleet_migration</option>
              <option value="unknown">unknown</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Solo Pendientes</label>
            <div className="flex items-center h-[38px]">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={filters.only_pending} onChange={(e) => handleFilterChange('only_pending', e.target.checked)} className="h-4 w-4 text-[#ef0000] rounded" />
                <span className="text-sm text-slate-600">UNPAID only</span>
              </label>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Orden</label>
            <select value={filters.order} onChange={(e) => handleFilterChange('order', e.target.value)} className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ef0000]">
              <option value="week_start_desc">Week Start (DESC)</option>
              <option value="week_start_asc">Week Start (ASC)</option>
              <option value="lead_date_desc">Lead Date (DESC)</option>
              <option value="lead_date_asc">Lead Date (ASC)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Buscar</label>
            <input type="text" value={filters.search} onChange={(e) => handleFilterChange('search', e.target.value)} placeholder="Nombre o ID" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ef0000]" />
          </div>
          <div className="flex items-end">
            <button onClick={handleResetFilters} className="w-full px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors">Limpiar</button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="border-b border-slate-200 px-4">
          <nav className="flex gap-4">
            <button onClick={() => handleTabChange('tabla')} className={`py-3 px-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'tabla' ? 'border-[#ef0000] text-[#ef0000]' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              Tabla
            </button>
            <button onClick={() => handleTabChange('kpis')} className={`py-3 px-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'kpis' ? 'border-[#ef0000] text-[#ef0000]' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
              KPIs Detallados
            </button>
          </nav>
        </div>

        {activeTab === 'tabla' ? (
          <div className="relative">
            {loading && (
              <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
                <div className="w-8 h-8 border-3 border-[#ef0000] border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            
            {/* Info */}
            {meta && (
              <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 text-sm text-slate-600">
                Total: <span className="font-semibold">{meta.total}</span> | Mostrando: <span className="font-semibold">{meta.returned}</span> | Página: <span className="font-semibold">{Math.floor(offset / limit) + 1}</span>
              </div>
            )}

            {data.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3 text-slate-400">{Icons.users}</div>
                <p className="text-slate-500 font-medium">Sin datos</p>
                <p className="text-sm text-slate-400">No hay drivers que coincidan</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full table-fixed">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200">
                      <th className="w-10 py-3 px-2"></th>
                      <th className="w-56 text-left py-3 px-3 text-xs font-semibold text-slate-600 uppercase">Driver</th>
                      <th className="w-24 text-left py-3 px-3 text-xs font-semibold text-slate-600 uppercase">Week</th>
                      <th className="w-24 text-center py-3 px-3 text-xs font-semibold text-slate-600 uppercase">Origin</th>
                      <th className="w-36 text-center py-3 px-2 text-xs font-semibold text-slate-600 uppercase">M1</th>
                      <th className="w-36 text-center py-3 px-2 text-xs font-semibold text-slate-600 uppercase">M5</th>
                      <th className="w-36 text-center py-3 px-2 text-xs font-semibold text-slate-600 uppercase">M25</th>
                      <th className="w-20 text-center py-3 px-2 text-xs font-semibold text-slate-600 uppercase">Conect.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.map((row, idx) => {
                      const rowKey = getRowKey(row);
                      const isExpanded = expandedRows[rowKey];
                      const hasInconsistency = row.m5_without_m1_flag || row.m25_without_m5_flag;
                      return (
                        <>
                          <tr key={idx} className={`hover:bg-slate-50/50 transition-colors ${isExpanded ? 'bg-slate-50' : ''}`}>
                            <td className="py-2 px-2">
                              <button onClick={() => toggleRowExpand(row)} className="p-1 hover:bg-slate-200 rounded transition-colors">
                                <span className={`inline-block text-slate-400 text-xs transition-transform ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                              </button>
                            </td>
                            <td className="py-2 px-3">
                              <div className="font-medium text-slate-900 truncate">{row.driver_name || '—'}</div>
                              <div className="text-xs text-slate-500 font-mono truncate">{row.driver_id?.substring(0, 16)}...</div>
                              {hasInconsistency && <Badge variant="warning" className="mt-1 text-xs">⚠</Badge>}
                            </td>
                            <td className="py-2 px-3 text-sm text-slate-600">{row.week_start ? new Date(row.week_start).toLocaleDateString('es-ES') : '—'}</td>
                            <td className="py-2 px-3 text-center"><Badge variant={row.origin_tag === 'cabinet' ? 'info' : 'default'}>{row.origin_tag || '?'}</Badge></td>
                            <td className="py-2 px-2"><CompactMilestoneCell achieved_flag={row.m1_achieved_flag} achieved_date={row.m1_achieved_date} expected_amount_yango={row.m1_expected_amount_yango} yango_payment_status={row.m1_yango_payment_status} window_status={row.m1_window_status} overdue_days={row.m1_overdue_days} label="M1" /></td>
                            <td className="py-2 px-2"><CompactMilestoneCell achieved_flag={row.m5_achieved_flag} achieved_date={row.m5_achieved_date} expected_amount_yango={row.m5_expected_amount_yango} yango_payment_status={row.m5_yango_payment_status} window_status={row.m5_window_status} overdue_days={row.m5_overdue_days} label="M5" /></td>
                            <td className="py-2 px-2"><CompactMilestoneCell achieved_flag={row.m25_achieved_flag} achieved_date={row.m25_achieved_date} expected_amount_yango={row.m25_expected_amount_yango} yango_payment_status={row.m25_yango_payment_status} window_status={row.m25_window_status} overdue_days={row.m25_overdue_days} label="M25" /></td>
                            <td className="py-2 px-2 text-center">{row.connected_flag ? <span className="text-green-500">✓</span> : <span className="text-slate-400">—</span>}</td>
                          </tr>
                          {isExpanded && (
                            <tr key={`${idx}-exp`} className="bg-slate-50">
                              <td colSpan={8} className="px-4 pb-4 pt-2 border-t border-slate-100">
                                <div className="grid grid-cols-3 gap-6">
                                  <div><h4 className="text-sm font-semibold text-slate-700 mb-2">M1</h4><MilestoneCell achieved_flag={row.m1_achieved_flag} achieved_date={row.m1_achieved_date} expected_amount_yango={row.m1_expected_amount_yango} yango_payment_status={row.m1_yango_payment_status} window_status={row.m1_window_status} overdue_days={row.m1_overdue_days} /></div>
                                  <div><h4 className="text-sm font-semibold text-slate-700 mb-2">M5</h4><MilestoneCell achieved_flag={row.m5_achieved_flag} achieved_date={row.m5_achieved_date} expected_amount_yango={row.m5_expected_amount_yango} yango_payment_status={row.m5_yango_payment_status} window_status={row.m5_window_status} overdue_days={row.m5_overdue_days} /></div>
                                  <div><h4 className="text-sm font-semibold text-slate-700 mb-2">M25</h4><MilestoneCell achieved_flag={row.m25_achieved_flag} achieved_date={row.m25_achieved_date} expected_amount_yango={row.m25_expected_amount_yango} yango_payment_status={row.m25_yango_payment_status} window_status={row.m25_window_status} overdue_days={row.m25_overdue_days} /></div>
                                </div>
                                <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-4 gap-4 text-sm">
                                  <div><span className="font-medium text-slate-500">Driver ID:</span> <span className="text-slate-700 font-mono text-xs break-all">{row.driver_id || '—'}</span></div>
                                  <div><span className="font-medium text-slate-500">Person Key:</span> <span className="text-slate-700 font-mono text-xs break-all">{row.person_key || '—'}</span></div>
                                  <div><span className="font-medium text-slate-500">Lead Date:</span> <span className="text-slate-700">{row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—'}</span></div>
                                  <div><span className="font-medium text-slate-500">Connected:</span> <span className="text-slate-700">{row.connected_date ? new Date(row.connected_date).toLocaleDateString('es-ES') : '—'}</span></div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {meta && data.length > 0 && (
              <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-slate-600">Mostrando {offset + 1} - {Math.min(offset + limit, meta.total)} de {meta.total}</span>
                  <select value={limit} onChange={(e) => { const nl = parseInt(e.target.value); setLimit(nl); setOffset(0); updateURL(filters, nl, 0, activeTab); }} className="px-2 py-1 text-sm border border-slate-200 rounded-lg">
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => { const no = Math.max(0, offset - limit); setOffset(no); updateURL(filters, limit, no, activeTab); }} disabled={offset === 0} className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed">← Anterior</button>
                  <span className="text-sm text-slate-600">Pág {Math.floor(offset / limit) + 1} de {Math.ceil(meta.total / limit)}</span>
                  <button onClick={() => { const no = offset + limit; setOffset(no); updateURL(filters, limit, no, activeTab); }} disabled={offset + limit >= meta.total} className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed">Siguiente →</button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">KPIs de Conversión</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-3">Funnel (C1)</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>Reg. Incompleto</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'registered_incomplete').length}</span></div>
                  <div className="flex justify-between"><span>Reg. Completo</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'registered_complete').length}</span></div>
                  <div className="flex justify-between"><span>Conectado</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'connected_no_trips').length}</span></div>
                  <div className="flex justify-between"><span>M1</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m1').length}</span></div>
                  <div className="flex justify-between"><span>M5</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m5').length}</span></div>
                  <div className="flex justify-between"><span>M25</span><span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m25').length}</span></div>
                </div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-green-800 mb-3">Milestones Achieved</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>M1 Achieved</span><span className="font-semibold">{m1Achieved}</span></div>
                  <div className="flex justify-between"><span>M5 Achieved</span><span className="font-semibold">{m5Achieved}</span></div>
                  <div className="flex justify-between"><span>M25 Achieved</span><span className="font-semibold">{m25Achieved}</span></div>
                </div>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-3">Achieved sin Claim</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>M1 sin claim</span><span className="font-semibold">{data.filter(r => r.m1_achieved_flag && !r.m1_yango_payment_status).length}</span></div>
                  <div className="flex justify-between"><span>M5 sin claim</span><span className="font-semibold">{data.filter(r => r.m5_achieved_flag && !r.m5_yango_payment_status).length}</span></div>
                  <div className="flex justify-between"><span>M25 sin claim</span><span className="font-semibold">{data.filter(r => r.m25_achieved_flag && !r.m25_yango_payment_status).length}</span></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DriverMatrixPage() {
  return (
    <Suspense fallback={<PageLoadingOverlay title="Driver Matrix" subtitle="Cargando..." />}>
      <DriverMatrixPageContent />
    </Suspense>
  );
}
