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

export default function CobranzaYangoPage() {
  const router = useRouter();
  const [data, setData] = useState<CabinetFinancialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    only_with_debt: true,
    reached_milestone: '',
    scout_id: '',
    week_start: '', // Filtro por semana (formato YYYY-MM-DD)
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
  
  // Debounce para filtros (300ms)
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedFilters(filters);
      setOffset(0); // Reset offset cuando cambian filtros
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

  // Cargar Identity Gaps con polling cada 60s
  useEffect(() => {
    async function loadIdentityGaps() {
      try {
        setLoadingIdentityGaps(true);
        const gaps = await getIdentityGaps({
          page: 1,
          page_size: 100,
        });
        setIdentityGaps(gaps);
      } catch (err) {
        console.error('Error cargando brechas de identidad:', err);
      } finally {
        setLoadingIdentityGaps(false);
      }
    }

    loadIdentityGaps();
    const interval = setInterval(loadIdentityGaps, 60000); // 60 segundos
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
    const interval = setInterval(loadIdentityGapAlerts, 60000); // 60 segundos
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

      // Crear URL temporal y descargar
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
    {
      name: 'only_with_debt',
      label: 'Solo con deuda',
      type: 'checkbox' as const,
    },
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
    {
      name: 'scout_id',
      label: 'Scout ID',
      type: 'number' as const,
    },
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

  // Memoizar columns para evitar re-renders innecesarios
  const columns = useMemo(() => [
    {
      key: 'driver_name',
      header: 'Conductor',
      render: (row: CabinetFinancialRow) =>
        row.driver_name ? (
          <div>
            <div className="font-medium">{row.driver_name}</div>
            <div className="text-xs text-gray-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : (
                '—'
              )}
            </div>
          </div>
        ) : (
          <div>
            <div className="text-gray-400">N/A</div>
            <div className="text-xs text-gray-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : (
                '—'
              )}
            </div>
          </div>
        ),
    },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: CabinetFinancialRow) => (
        <div>
          <div>{row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—'}</div>
          {row.iso_week && (
            <div className="text-xs text-gray-500">Semana: {row.iso_week}</div>
          )}
        </div>
      ),
    },
    {
      key: 'connected_flag',
      header: 'Conectado',
      render: (row: CabinetFinancialRow) => (
        <Badge variant={row.connected_flag ? 'success' : 'warning'}>
          {row.connected_flag ? 'Sí' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'total_trips_14d',
      header: 'Viajes 14d',
      render: (row: CabinetFinancialRow) => row.total_trips_14d || 0,
    },
    {
      key: 'milestones',
      header: 'Milestones',
      render: (row: CabinetFinancialRow) => {
        const milestones = [];
        if (row.reached_m1_14d) milestones.push('M1');
        if (row.reached_m5_14d) milestones.push('M5');
        if (row.reached_m25_14d) milestones.push('M25');
        
        if (milestones.length === 0) {
          return <span className="text-gray-400">—</span>;
        }
        
        return (
          <div className="flex gap-1 flex-wrap">
            {milestones.map((m) => (
              <Badge key={m} variant="info">{m}</Badge>
            ))}
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
          
          const tooltipText = [
            `Scout ID: ${row.scout_id}`,
            row.scout_name ? `Nombre: ${row.scout_name}` : '',
            row.scout_quality_bucket ? `Calidad: ${row.scout_quality_bucket}` : '',
            row.scout_source_table ? `Fuente: ${row.scout_source_table}` : '',
            row.scout_attribution_date ? `Fecha: ${new Date(row.scout_attribution_date).toLocaleDateString('es-ES')}` : '',
            row.scout_priority ? `Prioridad: ${row.scout_priority}` : '',
          ].filter(Boolean).join('\n');
          
          return (
            <div className="flex flex-col gap-1" title={tooltipText}>
              <div className="flex items-center gap-1 flex-wrap">
                <Badge variant={qualityBadgeVariant}>
                  {row.scout_name || `Scout ${row.scout_id}`}
                </Badge>
                {row.scout_quality_bucket && (
                  <Badge variant={qualityBadgeVariant === 'success' ? 'default' : qualityBadgeVariant} className="text-xs">
                    {row.scout_quality_bucket.replace(/_/g, ' ')}
                  </Badge>
                )}
              </div>
              {row.scout_id && (
                <div className="text-xs text-gray-500">ID: {row.scout_id}</div>
              )}
            </div>
          );
        }
        return (
          <div title="Scout que originó el registro (atribución canónica). Sin scout asignado.">
            <Badge variant="error">Sin scout</Badge>
          </div>
        );
      },
    },
    {
      key: 'expected_total_yango',
      header: 'Esperado',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.expected_total_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'total_paid_yango',
      header: 'Pagado',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.total_paid_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'amount_due_yango',
      header: 'Deuda',
      render: (row: CabinetFinancialRow) => {
        const amount = Number(row.amount_due_yango) || 0;
        return (
          <span className={amount > 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>
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
          if (row.claim_m1_exists) {
            claims.push(
              <div key="m1" className="text-xs">
                M1: <Badge variant={row.claim_m1_paid ? 'success' : 'warning'}>
                  {row.claim_m1_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m1" className="text-xs">
                M1: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (row.reached_m5_14d) {
          if (row.claim_m5_exists) {
            claims.push(
              <div key="m5" className="text-xs">
                M5: <Badge variant={row.claim_m5_paid ? 'success' : 'warning'}>
                  {row.claim_m5_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m5" className="text-xs">
                M5: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (row.reached_m25_14d) {
          if (row.claim_m25_exists) {
            claims.push(
              <div key="m25" className="text-xs">
                M25: <Badge variant={row.claim_m25_paid ? 'success' : 'warning'}>
                  {row.claim_m25_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m25" className="text-xs">
                M25: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (claims.length === 0) {
          return <span className="text-gray-400">—</span>;
        }
        
        return <div className="flex flex-col gap-1">{claims}</div>;
      },
    },
  ], [router]);

  // Handler para click en semana (preserva otros filtros)
  const handleWeekClick = useCallback((weekStart: string) => {
    setFilters(prev => ({
      ...prev,
      week_start: weekStart,
    }));
  }, []);

  // Handler para limpiar filtro semana
  const handleClearWeekFilter = useCallback(() => {
    setFilters(prev => ({
      ...prev,
      week_start: '',
    }));
  }, []);

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Cobranza Yango - Cabinet Financial 14d</h1>
            <p className="text-gray-600">
              Fuente de verdad financiera para CABINET. Ventana de 14 días desde lead_date.
            </p>
          </div>
          <a
            href="/docs/RESUMEN_EJECUTIVO_COBRANZA_YANGO.md"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-4 px-4 py-2 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 flex items-center gap-2 text-sm"
          >
            <span>📖</span>
            <span>Ver Resumen Ejecutivo</span>
          </a>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Métricas del Gap del Embudo */}
      {!loadingGap && funnelGap && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 text-yellow-900">
            ⚠️ Métricas del Embudo: Primer Gap (Leads Sin Identidad ni Pago)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded shadow">
              <div className="text-sm text-gray-600 mb-1">Total de Leads</div>
              <div className="text-2xl font-bold">{funnelGap.total_leads.toLocaleString()}</div>
            </div>
            <div className="bg-red-50 p-4 rounded shadow border border-red-200">
              <div className="text-sm text-red-700 mb-1">Leads Sin Identidad ni Claims</div>
              <div className="text-2xl font-bold text-red-700">
                {funnelGap.leads_without_both.toLocaleString()}
              </div>
              <div className="text-sm text-red-600 mt-1">
                ({funnelGap.percentages.without_both}% del total)
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded shadow border border-green-200">
              <div className="text-sm text-green-700 mb-1">Leads Con Identidad y Claims</div>
              <div className="text-2xl font-bold text-green-700">
                {funnelGap.leads_with_claims.toLocaleString()}
              </div>
              <div className="text-sm text-green-600 mt-1">
                ({funnelGap.percentages.with_claims}% del total)
              </div>
            </div>
          </div>
          <div className="mt-4 text-sm text-gray-700">
            <p className="mb-2">
              <strong>Desglose:</strong>
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>
                <strong>Con identidad:</strong> {funnelGap.leads_with_identity.toLocaleString()} 
                ({funnelGap.percentages.with_identity}%)
              </li>
              <li>
                <strong>Sin identidad:</strong> {funnelGap.leads_without_identity.toLocaleString()} 
                ({funnelGap.percentages.without_identity}%)
              </li>
              <li>
                <strong>Con claims:</strong> {funnelGap.leads_with_claims.toLocaleString()} 
                ({funnelGap.percentages.with_claims}%)
              </li>
              <li>
                <strong>Sin claims:</strong> {funnelGap.leads_without_claims.toLocaleString()} 
                ({funnelGap.percentages.without_claims}%)
              </li>
            </ul>
            <p className="mt-3 text-xs text-gray-600">
              💡 <strong>Interpretación:</strong> Los leads "Sin Identidad ni Claims" representan el primer gap del embudo. 
              Estos son leads que se registraron pero no lograron tener identidad canónica ni generar pago. 
              Un porcentaje alto puede indicar problemas en el proceso de matching o datos incompletos.
            </p>
          </div>
        </div>
      )}

      {/* Summary Cards - Mostrando datos filtrados */}
      {data && (
        <div className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <StatCard
              title="Total Deuda Yango (filtrado)"
              value={`S/ ${(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}`}
            />
            <StatCard
              title="Total Esperado (filtrado)"
              value={`S/ ${(Number(data.summary?.total_expected_yango) || 0).toFixed(2)}`}
            />
            <StatCard
              title="Total Pagado (filtrado)"
              value={`S/ ${(Number(data.summary?.total_paid_yango) || 0).toFixed(2)}`}
            />
            <StatCard
              title="% Cobranza (filtrado)"
              value={`${(Number(data.summary?.collection_percentage) || 0).toFixed(2)}%`}
            />
          </div>
          {/* KPIs de Atribución Scout (desde endpoint separado) */}
          {loadingScoutMetrics ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatCard title="Cargando..." value="—" />
              <StatCard title="Cargando..." value="—" />
              <StatCard title="Cargando..." value="—" />
            </div>
          ) : scoutMetrics ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatCard
                title="Drivers con Scout"
                value={`${scoutMetrics.metrics.drivers_with_scout} (${scoutMetrics.metrics.pct_with_scout.toFixed(1)}%)`}
              />
              <StatCard
                title="Drivers sin Scout"
                value={`${scoutMetrics.metrics.drivers_without_scout}`}
              />
              <StatCard
                title="Total Drivers (filtrado)"
                value={`${scoutMetrics.metrics.total_drivers}`}
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <StatCard
                title="Drivers con Scout"
                value={`${data.summary?.drivers_with_scout || 0} (${(data.summary?.pct_with_scout || 0).toFixed(1)}%)`}
              />
              <StatCard
                title="Drivers sin Scout"
                value={`${data.summary?.drivers_without_scout || 0}`}
              />
              <StatCard
                title="Total Drivers (filtrado)"
                value={`${data.summary?.total_drivers || 0}`}
              />
            </div>
          )}
          
          {/* KPIs por Semana */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">KPIs por Semana (últimas 52 semanas)</h3>
              {filters.week_start && (
                <div className="flex items-center gap-2">
                  <Badge variant="info">
                    Filtro activo: {new Date(filters.week_start).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })}
                  </Badge>
                  <button
                    onClick={handleClearWeekFilter}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    Limpiar filtro semana
                  </button>
                </div>
              )}
            </div>
            {loadingWeeklyKpis ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
                Cargando KPIs semanales...
              </div>
            ) : weeklyKpis && weeklyKpis.weeks.length > 0 ? (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Semana</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Drivers</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Con Scout</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">% Scout</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Deuda (S/)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">M1</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">M5</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">M25</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pagado (S/)</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {weeklyKpis.weeks.map((week) => (
                        <tr
                          key={week.week_start}
                          className={`hover:bg-gray-50 cursor-pointer ${filters.week_start === week.week_start ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`}
                          onClick={() => handleWeekClick(week.week_start)}
                        >
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                            {new Date(week.week_start).toLocaleDateString('es-ES', { year: 'numeric', month: 'short', day: 'numeric' })}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">{week.total_rows}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">{week.with_scout}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <Badge variant={week.pct_with_scout >= 90 ? 'success' : week.pct_with_scout >= 70 ? 'warning' : 'error'}>
                              {week.pct_with_scout.toFixed(1)}%
                            </Badge>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm font-semibold text-red-600">
                            S/ {week.debt_sum.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">{week.reached_m1}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">{week.reached_m5}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">{week.reached_m25}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-green-600">
                            S/ {week.paid_sum.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <button
                              className="text-blue-600 hover:text-blue-800 underline"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleWeekClick(week.week_start);
                              }}
                            >
                              Filtrar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
                No hay datos semanales disponibles
              </div>
            )}
          </div>
        </div>
      )}

      {/* Brechas de Identidad (Recovery) */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg p-6 shadow">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            🔍 Brechas de Identidad (Recovery)
          </h2>
          <button
            onClick={() => setShowAlerts(!showAlerts)}
            className="px-3 py-1 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
          >
            {showAlerts ? 'Ocultar' : 'Ver'} Alertas ({identityGapAlerts?.total || 0})
          </button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Cada lead sin identidad puede ser plata no cobrable. Este módulo detecta y reintenta matching automáticamente.
        </p>

        {loadingIdentityGaps ? (
          <div className="text-center py-8 text-gray-500">Cargando métricas de brechas...</div>
        ) : identityGaps ? (
          <>
            {/* Cards de métricas */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-gray-50 p-4 rounded shadow">
                <div className="text-sm text-gray-600 mb-1">Total Leads</div>
                <div className="text-2xl font-bold">{identityGaps.totals.total_leads.toLocaleString()}</div>
              </div>
              <div className="bg-red-50 p-4 rounded shadow border border-red-200">
                <div className="text-sm text-red-700 mb-1">Unresolved</div>
                <div className="text-2xl font-bold text-red-700">
                  {identityGaps.totals.unresolved.toLocaleString()}
                </div>
                <div className="text-sm text-red-600 mt-1">
                  ({identityGaps.totals.pct_unresolved.toFixed(1)}%)
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded shadow border border-green-200">
                <div className="text-sm text-green-700 mb-1">Resolved</div>
                <div className="text-2xl font-bold text-green-700">
                  {identityGaps.totals.resolved.toLocaleString()}
                </div>
                <div className="text-sm text-green-600 mt-1">
                  ({((identityGaps.totals.resolved / Math.max(identityGaps.totals.total_leads, 1)) * 100).toFixed(1)}%)
                </div>
              </div>
              <div className="bg-orange-50 p-4 rounded shadow border border-orange-200">
                <div className="text-sm text-orange-700 mb-1">High Risk</div>
                <div className="text-2xl font-bold text-orange-700">
                  {identityGaps.breakdown
                    .filter(b => b.risk_level === 'high')
                    .reduce((sum, b) => sum + b.count, 0)
                    .toLocaleString()}
                </div>
              </div>
            </div>

            {/* Métricas de Recovery Job */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded shadow border border-blue-200">
                <div className="text-sm text-blue-700 mb-1">Matched Last 24h</div>
                <div className="text-2xl font-bold text-blue-700">
                  {identityGaps.totals.matched_last_24h.toLocaleString()}
                </div>
                <div className="text-xs text-blue-600 mt-1">
                  Leads matcheados por el job
                </div>
              </div>
              <div className={`p-4 rounded shadow border ${
                identityGaps.totals.job_freshness_hours === null 
                  ? 'bg-red-50 border-red-200' 
                  : identityGaps.totals.job_freshness_hours > 24 
                    ? 'bg-orange-50 border-orange-200' 
                    : 'bg-green-50 border-green-200'
              }`}>
                <div className={`text-sm mb-1 ${
                  identityGaps.totals.job_freshness_hours === null 
                    ? 'text-red-700' 
                    : identityGaps.totals.job_freshness_hours > 24 
                      ? 'text-orange-700' 
                      : 'text-green-700'
                }`}>
                  Job Freshness
                </div>
                <div className={`text-2xl font-bold ${
                  identityGaps.totals.job_freshness_hours === null 
                    ? 'text-red-700' 
                    : identityGaps.totals.job_freshness_hours > 24 
                      ? 'text-orange-700' 
                      : 'text-green-700'
                }`}>
                  {identityGaps.totals.job_freshness_hours === null 
                    ? 'NUNCA' 
                    : `${identityGaps.totals.job_freshness_hours.toFixed(1)}h`}
                </div>
                <div className={`text-xs mt-1 ${
                  identityGaps.totals.job_freshness_hours === null 
                    ? 'text-red-600' 
                    : identityGaps.totals.job_freshness_hours > 24 
                      ? 'text-orange-600' 
                      : 'text-green-600'
                }`}>
                  {identityGaps.totals.job_freshness_hours === null 
                    ? 'Job nunca ha corrido' 
                    : identityGaps.totals.job_freshness_hours > 24 
                      ? '⚠️ STALE (>24h)' 
                      : '✅ OK (<24h)'}
                </div>
                {identityGaps.totals.last_job_run && (
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(identityGaps.totals.last_job_run).toLocaleString('es-ES')}
                  </div>
                )}
              </div>
              <div className="bg-purple-50 p-4 rounded shadow border border-purple-200">
                <div className="text-sm text-purple-700 mb-1">Estado del Recovery</div>
                <div className="text-lg font-bold text-purple-700">
                  {identityGaps.totals.matched_last_24h > 0 
                    ? '✅ ACTIVO' 
                    : identityGaps.totals.job_freshness_hours === null 
                      ? '❌ NO CONFIGURADO' 
                      : identityGaps.totals.unresolved > 0 
                        ? '⚠️ SIN SEÑAL' 
                        : '✅ COMPLETO'}
                </div>
                <div className="text-xs text-purple-600 mt-1">
                  {identityGaps.totals.matched_last_24h > 0 
                    ? 'Job está procesando y matcheando' 
                    : identityGaps.totals.job_freshness_hours === null 
                      ? 'Configurar scheduler (ver runbook)' 
                      : identityGaps.totals.unresolved > 0 
                        ? 'Job corre pero no encuentra matches' 
                        : 'Todos los leads están resueltos'}
                </div>
              </div>
            </div>

            {/* Tabla de brechas */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lead ID</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lead Date</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Gap Reason</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Days Open</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Trips 14d</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {identityGaps.items.slice(0, 20).map((item) => (
                    <tr key={item.lead_id}>
                      <td className="px-4 py-2 text-sm font-mono">{item.lead_id.substring(0, 12)}...</td>
                      <td className="px-4 py-2 text-sm">
                        {new Date(item.lead_date).toLocaleDateString('es-ES')}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <Badge
                          variant={
                            item.gap_reason === 'resolved' ? 'success' :
                            item.gap_reason === 'no_identity' ? 'error' :
                            'warning'
                          }
                        >
                          {item.gap_reason}
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <Badge
                          variant={
                            item.risk_level === 'high' ? 'error' :
                            item.risk_level === 'medium' ? 'warning' :
                            'default'
                          }
                        >
                          {item.risk_level}
                        </Badge>
                      </td>
                      <td className="px-4 py-2 text-sm">{item.gap_age_days}</td>
                      <td className="px-4 py-2 text-sm">{item.trips_14d}</td>
                      <td className="px-4 py-2 text-sm font-mono text-xs">
                        {item.person_key ? item.person_key.substring(0, 8) + '...' : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {identityGaps.items.length > 20 && (
              <div className="mt-2 text-sm text-gray-500 text-center">
                Mostrando 20 de {identityGaps.items.length} brechas. Usa los filtros de la API para ver más.
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-8 text-gray-500">No hay datos de brechas disponibles</div>
        )}

        {/* Modal/Sección de Alertas */}
        {showAlerts && (
          <div className="mt-6 border-t pt-6">
            <h3 className="text-lg font-semibold mb-4">Alertas Activas</h3>
            {loadingIdentityGapAlerts ? (
              <div className="text-center py-4 text-gray-500">Cargando alertas...</div>
            ) : identityGapAlerts && identityGapAlerts.items.length > 0 ? (
              <div className="space-y-2">
                {identityGapAlerts.items.map((alert) => (
                  <div
                    key={alert.lead_id}
                    className={`p-3 rounded border ${
                      alert.severity === 'high' ? 'bg-red-50 border-red-200' :
                      alert.severity === 'medium' ? 'bg-orange-50 border-orange-200' :
                      'bg-yellow-50 border-yellow-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="font-medium text-sm">
                          Lead: {alert.lead_id.substring(0, 12)}... | {alert.alert_type}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">{alert.suggested_action}</div>
                      </div>
                      <div className="text-xs text-gray-500">
                        {alert.days_open} días abierta
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">No hay alertas activas</div>
            )}
          </div>
        )}
      </div>

      {/* Resumen: Filtrado vs Total */}
      {data && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Resumen: Filtrado vs Total</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Columna izquierda: Datos filtrados */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="font-semibold text-gray-700 mb-3 border-b pb-2">
                Datos Filtrados (Mostrados en tabla)
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-gray-600">Total Drivers</div>
                  <div className="text-lg font-bold">{data.meta.total}</div>
                </div>
                <div>
                  <div className="text-gray-600">Con Deuda</div>
                  <div className="text-lg font-bold text-red-600">{data.summary?.drivers_with_debt || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M1 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m1 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M5 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m5 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M25 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m25 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">Deuda Total</div>
                  <div className="text-lg font-bold text-red-600">
                    S/ {(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">Con Scout</div>
                  <div className="text-lg font-bold text-green-600">{data.summary?.drivers_with_scout || 0}</div>
                  <div className="text-xs text-gray-500">({(data.summary?.pct_with_scout || 0).toFixed(1)}%)</div>
                </div>
                <div>
                  <div className="text-gray-600">Sin Scout</div>
                  <div className="text-lg font-bold text-orange-600">{data.summary?.drivers_without_scout || 0}</div>
                  <div className="text-xs text-gray-500">({((data.summary?.drivers_without_scout || 0) / Math.max(data.summary?.total_drivers || 1, 1) * 100).toFixed(1)}%)</div>
                </div>
              </div>
            </div>

            {/* Columna derecha: Total sin filtros */}
            {data.summary_total && (
              <div className="bg-blue-50 p-4 rounded-lg shadow border-2 border-blue-200">
                <h3 className="font-semibold text-blue-700 mb-3 border-b border-blue-300 pb-2">
                  Total Sin Filtros (Todos los drivers Cabinet)
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-gray-700">Total Drivers</div>
                    <div className="text-lg font-bold text-blue-700">{data.summary_total.total_drivers}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">Con Deuda</div>
                    <div className="text-lg font-bold text-red-600">{data.summary_total.drivers_with_debt}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M1 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m1}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M5 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m5}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M25 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m25}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">Deuda Total</div>
                    <div className="text-lg font-bold text-red-600">
                      S/ {(Number(data.summary_total.total_debt_yango) || 0).toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-700">Con Scout</div>
                    <div className="text-lg font-bold text-green-600">{data.summary_total.drivers_with_scout}</div>
                    <div className="text-xs text-gray-600">({(data.summary_total.pct_with_scout || 0).toFixed(1)}%)</div>
                  </div>
                  <div>
                    <div className="text-gray-700">Sin Scout</div>
                    <div className="text-lg font-bold text-orange-600">{data.summary_total.drivers_without_scout}</div>
                    <div className="text-xs text-gray-600">({((data.summary_total.drivers_without_scout || 0) / Math.max(data.summary_total.total_drivers || 1, 1) * 100).toFixed(1)}%)</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mb-4 flex items-center justify-between">
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
        />
        <button
          onClick={handleExport}
          disabled={exporting || loading}
          className="ml-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {exporting ? (
            <>
              <span className="animate-spin">⏳</span>
              <span>Exportando...</span>
            </>
          ) : (
            <>
              <span>📥</span>
              <span>Exportar CSV</span>
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
  );
}
