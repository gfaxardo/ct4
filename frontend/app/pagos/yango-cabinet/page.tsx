/**
 * Yango - Reconciliación
 * Diseño moderno consistente con el resto del sistema
 * 
 * Objetivo: "¿Cuál es el estado de reconciliación de pagos Yango?"
 */

'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  getYangoReconciliationSummary,
  getYangoReconciliationItems,
  getCabinetReconciliation,
  ApiError,
} from '@/lib/api';
import type {
  YangoReconciliationSummaryResponse,
  YangoReconciliationItemsResponse,
  CabinetReconciliationResponse,
  CabinetReconciliationRow,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';
import { PageLoadingOverlay } from '@/components/Skeleton';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getReconciliationStatusVariant(status: string | null): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (!status) return 'default';
  switch (status) {
    case 'OK':
      return 'success';
    case 'ACHIEVED_NOT_PAID':
      return 'warning';
    case 'PAID_WITHOUT_ACHIEVEMENT':
      return 'info';
    case 'NOT_APPLICABLE':
      return 'default';
    default:
      return 'default';
  }
}

function getReconciliationStatusLabel(status: string | null): string {
  if (!status) return '—';
  const labels: Record<string, string> = {
    'OK': 'OK',
    'ACHIEVED_NOT_PAID': 'Pendiente',
    'PAID_WITHOUT_ACHIEVEMENT': 'Pagado Anticipado',
    'NOT_APPLICABLE': 'N/A',
  };
  return labels[status] || status;
}

// ============================================================================
// TYPES
// ============================================================================

type DerivedFlag = 'OUT_OF_SEQUENCE' | 'EARLY_PAYMENT' | 'LATE_PAYMENT' | 'INCOMPLETE_SEQUENCE' | 'SEQUENCE_CORRECTED';

interface RowWithFlags extends CabinetReconciliationRow {
  derivedFlags: DerivedFlag[];
}

// ============================================================================
// FLAG DETECTION
// ============================================================================

function daysBetween(date1: string | null, date2: string | null): number | null {
  if (!date1 || !date2) return null;
  try {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffTime = Math.abs(d2.getTime() - d1.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function detectDerivedFlags(
  currentRow: CabinetReconciliationRow,
  allRows: CabinetReconciliationRow[]
): DerivedFlag[] {
  const flags: DerivedFlag[] = [];
  const driverId = currentRow.driver_id;
  const milestoneValue = currentRow.milestone_value;
  const payDate = currentRow.pay_date;
  const achievedDate = currentRow.achieved_date;
  const reconciliationStatus = currentRow.reconciliation_status;
  const paidFlag = currentRow.paid_flag;

  if (!driverId || milestoneValue === null) return flags;

  const driverRows = allRows.filter(r => r.driver_id === driverId && r.milestone_value !== null);

  // EARLY_PAYMENT
  if (reconciliationStatus === 'PAID_WITHOUT_ACHIEVEMENT' && payDate) {
    if (!achievedDate) {
      flags.push('EARLY_PAYMENT');
    } else {
      const daysDiff = daysBetween(achievedDate, payDate);
      if (daysDiff !== null && daysDiff < 0) {
        flags.push('EARLY_PAYMENT');
      }
    }
  }

  // LATE_PAYMENT
  if (achievedDate && payDate) {
    const daysDiff = daysBetween(achievedDate, payDate);
    if (daysDiff !== null && daysDiff > 7) {
      flags.push('LATE_PAYMENT');
    }
  }

  // OUT_OF_SEQUENCE
  if (paidFlag && payDate) {
    const greaterMilestones = driverRows.filter(
      r => r.milestone_value !== null && 
      r.milestone_value > milestoneValue && 
      r.paid_flag && 
      r.pay_date
    );
    
    for (const greaterRow of greaterMilestones) {
      if (greaterRow.pay_date) {
        const daysDiff = daysBetween(greaterRow.pay_date, payDate);
        if (daysDiff !== null && daysDiff < 0) {
          flags.push('OUT_OF_SEQUENCE');
          break;
        }
      }
    }
  }

  // INCOMPLETE_SEQUENCE
  if (paidFlag && milestoneValue > 1) {
    const expectedMilestones = [1, 5, 25].filter(m => m < milestoneValue);
    const paidMilestones = driverRows
      .filter(r => r.paid_flag && r.milestone_value !== null && expectedMilestones.includes(r.milestone_value))
      .map(r => r.milestone_value!);
    
    const missingMilestones = expectedMilestones.filter(m => !paidMilestones.includes(m));
    if (missingMilestones.length > 0) {
      flags.push('INCOMPLETE_SEQUENCE');
    }
  }

  return flags;
}

function getDerivedFlagLabel(flag: DerivedFlag): string {
  const labels: Record<DerivedFlag, string> = {
    'OUT_OF_SEQUENCE': 'Fuera Secuencia',
    'EARLY_PAYMENT': 'Anticipado',
    'LATE_PAYMENT': 'Tardío',
    'INCOMPLETE_SEQUENCE': 'Incompleto',
    'SEQUENCE_CORRECTED': 'Corregido',
  };
  return labels[flag];
}

function getDerivedFlagVariant(flag: DerivedFlag): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const variants: Record<DerivedFlag, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    'OUT_OF_SEQUENCE': 'warning',
    'EARLY_PAYMENT': 'info',
    'LATE_PAYMENT': 'warning',
    'INCOMPLETE_SEQUENCE': 'warning',
    'SEQUENCE_CORRECTED': 'success',
  };
  return variants[flag];
}

// ============================================================================
// ICONS
// ============================================================================

const Icons = {
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  pending: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  money: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
};

// ============================================================================
// TAB COMPONENTS
// ============================================================================

interface TabProps {
  id: string;
  label: string;
  active: boolean;
  onClick: () => void;
  badge?: number;
}

function Tab({ label, active, onClick, badge }: TabProps) {
  return (
    <button
      onClick={onClick}
      className={`
        relative px-4 py-3 text-sm font-medium transition-all duration-200
        ${active 
          ? 'text-cyan-600 border-b-2 border-cyan-500 bg-cyan-50/50' 
          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
        }
      `}
    >
      <span className="flex items-center gap-2">
        {label}
        {badge !== undefined && badge > 0 && (
          <span className={`
            px-2 py-0.5 text-xs rounded-full
            ${active ? 'bg-cyan-100 text-cyan-700' : 'bg-slate-100 text-slate-600'}
          `}>
            {badge}
          </span>
        )}
      </span>
    </button>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function YangoCabinetPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'summary' | 'reconciliation'>('summary');
  const [summary, setSummary] = useState<YangoReconciliationSummaryResponse | null>(null);
  const [items, setItems] = useState<YangoReconciliationItemsResponse | null>(null);
  const [cabinetReconciliation, setCabinetReconciliation] = useState<CabinetReconciliationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [reconciliationLoading, setReconciliationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconciliationError, setReconciliationError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    week_start: '',
    milestone_value: '',
    mode: 'real',
  });
  const [offset, setOffset] = useState(0);
  const [limit] = useState(100);
  
  // Paginación para Items Detallados
  const [itemsPage, setItemsPage] = useState(0);
  const itemsPerPage = 20;
  
  // Paginación para Reconciliación Detallada
  const [reconPage, setReconPage] = useState(0);
  const reconPerPage = 30;

  // Load summary data
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, itemsData] = await Promise.all([
          getYangoReconciliationSummary({
            week_start: filters.week_start || undefined,
            milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
            mode: filters.mode as 'real' | 'assumed',
            limit: 100,
          }),
          getYangoReconciliationItems({
            week_start: filters.week_start || undefined,
            milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
            limit,
            offset,
          }),
        ]);

        setSummary(summaryData);
        setItems(itemsData);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Error ${err.status}: ${err.detail || err.message}`);
        } else {
          setError('Error al cargar datos');
        }
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [filters, offset, limit]);

  // Load reconciliation data when tab is active
  useEffect(() => {
    if (activeTab === 'reconciliation' && !cabinetReconciliation) {
      async function loadReconciliation() {
        try {
          setReconciliationLoading(true);
          setReconciliationError(null);
          const data = await getCabinetReconciliation({ limit: 100, offset: 0 });
          setCabinetReconciliation(data);
        } catch (err) {
          if (err instanceof ApiError) {
            setReconciliationError(`Error ${err.status}: ${err.detail || err.message}`);
          } else {
            setReconciliationError('Error al cargar reconciliación');
          }
        } finally {
          setReconciliationLoading(false);
        }
      }
      loadReconciliation();
    }
  }, [activeTab, cabinetReconciliation]);

  // Calculate stats from reconciliation data
  const reconciliationStats = useMemo(() => {
    if (!cabinetReconciliation?.rows) return null;
    
    const stats = {
      total: cabinetReconciliation.rows.length,
      ok: 0,
      pending: 0,
      earlyPaid: 0,
      notApplicable: 0,
    };

    cabinetReconciliation.rows.forEach(row => {
      switch (row.reconciliation_status) {
        case 'OK': stats.ok++; break;
        case 'ACHIEVED_NOT_PAID': stats.pending++; break;
        case 'PAID_WITHOUT_ACHIEVEMENT': stats.earlyPaid++; break;
        case 'NOT_APPLICABLE': stats.notApplicable++; break;
      }
    });

    return stats;
  }, [cabinetReconciliation]);

  // Calculate rows with flags
  const rowsWithFlags = useMemo((): RowWithFlags[] => {
    if (!cabinetReconciliation?.rows) return [];
    return cabinetReconciliation.rows.map(row => ({
      ...row,
      derivedFlags: detectDerivedFlags(row, cabinetReconciliation.rows),
    }));
  }, [cabinetReconciliation]);

  // Initial loading
  if (loading && !summary && !items) {
    return <PageLoadingOverlay title="Reconciliación" subtitle="Cargando datos de reconciliación..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reconciliación de Pagos Yango</h1>
          <p className="text-slate-500 mt-1">
            Cruce entre milestones logrados operativamente y pagos ejecutados por Yango
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
          <p className="text-rose-800">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200/60 overflow-hidden">
        <div className="flex border-b border-slate-200">
          <Tab 
            id="summary" 
            label="Resumen" 
            active={activeTab === 'summary'} 
            onClick={() => setActiveTab('summary')}
            badge={summary?.rows?.length}
          />
          <Tab 
            id="reconciliation" 
            label="Reconciliación Detallada" 
            active={activeTab === 'reconciliation'} 
            onClick={() => setActiveTab('reconciliation')}
            badge={cabinetReconciliation?.rows?.length}
          />
        </div>

        <div className="p-6">
          {/* ============== TAB: SUMMARY ============== */}
          {activeTab === 'summary' && (
            <div className="space-y-6">
              {/* Filters */}
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Semana</label>
                    <input
                      type="date"
                      value={filters.week_start}
                      onChange={(e) => setFilters(prev => ({ ...prev, week_start: e.target.value }))}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Milestone</label>
                    <select
                      value={filters.milestone_value}
                      onChange={(e) => setFilters(prev => ({ ...prev, milestone_value: e.target.value }))}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500"
                    >
                      <option value="">Todos</option>
                      <option value="1">M1</option>
                      <option value="5">M5</option>
                      <option value="25">M25</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1.5">Modo</label>
                    <select
                      value={filters.mode}
                      onChange={(e) => setFilters(prev => ({ ...prev, mode: e.target.value }))}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500"
                    >
                      <option value="real">Real</option>
                      <option value="assumed">Assumed</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={() => {
                        setFilters({ week_start: '', milestone_value: '', mode: 'real' });
                        setOffset(0);
                      }}
                      className="w-full px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                    >
                      Limpiar
                    </button>
                  </div>
                </div>
              </div>

              {/* Summary Table */}
              {summary && summary.rows.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">Resumen por Semana y Milestone</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Semana</th>
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Milestone</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Esperado</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pagado</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pendiente</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Diferencia</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {summary.rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                            <td className="py-3 px-4 text-sm text-slate-900">
                              {row.pay_week_start_monday ? new Date(row.pay_week_start_monday).toLocaleDateString('es-ES') : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant={row.milestone_value === 25 ? 'success' : row.milestone_value === 5 ? 'warning' : 'info'}>
                                M{row.milestone_value}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-sm text-right font-medium text-slate-900">
                              S/ {row.amount_expected_sum ? Number(row.amount_expected_sum).toFixed(2) : '0.00'}
                            </td>
                            <td className="py-3 px-4 text-sm text-right font-medium text-emerald-600">
                              S/ {row.amount_paid_total_visible ? Number(row.amount_paid_total_visible).toFixed(2) : '0.00'}
                            </td>
                            <td className="py-3 px-4 text-sm text-right font-medium text-amber-600">
                              S/ {row.amount_pending_active_sum ? Number(row.amount_pending_active_sum).toFixed(2) : '0.00'}
                            </td>
                            <td className={`py-3 px-4 text-sm text-right font-medium ${row.amount_diff && row.amount_diff < 0 ? 'text-rose-600' : 'text-slate-600'}`}>
                              S/ {row.amount_diff ? Number(row.amount_diff).toFixed(2) : '0.00'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Items Table */}
              {items && items.rows.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-4">
                    Items Detallados
                    <span className="ml-2 text-sm font-normal text-slate-500">({items.count} items)</span>
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Driver</th>
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Milestone</th>
                          <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Monto</th>
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Vencimiento</th>
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Estado</th>
                          <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Fecha Pago</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {items.rows.slice(itemsPage * itemsPerPage, (itemsPage + 1) * itemsPerPage).map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                            <td className="py-3 px-4">
                              <button
                                onClick={() => router.push(`/pagos/yango-cabinet/driver/${row.driver_id}`)}
                                className="text-sm font-medium text-cyan-600 hover:text-cyan-700 hover:underline"
                              >
                                {row.driver_id || '—'}
                              </button>
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant={row.milestone_value === 25 ? 'success' : row.milestone_value === 5 ? 'warning' : 'info'}>
                                M{row.milestone_value}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-sm text-right font-medium text-slate-900">
                              S/ {row.expected_amount || '0.00'}
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600">
                              {row.due_date ? new Date(row.due_date).toLocaleDateString('es-ES') : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge variant={row.paid_status?.includes('paid') ? 'success' : row.paid_status?.includes('pending') ? 'warning' : 'error'}>
                                {row.paid_status || 'PENDING'}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-sm text-slate-600">
                              {row.paid_date ? new Date(row.paid_date).toLocaleDateString('es-ES') : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Controles de paginación para Items */}
                  <div className="mt-4 flex items-center justify-between">
                    <p className="text-sm text-slate-500">
                      Mostrando {Math.min(itemsPage * itemsPerPage + 1, items.rows.length)} - {Math.min((itemsPage + 1) * itemsPerPage, items.rows.length)} de {items.count} items
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setItemsPage(p => Math.max(0, p - 1))}
                        disabled={itemsPage === 0}
                        className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        ← Anterior
                      </button>
                      <span className="text-sm text-slate-600">
                        Página {itemsPage + 1} de {Math.ceil(items.rows.length / itemsPerPage)}
                      </span>
                      <button
                        onClick={() => setItemsPage(p => Math.min(Math.ceil(items.rows.length / itemsPerPage) - 1, p + 1))}
                        disabled={(itemsPage + 1) * itemsPerPage >= items.rows.length}
                        className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Siguiente →
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {(!summary?.rows?.length && !items?.rows?.length) && !loading && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-4">
                    {Icons.warning}
                  </div>
                  <p className="text-slate-500">No hay datos para los filtros seleccionados</p>
                </div>
              )}
            </div>
          )}

          {/* ============== TAB: RECONCILIATION ============== */}
          {activeTab === 'reconciliation' && (
            <div className="space-y-6">
              {reconciliationLoading && (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="relative w-12 h-12 mb-4">
                    <div className="absolute inset-0 border-4 border-slate-200 rounded-full" />
                    <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                  <p className="text-slate-600">Cargando reconciliación...</p>
                </div>
              )}

              {reconciliationError && (
                <div className="bg-rose-50 border border-rose-200 rounded-xl p-4">
                  <p className="text-rose-800">{reconciliationError}</p>
                </div>
              )}

              {!reconciliationLoading && reconciliationStats && (
                <>
                  {/* Stats Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <StatCard
                      title="Total"
                      value={reconciliationStats.total}
                      subtitle="Registros analizados"
                      icon={Icons.money}
                    />
                    <StatCard
                      title="OK"
                      value={reconciliationStats.ok}
                      subtitle={`${((reconciliationStats.ok / reconciliationStats.total) * 100).toFixed(1)}% del total`}
                      icon={Icons.check}
                      variant="success"
                    />
                    <StatCard
                      title="Pendientes"
                      value={reconciliationStats.pending}
                      subtitle="Logrado, no pagado"
                      icon={Icons.pending}
                      variant="warning"
                    />
                    <StatCard
                      title="Anticipados"
                      value={reconciliationStats.earlyPaid}
                      subtitle="Pagado por Yango"
                      icon={Icons.money}
                      variant="info"
                    />
                  </div>

                  {/* Info Panel */}
                  <div className="bg-gradient-to-r from-slate-50 to-cyan-50/30 rounded-xl border border-slate-200/60 p-4">
                    <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
                      <svg className="w-4 h-4 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Sobre la Reconciliación
                    </h3>
                    <p className="text-sm text-slate-600">
                      Esta vista muestra el cruce entre milestones <strong>logrados operativamente</strong> y <strong>pagados por Yango</strong>. 
                      Los estados son explicativos, no correctivos. El sistema CT4 no corrige el pasado, lo explica con evidencia.
                    </p>
                  </div>

                  {/* Reconciliation Table */}
                  {rowsWithFlags.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50">
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Driver</th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Milestone</th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Estado</th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Señales</th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Fecha Pago</th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Fecha Logro</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {rowsWithFlags.slice(reconPage * reconPerPage, (reconPage + 1) * reconPerPage).map((row, idx) => (
                            <tr key={`${row.driver_id}-${row.milestone_value}-${idx}`} className="hover:bg-slate-50/50 transition-colors">
                              <td className="py-3 px-4">
                                <button
                                  onClick={() => router.push(`/pagos/yango-cabinet/driver/${row.driver_id}`)}
                                  className="text-sm font-medium text-cyan-600 hover:text-cyan-700 hover:underline"
                                >
                                  {row.driver_id || '—'}
                                </button>
                              </td>
                              <td className="py-3 px-4">
                                <Badge variant={row.milestone_value === 25 ? 'success' : row.milestone_value === 5 ? 'warning' : 'info'}>
                                  M{row.milestone_value || '—'}
                                </Badge>
                              </td>
                              <td className="py-3 px-4">
                                <Badge variant={getReconciliationStatusVariant(row.reconciliation_status)}>
                                  {getReconciliationStatusLabel(row.reconciliation_status)}
                                </Badge>
                              </td>
                              <td className="py-3 px-4">
                                {row.derivedFlags.length === 0 ? (
                                  <span className="text-slate-400">—</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1">
                                    {row.derivedFlags.map((flag, i) => (
                                      <Badge key={i} variant={getDerivedFlagVariant(flag)}>
                                        {getDerivedFlagLabel(flag)}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600">
                                {row.pay_date ? new Date(row.pay_date).toLocaleDateString('es-ES') : '—'}
                              </td>
                              <td className="py-3 px-4 text-sm text-slate-600">
                                {row.achieved_date ? new Date(row.achieved_date).toLocaleDateString('es-ES') : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <p className="text-slate-500">No hay datos de reconciliación</p>
                    </div>
                  )}

                  {/* Controles de paginación para Reconciliación */}
                  {rowsWithFlags.length > 0 && (
                    <div className="mt-4 flex items-center justify-between">
                      <p className="text-sm text-slate-500">
                        Mostrando {Math.min(reconPage * reconPerPage + 1, rowsWithFlags.length)} - {Math.min((reconPage + 1) * reconPerPage, rowsWithFlags.length)} de {rowsWithFlags.length} registros
                      </p>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setReconPage(p => Math.max(0, p - 1))}
                          disabled={reconPage === 0}
                          className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          ← Anterior
                        </button>
                        <span className="text-sm text-slate-600">
                          Página {reconPage + 1} de {Math.ceil(rowsWithFlags.length / reconPerPage)}
                        </span>
                        <button
                          onClick={() => setReconPage(p => Math.min(Math.ceil(rowsWithFlags.length / reconPerPage) - 1, p + 1))}
                          disabled={(reconPage + 1) * reconPerPage >= rowsWithFlags.length}
                          className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          Siguiente →
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
