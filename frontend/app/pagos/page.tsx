/**
 * Pagos - Elegibilidad
 * Diseño moderno consistente con el resto del sistema
 * 
 * Objetivo: "¿Qué pagos son elegibles y cumplen condiciones?"
 */

'use client';

import { useEffect, useState, useMemo } from 'react';
import { getPaymentEligibility, ApiError } from '@/lib/api';
import type { PaymentEligibilityResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import { PageLoadingOverlay } from '@/components/Skeleton';

// ============================================================================
// ICONS
// ============================================================================

const Icons = {
  money: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  x: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function PagosPage() {
  const [eligibility, setEligibility] = useState<PaymentEligibilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    origin_tag: '',
    rule_scope: '',
    is_payable: '',
    scout_id: '',
    driver_id: '',
    payable_from: '',
    payable_to: '',
    order_by: 'payable_date',
    order_dir: 'desc',
  });
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 25;

  useEffect(() => {
    async function loadEligibility() {
      try {
        setLoading(true);
        setError(null);

        const data = await getPaymentEligibility({
          origin_tag: filters.origin_tag || undefined,
          rule_scope: filters.rule_scope || undefined,
          is_payable: filters.is_payable ? filters.is_payable === 'true' : undefined,
          scout_id: filters.scout_id ? parseInt(filters.scout_id) : undefined,
          driver_id: filters.driver_id || undefined,
          payable_from: filters.payable_from || undefined,
          payable_to: filters.payable_to || undefined,
          order_by: filters.order_by as 'payable_date' | 'lead_date' | 'amount',
          order_dir: filters.order_dir as 'asc' | 'desc',
          limit: 500,
          offset: 0,
        });

        setEligibility(data);
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

    loadEligibility();
  }, [filters]);

  // Calcular estadísticas
  const stats = useMemo(() => {
    if (!eligibility?.rows) return { total: 0, payable: 0, notPayable: 0, totalAmount: 0 };
    
    const payable = eligibility.rows.filter(r => r.is_payable).length;
    const totalAmount = eligibility.rows.reduce((sum, r) => sum + (Number(r.amount) || 0), 0);
    
    return {
      total: eligibility.count,
      payable,
      notPayable: eligibility.rows.length - payable,
      totalAmount,
    };
  }, [eligibility]);

  // Paginación
  const paginatedRows = useMemo(() => {
    if (!eligibility?.rows) return [];
    const start = currentPage * pageSize;
    return eligibility.rows.slice(start, start + pageSize);
  }, [eligibility, currentPage]);

  const totalPages = Math.ceil((eligibility?.rows.length || 0) / pageSize);

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setCurrentPage(0);
  };

  const resetFilters = () => {
    setFilters({
      origin_tag: '',
      rule_scope: '',
      is_payable: '',
      scout_id: '',
      driver_id: '',
      payable_from: '',
      payable_to: '',
      order_by: 'payable_date',
      order_dir: 'desc',
    });
    setCurrentPage(0);
  };

  // Loading inicial
  if (loading && !eligibility) {
    return <PageLoadingOverlay title="Elegibilidad" subtitle="Cargando datos de pagos elegibles..." />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-1">Elegibilidad de Pagos</h1>
        <p className="text-slate-600">Consulta de pagos elegibles según condiciones y reglas</p>
      </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            title="Total Registros"
            value={stats.total.toLocaleString()}
            icon={Icons.money}
            variant="default"
          />
          <StatCard
            title="Pagables"
            value={stats.payable.toLocaleString()}
            subtitle={`${((stats.payable / (stats.total || 1)) * 100).toFixed(1)}% del total`}
            icon={Icons.check}
            variant="success"
          />
          <StatCard
            title="No Pagables"
            value={stats.notPayable.toLocaleString()}
            icon={Icons.x}
            variant="warning"
          />
          <StatCard
            title="Monto Total"
            value={`S/ ${stats.totalAmount.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`}
            icon={Icons.money}
            variant="info"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Origen</label>
              <select
                value={filters.origin_tag}
                onChange={(e) => handleFilterChange('origin_tag', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="">Todos</option>
                <option value="cabinet">Cabinet</option>
                <option value="fleet_migration">Fleet Migration</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Scope</label>
              <select
                value={filters.rule_scope}
                onChange={(e) => handleFilterChange('rule_scope', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="">Todos</option>
                <option value="scout">Scout</option>
                <option value="partner">Partner</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Es Pagable</label>
              <select
                value={filters.is_payable}
                onChange={(e) => handleFilterChange('is_payable', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="">Todos</option>
                <option value="true">Sí</option>
                <option value="false">No</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Driver ID</label>
              <input
                type="text"
                value={filters.driver_id}
                onChange={(e) => handleFilterChange('driver_id', e.target.value)}
                placeholder="Buscar..."
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Scout ID</label>
              <input
                type="number"
                value={filters.scout_id}
                onChange={(e) => handleFilterChange('scout_id', e.target.value)}
                placeholder="ID..."
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Payable Desde</label>
              <input
                type="date"
                value={filters.payable_from}
                onChange={(e) => handleFilterChange('payable_from', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Payable Hasta</label>
              <input
                type="date"
                value={filters.payable_to}
                onChange={(e) => handleFilterChange('payable_to', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Ordenar</label>
              <select
                value={filters.order_by}
                onChange={(e) => handleFilterChange('order_by', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="payable_date">Payable Date</option>
                <option value="lead_date">Lead Date</option>
                <option value="amount">Monto</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Dirección</label>
              <select
                value={filters.order_dir}
                onChange={(e) => handleFilterChange('order_dir', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              >
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={resetFilters}
                className="w-full px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                Limpiar
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {loading && eligibility && (
            <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
              <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Driver ID</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Origen</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Scope</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Trips</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Monto</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pagable</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Lead Date</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Payable Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedRows.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-slate-500">
                      No hay pagos elegibles que coincidan con los filtros
                    </td>
                  </tr>
                ) : (
                  paginatedRows.map((row, idx) => (
                    <tr key={`${row.driver_id}-${row.milestone_trips}-${idx}`} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4">
                        <span className="text-sm font-medium text-cyan-600">
                          {row.driver_id ? row.driver_id.substring(0, 16) + '...' : '—'}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={row.origin_tag === 'cabinet' ? 'info' : 'default'}>
                          {row.origin_tag || '—'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={row.rule_scope === 'partner' ? 'warning' : 'default'}>
                          {row.rule_scope || '—'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant={row.milestone_trips === 25 ? 'success' : row.milestone_trips === 5 ? 'warning' : 'info'}>
                          M{row.milestone_trips}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right text-sm font-medium text-slate-900">
                        {row.amount ? `S/ ${Number(row.amount).toFixed(2)}` : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant={row.is_payable ? 'success' : 'error'}>
                          {row.is_payable ? 'Sí' : 'No'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—'}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {row.payable_date ? new Date(row.payable_date).toLocaleDateString('es-ES') : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {eligibility && eligibility.rows.length > 0 && (
            <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
              <p className="text-sm text-slate-600">
                Mostrando {currentPage * pageSize + 1} - {Math.min((currentPage + 1) * pageSize, eligibility.rows.length)} de {eligibility.rows.length} registros
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                  disabled={currentPage === 0}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  ← Anterior
                </button>
                <span className="text-sm text-slate-600">
                  Página {currentPage + 1} de {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={currentPage >= totalPages - 1}
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
