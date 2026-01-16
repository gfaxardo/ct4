/**
 * Yango Cabinet Claims - Claims Exigibles
 * 
 * Objetivo: "¿Qué claims exigibles tenemos para cobrar a Yango?"
 */

'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getYangoCabinetClaimsToCollect,
  getYangoCabinetClaimDrilldown,
  ApiError,
} from '@/lib/api';
import type {
  YangoCabinetClaimRow,
  YangoCabinetClaimDrilldownResponse,
} from '@/lib/types';
import Badge from '@/components/Badge';
import Modal from '@/components/Modal';
import { PageLoadingOverlay, StandardPageSkeleton } from '@/components/Skeleton';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Icons
const MoneyIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const SearchIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

// Stat Card Component
function StatCard({ 
  title, 
  value, 
  subtitle, 
  color = 'cyan',
  icon 
}: { 
  title: string; 
  value: string | number; 
  subtitle?: string;
  color?: 'cyan' | 'red' | 'amber' | 'emerald' | 'slate';
  icon?: React.ReactNode;
}) {
  const colorClasses = {
    cyan: 'from-cyan-500/10 to-cyan-500/5 border-cyan-200/50',
    red: 'from-red-500/10 to-red-500/5 border-red-200/50',
    amber: 'from-amber-500/10 to-amber-500/5 border-amber-200/50',
    emerald: 'from-emerald-500/10 to-emerald-500/5 border-emerald-200/50',
    slate: 'from-slate-500/10 to-slate-500/5 border-slate-200/50',
  };
  
  const textColors = {
    cyan: 'text-cyan-600',
    red: 'text-red-600',
    amber: 'text-amber-600',
    emerald: 'text-emerald-600',
    slate: 'text-slate-600',
  };

  return (
    <div className={`relative overflow-hidden bg-gradient-to-br ${colorClasses[color]} rounded-xl border p-5 transition-all hover:shadow-md`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
          <p className={`text-3xl font-bold ${textColors[color]}`}>{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className={`p-2 rounded-lg bg-white/60 ${textColors[color]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}


export default function YangoCabinetClaimsPage() {
  const [filters, setFilters] = useState({
    date_from: '',
    date_to: '',
    milestone_value: '',
    search: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit] = useState(50);
  
  // Drilldown modal state
  const [selectedClaim, setSelectedClaim] = useState<YangoCabinetClaimRow | null>(null);
  const [showDrilldownModal, setShowDrilldownModal] = useState(false);

  // React Query for claims
  const { 
    data: claimsData, 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['claims-cabinet', filters, offset, limit],
    queryFn: () => getYangoCabinetClaimsToCollect({
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
      milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
      search: filters.search || undefined,
      limit,
      offset,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutos
  });

  // Drilldown query
  const { 
    data: drilldownData, 
    isLoading: drilldownLoading,
    error: drilldownError,
  } = useQuery({
    queryKey: ['claim-drilldown', selectedClaim?.driver_id, selectedClaim?.milestone_value, selectedClaim?.lead_date],
    queryFn: () => selectedClaim?.driver_id && selectedClaim?.milestone_value 
      ? getYangoCabinetClaimDrilldown(
          selectedClaim.driver_id,
          selectedClaim.milestone_value,
          selectedClaim.lead_date || undefined
        )
      : null,
    enabled: !!selectedClaim?.driver_id && !!selectedClaim?.milestone_value && showDrilldownModal,
    staleTime: 5 * 60 * 1000,
  });

  const claims = claimsData?.rows || [];
  const total = claimsData?.total || 0;

  // Calculate summary stats
  const stats = useMemo(() => {
    if (!claims.length) return { totalAmount: 0, avgDaysOverdue: 0, byMilestone: { m1: 0, m5: 0, m25: 0 } };
    
    const totalAmount = claims.reduce((sum, c) => sum + (Number(c.expected_amount) || 0), 0);
    const avgDaysOverdue = claims.reduce((sum, c) => sum + (c.days_overdue_yango || 0), 0) / claims.length;
    const byMilestone = {
      m1: claims.filter(c => c.milestone_value === 1).length,
      m5: claims.filter(c => c.milestone_value === 5).length,
      m25: claims.filter(c => c.milestone_value === 25).length,
    };
    
    return { totalAmount, avgDaysOverdue, byMilestone };
  }, [claims]);

  const handleRowClick = (row: YangoCabinetClaimRow) => {
    if (!row.driver_id || !row.milestone_value) return;
    setSelectedClaim(row);
    setShowDrilldownModal(true);
  };

  const handleExportCSV = () => {
    const searchParams = new URLSearchParams();
    if (filters.date_from) searchParams.set('date_from', filters.date_from);
    if (filters.date_to) searchParams.set('date_to', filters.date_to);
    if (filters.milestone_value) searchParams.set('milestone_value', filters.milestone_value);
    if (filters.search) searchParams.set('search', filters.search);
    const query = searchParams.toString();
    window.open(`${API_BASE_URL}/api/v1/yango/cabinet/claims/export${query ? `?${query}` : ''}`, '_blank');
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (isLoading && !claimsData) {
    return <PageLoadingOverlay title="Claims Cabinet" subtitle="Cargando claims exigibles..." />;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Claims Exigibles a Yango</h1>
          <p className="text-slate-500 mt-1">Claims UNPAID pendientes de cobro</p>
        </div>
        <button
          onClick={handleExportCSV}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-xl font-medium hover:from-emerald-600 hover:to-emerald-700 transition-all shadow-sm hover:shadow-md"
        >
          <DownloadIcon />
          Exportar CSV
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Claims"
          value={total.toLocaleString()}
          subtitle="Claims sin pagar"
          color="cyan"
          icon={<MoneyIcon />}
        />
        <StatCard
          title="Monto Total"
          value={`S/ ${stats.totalAmount.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
          subtitle="Por cobrar a Yango"
          color="red"
          icon={<MoneyIcon />}
        />
        <StatCard
          title="Días Vencidos Prom."
          value={Math.round(stats.avgDaysOverdue)}
          subtitle="Promedio de días"
          color="amber"
          icon={<AlertIcon />}
        />
        <StatCard
          title="Por Milestone"
          value={`${stats.byMilestone.m1}/${stats.byMilestone.m5}/${stats.byMilestone.m25}`}
          subtitle="M1 / M5 / M25"
          color="slate"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200/60 p-4 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Fecha Desde</label>
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Fecha Hasta</label>
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Milestone</label>
            <select
              value={filters.milestone_value}
              onChange={(e) => setFilters({ ...filters, milestone_value: e.target.value })}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 transition-all"
            >
              <option value="">Todos</option>
              <option value="1">M1 (S/25)</option>
              <option value="5">M5 (S/35)</option>
              <option value="25">M25 (S/100)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Buscar</label>
            <div className="relative">
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="Driver ID o nombre..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500/20 focus:border-cyan-500 transition-all"
              />
              <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                <SearchIcon />
              </div>
            </div>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilters({ date_from: '', date_to: '', milestone_value: '', search: '' });
                setOffset(0);
              }}
              className="w-full px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-all"
            >
              Limpiar
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-red-700 text-sm">{(error as ApiError)?.detail || 'Error al cargar claims'}</p>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/60">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Conductor</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Milestone</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Monto</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Fecha Lead</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Vencimiento</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Días Vencidos</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-32" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-12" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-20" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-24" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-24" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-16" /></td>
                    <td className="px-4 py-4"><div className="h-4 bg-slate-200 rounded w-20" /></td>
                  </tr>
                ))
              ) : claims.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                    No hay claims que coincidan con los filtros
                  </td>
                </tr>
              ) : (
                claims.map((claim, idx) => (
                  <tr
                    key={`${claim.driver_id}-${claim.milestone_value}-${idx}`}
                    onClick={() => handleRowClick(claim)}
                    className="hover:bg-slate-50/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-800 text-sm">{claim.driver_name || '—'}</p>
                        <p className="text-xs text-slate-400 font-mono">{claim.driver_id?.slice(0, 12)}...</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                        claim.milestone_value === 25 ? 'bg-purple-100 text-purple-700' :
                        claim.milestone_value === 5 ? 'bg-blue-100 text-blue-700' :
                        'bg-green-100 text-green-700'
                      }`}>
                        M{claim.milestone_value}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-slate-800">
                        S/ {Number(claim.expected_amount || 0).toFixed(2)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {claim.lead_date ? new Date(claim.lead_date).toLocaleDateString('es-PE') : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">
                      {claim.yango_due_date ? new Date(claim.yango_due_date).toLocaleDateString('es-PE') : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${
                        (claim.days_overdue_yango || 0) > 30 ? 'text-red-600' :
                        (claim.days_overdue_yango || 0) > 14 ? 'text-amber-600' :
                        'text-slate-600'
                      }`}>
                        {claim.days_overdue_yango ?? 0}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="error">UNPAID</Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-slate-200/60 flex items-center justify-between bg-slate-50/50">
            <p className="text-sm text-slate-500">
              Mostrando {offset + 1} - {Math.min(offset + limit, total)} de {total}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Anterior
              </button>
              <span className="px-3 py-1.5 text-sm text-slate-600">
                Página {currentPage} de {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Drilldown Modal - Usando Portal para overlay correcto */}
      <Modal
        isOpen={showDrilldownModal}
        onClose={() => {
          setShowDrilldownModal(false);
          setSelectedClaim(null);
        }}
        title={selectedClaim ? `Detalle: ${selectedClaim.driver_name} • M${selectedClaim.milestone_value}` : 'Detalle del Claim'}
        size="full"
      >
        <div className="p-6">
          {drilldownLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="relative w-12 h-12 mb-4">
                    <div className="absolute inset-0 border-4 border-slate-200 rounded-full" />
                    <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                  <p className="text-sm text-slate-500">Cargando detalles del claim...</p>
                </div>
              ) : drilldownError ? (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-red-700">{(drilldownError as ApiError)?.detail || 'Error al cargar detalles'}</p>
                </div>
              ) : drilldownData ? (
                <div className="space-y-6">
                  {/* Claim Info */}
                  {drilldownData.claim && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Información del Claim</h3>
                      <div className="bg-gradient-to-br from-slate-50 to-slate-100/50 rounded-xl p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs text-slate-400">Driver ID</span>
                          <p className="font-mono text-sm text-slate-700">{drilldownData.claim.driver_id || '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400">Nombre</span>
                          <p className="font-medium text-slate-700">{drilldownData.claim.driver_name || '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400">Milestone</span>
                          <p className="font-medium text-slate-700">M{drilldownData.claim.milestone_value}</p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400">Monto</span>
                          <p className="font-bold text-lg text-red-600">
                            S/ {Number(drilldownData.claim.expected_amount || 0).toFixed(2)}
                          </p>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400">Estado</span>
                          <div className="mt-1">
                            <Badge
                              variant={
                                drilldownData.claim.yango_payment_status === 'PAID' ? 'success' :
                                drilldownData.claim.yango_payment_status === 'PAID_MISAPPLIED' ? 'warning' : 'error'
                              }
                            >
                              {drilldownData.claim.yango_payment_status || 'UNPAID'}
                            </Badge>
                          </div>
                        </div>
                        <div>
                          <span className="text-xs text-slate-400">Días Vencidos</span>
                          <p className={`font-semibold ${(drilldownData.claim.days_overdue_yango || 0) > 14 ? 'text-red-600' : 'text-slate-700'}`}>
                            {drilldownData.claim.days_overdue_yango ?? 0} días
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Lead Cabinet Info */}
                  {drilldownData.lead_cabinet && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Lead Cabinet</h3>
                      <div className="bg-gradient-to-br from-cyan-50 to-cyan-100/50 rounded-xl p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs text-cyan-600">Source PK</span>
                          <p className="font-mono text-sm text-slate-700">{drilldownData.lead_cabinet.source_pk || '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-cyan-600">Match Rule</span>
                          <p className="font-medium text-slate-700">{drilldownData.lead_cabinet.match_rule || '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-cyan-600">Match Score</span>
                          <p className="font-medium text-slate-700">{drilldownData.lead_cabinet.match_score ?? '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-cyan-600">Confidence</span>
                          <p className="font-medium text-slate-700">{drilldownData.lead_cabinet.confidence_level || '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Reconciliation */}
                  {drilldownData.reconciliation && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Reconciliación</h3>
                      <div className="bg-gradient-to-br from-amber-50 to-amber-100/50 rounded-xl p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-xs text-amber-600">Estado</span>
                          <p className="font-medium text-slate-700">{drilldownData.reconciliation.reconciliation_status || '—'}</p>
                        </div>
                        <div>
                          <span className="text-xs text-amber-600">Match Method</span>
                          <p className="font-medium text-slate-700">{drilldownData.reconciliation.match_method || '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Misapplied Explanation */}
                  {drilldownData.misapplied_explanation && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Explicación</h3>
                      <div className="bg-gradient-to-br from-yellow-50 to-yellow-100/50 border border-yellow-200 rounded-xl p-4">
                        <p className="text-yellow-800 text-sm whitespace-pre-wrap">{drilldownData.misapplied_explanation}</p>
                      </div>
                    </div>
                  )}
                </div>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
