/**
 * Yango - Cobranza (Cabinet Financial 14d)
 * Fuente de verdad financiera para CABINET
 * 
 * Objetivo: "¿Qué conductores generan pago de Yango y cuánto nos deben?"
 */

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  getCabinetFinancial14d,
  exportCabinetFinancial14dCSV,
  getFunnelGapMetrics,
  getCobranzaYangoScoutAttributionMetrics,
  getCobranzaYangoWeeklyKpis,
  getIdentityGaps,
  getIdentityGapAlerts,
  ApiError,
} from '@/lib/api';
import type { FunnelGapMetrics, ScoutAttributionMetricsResponse, WeeklyKpisResponse, IdentityGapResponse, IdentityGapAlertsResponse } from '@/lib/api';
import type {
  CabinetFinancialResponse,
  CabinetFinancialRow,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';
import Tabs, { TabPanel } from '@/components/Tabs';
import CabinetLimboSection from '@/components/CabinetLimboSection';
import CabinetClaimsGapSection from '@/components/CabinetClaimsGapSection';
import { StatCardSkeleton, TableSkeleton, LoadingSpinner } from '@/components/Skeleton';

// Icons for tabs
const DashboardIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const CalendarIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

const TableIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const RecoveryIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

export default function CobranzaYangoPage() {
  const router = useRouter();
  const [data, setData] = useState<CabinetFinancialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    only_with_debt: true,
    reached_milestone: '',
    scout_id: '',
    week_start: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);
  const [exporting, setExporting] = useState(false);
  const [funnelGap, setFunnelGap] = useState<FunnelGapMetrics | null>(null);
  const [loadingGap, setLoadingGap] = useState(true);
  const [scoutMetrics, setScoutMetrics] = useState<ScoutAttributionMetricsResponse | null>(null);
  const [loadingScoutMetrics, setLoadingScoutMetrics] = useState(true);
  const [weeklyKpis, setWeeklyKpis] = useState<WeeklyKpisResponse | null>(null);
  const [loadingWeeklyKpis, setLoadingWeeklyKpis] = useState(true);
  const [identityGaps, setIdentityGaps] = useState<IdentityGapResponse | null>(null);
  const [loadingIdentityGaps, setLoadingIdentityGaps] = useState(true);
  const [identityGapAlerts, setIdentityGapAlerts] = useState<IdentityGapAlertsResponse | null>(null);
  const [loadingIdentityGapAlerts, setLoadingIdentityGapAlerts] = useState(true);
  const [showAlerts, setShowAlerts] = useState(false);
  
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedFilters(filters);
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const response = await getCabinetFinancial14d({
          only_with_debt: debouncedFilters.only_with_debt,
          reached_milestone: debouncedFilters.reached_milestone ? debouncedFilters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
          scout_id: debouncedFilters.scout_id ? parseInt(debouncedFilters.scout_id) : undefined,
          week_start: debouncedFilters.week_start || undefined,
          limit,
          offset,
          include_summary: true,
          use_materialized: true,
        });
        setData(response);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar cobranza Yango');
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
  }, [debouncedFilters, offset, limit]);

  useEffect(() => {
    async function loadFunnelGap() {
      try {
        setLoadingGap(true);
        const gapData = await getFunnelGapMetrics();
        setFunnelGap(gapData);
      } catch (err) {
        console.error('Error cargando métricas del gap:', err);
      } finally {
        setLoadingGap(false);
      }
    }
    loadFunnelGap();
  }, []);

  useEffect(() => {
    async function loadScoutMetrics() {
      try {
        setLoadingScoutMetrics(true);
        const metrics = await getCobranzaYangoScoutAttributionMetrics({
          only_with_debt: debouncedFilters.only_with_debt,
          reached_milestone: debouncedFilters.reached_milestone ? debouncedFilters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
          scout_id: debouncedFilters.scout_id ? parseInt(debouncedFilters.scout_id) : undefined,
          use_materialized: true,
        });
        setScoutMetrics(metrics);
      } catch (err) {
        console.error('Error cargando métricas de scout:', err);
      } finally {
        setLoadingScoutMetrics(false);
      }
    }
    loadScoutMetrics();
  }, [debouncedFilters]);

  useEffect(() => {
    async function loadWeeklyKpis() {
      try {
        setLoadingWeeklyKpis(true);
        const kpis = await getCobranzaYangoWeeklyKpis({
          only_with_debt: debouncedFilters.only_with_debt,
          reached_milestone: debouncedFilters.reached_milestone ? debouncedFilters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
          scout_id: debouncedFilters.scout_id ? parseInt(debouncedFilters.scout_id) : undefined,
          limit_weeks: 52,
          use_materialized: true,
        });
        setWeeklyKpis(kpis);
      } catch (err) {
        console.error('Error cargando KPIs semanales:', err);
      } finally {
        setLoadingWeeklyKpis(false);
      }
    }
    loadWeeklyKpis();
  }, [debouncedFilters]);

  useEffect(() => {
    async function loadIdentityGaps() {
      try {
        setLoadingIdentityGaps(true);
        const gaps = await getIdentityGaps({ page: 1, page_size: 100 });
        setIdentityGaps(gaps);
      } catch (err) {
        console.error('Error cargando brechas de identidad:', err);
      } finally {
        setLoadingIdentityGaps(false);
      }
    }
    loadIdentityGaps();
    const interval = setInterval(loadIdentityGaps, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    async function loadIdentityGapAlerts() {
      try {
        setLoadingIdentityGapAlerts(true);
        const alerts = await getIdentityGapAlerts();
        setIdentityGapAlerts(alerts);
      } catch (err) {
        console.error('Error cargando alertas de brechas:', err);
      } finally {
        setLoadingIdentityGapAlerts(false);
      }
    }
    loadIdentityGapAlerts();
    const interval = setInterval(loadIdentityGapAlerts, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleExport = async () => {
    try {
      setExporting(true);
      setError(null);
      const blob = await exportCabinetFinancial14dCSV({
        only_with_debt: debouncedFilters.only_with_debt,
        reached_milestone: debouncedFilters.reached_milestone ? debouncedFilters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
        week_start: debouncedFilters.week_start || undefined,
        use_materialized: true,
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cabinet_financial_14d_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error al exportar: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido al exportar');
      }
    } finally {
      setExporting(false);
    }
  };

  const filterFields = [
    { name: 'only_with_debt', label: 'Solo con deuda', type: 'checkbox' as const },
    {
      name: 'reached_milestone',
      label: 'Milestone alcanzado',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: 'm1', label: 'Solo M1 (1-4 viajes)' },
        { value: 'm5', label: 'M5 pero no M25 (5-24 viajes)' },
        { value: 'm25', label: 'M25 alcanzado (25+ viajes)' },
      ],
    },
    { name: 'scout_id', label: 'Scout ID', type: 'number' as const },
    {
      name: 'week_start',
      label: 'Semana',
      type: 'select' as const,
      options: weeklyKpis?.weeks 
        ? [
            { value: '', label: 'Todas' },
            ...weeklyKpis.weeks.map(w => ({
              value: w.week_start,
              label: `${new Date(w.week_start).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })} (${w.total_rows} drivers)`
            }))
          ]
        : [{ value: '', label: 'Todas' }],
    },
  ];

  const columns = useMemo(() => [
    {
      key: 'driver_name',
      header: 'Conductor',
      render: (row: CabinetFinancialRow) =>
        row.driver_name ? (
          <div>
            <div className="font-medium text-slate-900">{row.driver_name}</div>
            <div className="text-xs text-slate-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-cyan-600 hover:text-cyan-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : '—'}
            </div>
          </div>
        ) : (
          <div>
            <div className="text-slate-400">N/A</div>
            <div className="text-xs text-slate-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-cyan-600 hover:text-cyan-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : '—'}
            </div>
          </div>
        ),
    },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: CabinetFinancialRow) => (
        <div>
          <div className="text-slate-700">{row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—'}</div>
          {row.iso_week && <div className="text-xs text-slate-500">Semana: {row.iso_week}</div>}
        </div>
      ),
    },
    {
      key: 'connected_flag',
      header: 'Conectado',
      render: (row: CabinetFinancialRow) => (
        <Badge variant={row.connected_flag ? 'success' : 'warning'}>{row.connected_flag ? 'Sí' : 'No'}</Badge>
      ),
    },
    {
      key: 'total_trips_14d',
      header: 'Viajes 14d',
      render: (row: CabinetFinancialRow) => <span className="font-medium">{row.total_trips_14d || 0}</span>,
    },
    {
      key: 'milestones',
      header: 'Milestones',
      render: (row: CabinetFinancialRow) => {
        const milestones = [];
        if (row.reached_m1_14d) milestones.push('M1');
        if (row.reached_m5_14d) milestones.push('M5');
        if (row.reached_m25_14d) milestones.push('M25');
        if (milestones.length === 0) return <span className="text-slate-400">—</span>;
        return (
          <div className="flex gap-1 flex-wrap">
            {milestones.map((m) => <Badge key={m} variant="info">{m}</Badge>)}
          </div>
        );
      },
    },
    {
      key: 'scout',
      header: 'Scout',
      render: (row: CabinetFinancialRow) => {
        if (row.scout_id) {
          const qualityBadgeVariant = 
            row.scout_quality_bucket === 'SATISFACTORY_LEDGER' ? 'success' :
            row.scout_quality_bucket === 'EVENTS_ONLY' ? 'warning' :
            row.scout_quality_bucket === 'MIGRATIONS_ONLY' ? 'warning' :
            row.scout_quality_bucket === 'SCOUTING_DAILY_ONLY' ? 'default' :
            row.scout_quality_bucket === 'CABINET_PAYMENTS_ONLY' ? 'default' :
            'error';
          return (
            <div className="flex flex-col gap-1">
              <Badge variant={qualityBadgeVariant}>{row.scout_name || `Scout ${row.scout_id}`}</Badge>
              {row.scout_id && <div className="text-xs text-slate-500">ID: {row.scout_id}</div>}
            </div>
          );
        }
        return <Badge variant="error">Sin scout</Badge>;
      },
    },
    {
      key: 'expected_total_yango',
      header: 'Esperado',
      render: (row: CabinetFinancialRow) => (
        <span className="font-medium text-slate-700">S/ {(Number(row.expected_total_yango) || 0).toFixed(2)}</span>
      ),
    },
    {
      key: 'total_paid_yango',
      header: 'Pagado',
      render: (row: CabinetFinancialRow) => (
        <span className="font-medium text-emerald-600">S/ {(Number(row.total_paid_yango) || 0).toFixed(2)}</span>
      ),
    },
    {
      key: 'amount_due_yango',
      header: 'Deuda',
      render: (row: CabinetFinancialRow) => {
        const amount = Number(row.amount_due_yango) || 0;
        return (
          <span className={amount > 0 ? 'text-rose-600 font-semibold' : 'text-emerald-600 font-medium'}>
            S/ {amount.toFixed(2)}
          </span>
        );
      },
    },
    {
      key: 'claims_status',
      header: 'Estado Claims',
      render: (row: CabinetFinancialRow) => {
        const claims = [];
        if (row.reached_m1_14d) {
          claims.push(
            <div key="m1" className="text-xs flex items-center gap-1">
              <span className="text-slate-500">M1:</span>
              <Badge variant={row.claim_m1_exists ? (row.claim_m1_paid ? 'success' : 'warning') : 'error'} size="sm">
                {row.claim_m1_exists ? (row.claim_m1_paid ? 'Pagado' : 'Pendiente') : 'Sin claim'}
              </Badge>
            </div>
          );
        }
        if (row.reached_m5_14d) {
          claims.push(
            <div key="m5" className="text-xs flex items-center gap-1">
              <span className="text-slate-500">M5:</span>
              <Badge variant={row.claim_m5_exists ? (row.claim_m5_paid ? 'success' : 'warning') : 'error'} size="sm">
                {row.claim_m5_exists ? (row.claim_m5_paid ? 'Pagado' : 'Pendiente') : 'Sin claim'}
              </Badge>
            </div>
          );
        }
        if (row.reached_m25_14d) {
          claims.push(
            <div key="m25" className="text-xs flex items-center gap-1">
              <span className="text-slate-500">M25:</span>
              <Badge variant={row.claim_m25_exists ? (row.claim_m25_paid ? 'success' : 'warning') : 'error'} size="sm">
                {row.claim_m25_exists ? (row.claim_m25_paid ? 'Pagado' : 'Pendiente') : 'Sin claim'}
              </Badge>
            </div>
          );
        }
        if (claims.length === 0) return <span className="text-slate-400">—</span>;
        return <div className="flex flex-col gap-1">{claims}</div>;
      },
    },
  ], [router]);

  const handleWeekClick = useCallback((weekStart: string) => {
    setFilters(prev => ({ ...prev, week_start: weekStart }));
  }, []);

  const handleClearWeekFilter = useCallback(() => {
    setFilters(prev => ({ ...prev, week_start: '' }));
  }, []);

  // Tabs configuration
  const tabs = [
    { id: 'resumen', label: 'Resumen', icon: <DashboardIcon /> },
    { id: 'semanal', label: 'KPIs Semanales', icon: <CalendarIcon />, badge: weeklyKpis?.weeks?.length },
    { id: 'conductores', label: 'Conductores', icon: <TableIcon />, badge: data?.meta?.total },
    { id: 'recovery', label: 'Recovery & Gaps', icon: <RecoveryIcon />, badge: identityGaps?.totals?.unresolved },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Cobranza Yango - Cabinet Financial 14d</h1>
          <p className="text-slate-500 mt-1">Fuente de verdad financiera para CABINET. Ventana de 14 días desde lead_date.</p>
        </div>
        <a
          href="/docs/RESUMEN_EJECUTIVO_COBRANZA_YANGO.md"
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-secondary gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          Ver Resumen Ejecutivo
        </a>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>{error}</p>
        </div>
      )}

      {/* Tabs */}
      <Tabs tabs={tabs} defaultTab="resumen">
        {(activeTab) => (
          <>
            {/* TAB: Resumen */}
            <TabPanel id="resumen" activeTab={activeTab}>
              <div className="space-y-6">
                {/* Métricas del Gap del Embudo */}
                {loadingGap ? (
                  <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-5 h-5 bg-amber-200 rounded animate-pulse" />
                      <div className="h-6 w-48 bg-amber-200 rounded animate-pulse" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <StatCardSkeleton />
                      <StatCardSkeleton />
                      <StatCardSkeleton />
                    </div>
                  </div>
                ) : funnelGap ? (
                  <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-amber-900 mb-4 flex items-center gap-2">
                      <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      Métricas del Embudo: Primer Gap
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="bg-white/80 rounded-xl p-4 border border-slate-200/50">
                        <div className="text-sm text-slate-600 mb-1">Total de Leads</div>
                        <div className="text-2xl font-bold text-slate-900">{funnelGap.total_leads.toLocaleString()}</div>
                      </div>
                      <div className="bg-white/80 rounded-xl p-4 border border-rose-200/50">
                        <div className="text-sm text-rose-600 mb-1">Sin Identidad ni Claims</div>
                        <div className="text-2xl font-bold text-rose-700">{funnelGap.leads_without_both.toLocaleString()}</div>
                        <div className="text-sm text-rose-600 mt-1">({funnelGap.percentages.without_both}%)</div>
                      </div>
                      <div className="bg-white/80 rounded-xl p-4 border border-emerald-200/50">
                        <div className="text-sm text-emerald-600 mb-1">Con Identidad y Claims</div>
                        <div className="text-2xl font-bold text-emerald-700">{funnelGap.leads_with_claims.toLocaleString()}</div>
                        <div className="text-sm text-emerald-600 mt-1">({funnelGap.percentages.with_claims}%)</div>
                      </div>
                    </div>
                    <div className="bg-white/60 rounded-lg p-4">
                      <p className="text-sm font-medium text-amber-800 mb-2">Desglose:</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-amber-700">
                        <div>Con identidad: <strong>{funnelGap.leads_with_identity.toLocaleString()}</strong> ({funnelGap.percentages.with_identity}%)</div>
                        <div>Sin identidad: <strong>{funnelGap.leads_without_identity.toLocaleString()}</strong> ({funnelGap.percentages.without_identity}%)</div>
                        <div>Con claims: <strong>{funnelGap.leads_with_claims.toLocaleString()}</strong> ({funnelGap.percentages.with_claims}%)</div>
                        <div>Sin claims: <strong>{funnelGap.leads_without_claims.toLocaleString()}</strong> ({funnelGap.percentages.without_claims}%)</div>
                      </div>
                    </div>
                  </div>
                ) : null}

                {/* Summary Cards */}
                {data && (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <StatCard title="Total Deuda Yango" value={`S/ ${(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}`} variant="error" />
                      <StatCard title="Total Esperado" value={`S/ ${(Number(data.summary?.total_expected_yango) || 0).toFixed(2)}`} variant="info" />
                      <StatCard title="Total Pagado" value={`S/ ${(Number(data.summary?.total_paid_yango) || 0).toFixed(2)}`} variant="success" />
                      <StatCard title="% Cobranza" value={`${(Number(data.summary?.collection_percentage) || 0).toFixed(2)}%`} variant="brand" />
                    </div>
                    
                    {/* Scout metrics */}
                    {loadingScoutMetrics ? (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCardSkeleton />
                        <StatCardSkeleton />
                        <StatCardSkeleton />
                      </div>
                    ) : scoutMetrics ? (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <StatCard title="Drivers con Scout" value={`${scoutMetrics.metrics.drivers_with_scout} (${scoutMetrics.metrics.pct_with_scout.toFixed(1)}%)`} variant="success" />
                        <StatCard title="Drivers sin Scout" value={scoutMetrics.metrics.drivers_without_scout.toString()} variant="warning" />
                        <StatCard title="Total Drivers" value={scoutMetrics.metrics.total_drivers.toString()} />
                      </div>
                    ) : (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-700 text-sm">
                        <span className="font-medium">⚠️ Métricas de scout no disponibles.</span> El endpoint puede estar cargando.
                      </div>
                    )}

                    {/* Resumen: Filtrado vs Total */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="card">
                        <div className="card-header">
                          <h3 className="font-semibold text-slate-900">Datos Filtrados</h3>
                        </div>
                        <div className="card-body">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div><span className="text-slate-500">Total Drivers:</span> <span className="font-bold">{data.meta.total}</span></div>
                            <div><span className="text-slate-500">Con Deuda:</span> <span className="font-bold text-rose-600">{data.summary?.drivers_with_debt || 0}</span></div>
                            <div><span className="text-slate-500">M1:</span> <span className="font-bold">{data.summary?.drivers_m1 || 0}</span></div>
                            <div><span className="text-slate-500">M5:</span> <span className="font-bold">{data.summary?.drivers_m5 || 0}</span></div>
                            <div><span className="text-slate-500">M25:</span> <span className="font-bold">{data.summary?.drivers_m25 || 0}</span></div>
                            <div><span className="text-slate-500">Deuda:</span> <span className="font-bold text-rose-600">S/ {(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}</span></div>
                          </div>
                        </div>
                      </div>

                      {data.summary_total && (
                        <div className="card border-2 border-cyan-200">
                          <div className="card-header bg-cyan-50">
                            <h3 className="font-semibold text-cyan-900">Total Sin Filtros</h3>
                          </div>
                          <div className="card-body">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div><span className="text-slate-500">Total Drivers:</span> <span className="font-bold text-cyan-700">{data.summary_total.total_drivers}</span></div>
                              <div><span className="text-slate-500">Con Deuda:</span> <span className="font-bold text-rose-600">{data.summary_total.drivers_with_debt}</span></div>
                              <div><span className="text-slate-500">M1:</span> <span className="font-bold">{data.summary_total.drivers_m1}</span></div>
                              <div><span className="text-slate-500">M5:</span> <span className="font-bold">{data.summary_total.drivers_m5}</span></div>
                              <div><span className="text-slate-500">M25:</span> <span className="font-bold">{data.summary_total.drivers_m25}</span></div>
                              <div><span className="text-slate-500">Deuda:</span> <span className="font-bold text-rose-600">S/ {(Number(data.summary_total.total_debt_yango) || 0).toFixed(2)}</span></div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </TabPanel>

            {/* TAB: KPIs Semanales */}
            <TabPanel id="semanal" activeTab={activeTab}>
              <div className="card">
                <div className="card-header flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">KPIs por Semana (últimas 52 semanas)</h3>
                  {filters.week_start && (
                    <div className="flex items-center gap-2">
                      <Badge variant="info">Filtro: {new Date(filters.week_start).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })}</Badge>
                      <button onClick={handleClearWeekFilter} className="text-sm text-cyan-600 hover:text-cyan-800 underline">Limpiar</button>
                    </div>
                  )}
                </div>
                {loadingWeeklyKpis ? (
                  <div className="p-4">
                    <LoadingSpinner text="Cargando KPIs semanales..." />
                  </div>
                ) : weeklyKpis && weeklyKpis.weeks.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="table-modern">
                      <thead>
                        <tr>
                          <th>Semana</th>
                          <th>Drivers</th>
                          <th>Con Scout</th>
                          <th>% Scout</th>
                          <th className="text-right">Deuda</th>
                          <th>M1</th>
                          <th>M5</th>
                          <th>M25</th>
                          <th className="text-right">Pagado</th>
                          <th>Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {weeklyKpis.weeks.map((week) => (
                          <tr
                            key={week.week_start}
                            className={`cursor-pointer ${filters.week_start === week.week_start ? 'bg-cyan-50 !border-l-4 !border-l-cyan-500' : ''}`}
                            onClick={() => handleWeekClick(week.week_start)}
                          >
                            <td className="font-medium">{new Date(week.week_start).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                            <td>{week.total_rows}</td>
                            <td>{week.with_scout}</td>
                            <td><Badge variant={week.pct_with_scout >= 90 ? 'success' : week.pct_with_scout >= 70 ? 'warning' : 'error'}>{Number(week.pct_with_scout).toFixed(1)}%</Badge></td>
                            <td className="text-right font-semibold text-rose-600">S/ {Number(week.debt_sum).toFixed(2)}</td>
                            <td>{week.reached_m1}</td>
                            <td>{week.reached_m5}</td>
                            <td>{week.reached_m25}</td>
                            <td className="text-right font-semibold text-emerald-600">S/ {Number(week.paid_sum).toFixed(2)}</td>
                            <td>
                              <button className="text-cyan-600 hover:text-cyan-800 text-sm underline" onClick={(e) => { e.stopPropagation(); handleWeekClick(week.week_start); }}>
                                Filtrar
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500">No hay datos semanales disponibles</div>
                )}
              </div>
            </TabPanel>

            {/* TAB: Conductores */}
            <TabPanel id="conductores" activeTab={activeTab}>
              <div className="space-y-4">
                {/* Filtros y Exportar */}
                <div className="flex items-start justify-between gap-4">
                  <Filters
                    fields={filterFields}
                    values={filters}
                    onChange={(values) => {
                      setFilters(values as typeof filters);
                      setOffset(0);
                    }}
                    onReset={() => {
                      setFilters({ only_with_debt: true, reached_milestone: '', scout_id: '', week_start: '' });
                      setOffset(0);
                    }}
                    className="flex-1"
                  />
                  <button
                    onClick={handleExport}
                    disabled={exporting || loading}
                    className="btn btn-success gap-2 disabled:opacity-50"
                  >
                    {exporting ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Exportando...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Exportar CSV
                      </>
                    )}
                  </button>
                </div>

                <DataTable
                  data={data?.data || []}
                  columns={columns}
                  loading={loading}
                  emptyMessage="No hay drivers con deuda pendiente que coincidan con los filtros"
                />

                {!loading && data && data.data.length > 0 && (
                  <Pagination
                    total={data.meta.total}
                    limit={limit}
                    offset={offset}
                    onPageChange={(newOffset) => setOffset(newOffset)}
                  />
                )}
              </div>
            </TabPanel>

            {/* TAB: Recovery & Gaps */}
            <TabPanel id="recovery" activeTab={activeTab}>
              <div className="space-y-6">
                {/* Brechas de Identidad */}
                <div className="card">
                  <div className="card-header flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                        <svg className="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        Brechas de Identidad (Recovery)
                      </h2>
                      <p className="text-sm text-slate-500 mt-1">Cada lead sin identidad puede ser plata no cobrable.</p>
                    </div>
                    <button onClick={() => setShowAlerts(!showAlerts)} className="btn btn-secondary text-sm">
                      {showAlerts ? 'Ocultar' : 'Ver'} Alertas ({identityGapAlerts?.total || 0})
                    </button>
                  </div>
                  <div className="card-body">
                    {loadingIdentityGaps ? (
                      <div className="text-center py-8 text-slate-500">Cargando métricas de brechas...</div>
                    ) : identityGaps ? (
                      <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                          <div className="bg-slate-50 rounded-xl p-4">
                            <div className="text-sm text-slate-600 mb-1">Total Leads</div>
                            <div className="text-2xl font-bold text-slate-900">{identityGaps.totals.total_leads.toLocaleString()}</div>
                          </div>
                          <div className="bg-rose-50 rounded-xl p-4 border border-rose-200/50">
                            <div className="text-sm text-rose-600 mb-1">Unresolved</div>
                            <div className="text-2xl font-bold text-rose-700">{identityGaps.totals.unresolved.toLocaleString()}</div>
                            <div className="text-sm text-rose-600">({identityGaps.totals.pct_unresolved.toFixed(1)}%)</div>
                          </div>
                          <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200/50">
                            <div className="text-sm text-emerald-600 mb-1">Resolved</div>
                            <div className="text-2xl font-bold text-emerald-700">{identityGaps.totals.resolved.toLocaleString()}</div>
                          </div>
                          <div className="bg-amber-50 rounded-xl p-4 border border-amber-200/50">
                            <div className="text-sm text-amber-600 mb-1">High Risk</div>
                            <div className="text-2xl font-bold text-amber-700">
                              {identityGaps.breakdown.filter(b => b.risk_level === 'high').reduce((sum, b) => sum + b.count, 0).toLocaleString()}
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                          <div className="bg-cyan-50 rounded-xl p-4 border border-cyan-200/50">
                            <div className="text-sm text-cyan-600 mb-1">Matched Last 24h</div>
                            <div className="text-2xl font-bold text-cyan-700">{identityGaps.totals.matched_last_24h.toLocaleString()}</div>
                          </div>
                          <div className={`rounded-xl p-4 border ${
                            identityGaps.totals.job_freshness_hours === null ? 'bg-rose-50 border-rose-200' :
                            identityGaps.totals.job_freshness_hours > 24 ? 'bg-amber-50 border-amber-200' :
                            'bg-emerald-50 border-emerald-200'
                          }`}>
                            <div className="text-sm mb-1">Job Freshness</div>
                            <div className="text-2xl font-bold">
                              {identityGaps.totals.job_freshness_hours === null ? 'NUNCA' : `${identityGaps.totals.job_freshness_hours.toFixed(1)}h`}
                            </div>
                            <div className="text-xs mt-1">
                              {identityGaps.totals.job_freshness_hours === null ? 'Job nunca ha corrido' :
                               identityGaps.totals.job_freshness_hours > 24 ? '⚠️ STALE (>24h)' : '✅ OK (<24h)'}
                            </div>
                          </div>
                          <div className="bg-violet-50 rounded-xl p-4 border border-violet-200/50">
                            <div className="text-sm text-violet-600 mb-1">Estado del Recovery</div>
                            <div className="text-lg font-bold text-violet-700">
                              {identityGaps.totals.matched_last_24h > 0 ? '✅ ACTIVO' :
                               identityGaps.totals.job_freshness_hours === null ? '❌ NO CONFIGURADO' :
                               identityGaps.totals.unresolved > 0 ? '⚠️ SIN SEÑAL' : '✅ COMPLETO'}
                            </div>
                          </div>
                        </div>

                        <div className="overflow-x-auto">
                          <table className="table-modern">
                            <thead>
                              <tr>
                                <th>Lead ID</th>
                                <th>Lead Date</th>
                                <th>Gap Reason</th>
                                <th>Risk</th>
                                <th>Days Open</th>
                                <th>Trips 14d</th>
                                <th>Person Key</th>
                              </tr>
                            </thead>
                            <tbody>
                              {identityGaps.items.slice(0, 10).map((item) => (
                                <tr key={item.lead_id}>
                                  <td className="font-mono text-xs">{item.lead_id.substring(0, 12)}...</td>
                                  <td>{new Date(item.lead_date).toLocaleDateString('es-ES')}</td>
                                  <td>
                                    <Badge variant={item.gap_reason === 'resolved' ? 'success' : item.gap_reason === 'no_identity' ? 'error' : 'warning'}>
                                      {item.gap_reason}
                                    </Badge>
                                  </td>
                                  <td>
                                    <Badge variant={item.risk_level === 'high' ? 'error' : item.risk_level === 'medium' ? 'warning' : 'default'}>
                                      {item.risk_level}
                                    </Badge>
                                  </td>
                                  <td>{item.gap_age_days}</td>
                                  <td>{item.trips_14d}</td>
                                  <td className="font-mono text-xs">{item.person_key ? item.person_key.substring(0, 8) + '...' : '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {identityGaps.items.length > 10 && (
                          <p className="text-center text-sm text-slate-500 mt-4">
                            Mostrando 10 de {identityGaps.items.length} brechas.
                          </p>
                        )}
                      </>
                    ) : (
                      <div className="text-center py-8 text-slate-500">No hay datos de brechas disponibles</div>
                    )}

                    {showAlerts && (
                      <div className="mt-6 pt-6 border-t border-slate-200">
                        <h3 className="text-lg font-semibold text-slate-900 mb-4">Alertas Activas</h3>
                        {loadingIdentityGapAlerts ? (
                          <div className="text-center py-4 text-slate-500">Cargando alertas...</div>
                        ) : identityGapAlerts && identityGapAlerts.items.length > 0 ? (
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {identityGapAlerts.items.slice(0, 10).map((alert) => (
                              <div key={alert.lead_id} className={`p-4 rounded-xl border ${
                                alert.severity === 'high' ? 'bg-rose-50 border-rose-200' :
                                alert.severity === 'medium' ? 'bg-amber-50 border-amber-200' :
                                'bg-yellow-50 border-yellow-200'
                              }`}>
                                <div className="flex items-start justify-between">
                                  <div>
                                    <div className="font-medium text-sm">Lead: {alert.lead_id.substring(0, 12)}... | {alert.alert_type}</div>
                                    <div className="text-xs text-slate-600 mt-1">{alert.suggested_action}</div>
                                  </div>
                                  <Badge variant={alert.severity === 'high' ? 'error' : 'warning'}>{alert.days_open} días</Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-center py-4 text-slate-500">No hay alertas activas</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Leads en Limbo */}
                <CabinetLimboSection />

                {/* Claims Gap */}
                <CabinetClaimsGapSection />
              </div>
            </TabPanel>
          </>
        )}
      </Tabs>
    </div>
  );
}
