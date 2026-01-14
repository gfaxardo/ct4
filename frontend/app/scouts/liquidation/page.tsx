/**
 * Scout Liquidation Base - Vista base para liquidación de scouts
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { getScoutLiquidationBase, ApiError } from '@/lib/api';
import type { ScoutLiquidationBaseResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Link from 'next/link';
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
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  download: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
  ),
};

export default function ScoutLiquidationPage() {
  const [data, setData] = useState<ScoutLiquidationBaseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const result = await getScoutLiquidationBase({ page, page_size: pageSize });
        setData(result);
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
  }, [page, pageSize]);

  if (loading && !data) {
    return <PageLoadingOverlay title="Liquidación de Scouts" subtitle="Cargando datos de liquidación..." />;
  }

  // Calcular KPIs
  const totalItems = data?.pagination.total || 0;
  const pendingCount = data?.items.filter(i => i.payment_status === 'PENDING').length || 0;
  const blockedCount = data?.items.filter(i => i.payment_status === 'BLOCKED').length || 0;
  const eligibleCount = data?.items.filter(i => i.payment_status === 'ELIGIBLE').length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Liquidación de Scouts</h1>
          <p className="text-slate-600">Vista base para liquidación diaria. <span className="text-amber-600 font-medium">NO ejecuta pagos.</span></p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (!data) return;
              const headers = ['person_key', 'driver_id', 'scout_id', 'origin_tag', 'milestone_reached', 'amount_payable', 'payment_status', 'block_reason'];
              const csv = [headers.join(','), ...data.items.map(i => headers.map(h => (i as Record<string, unknown>)[h] ?? '').join(','))].join('\n');
              const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `liquidacion-scouts-${new Date().toISOString().split('T')[0]}.csv`;
              a.click();
            }}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors text-sm font-medium"
          >
            {Icons.download} Exportar CSV
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

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Total Registros" value={totalItems.toLocaleString()} icon={Icons.users} variant="default" />
        <StatCard title="Pendientes" value={pendingCount.toLocaleString()} subtitle="PENDING" icon={Icons.clock} variant="warning" />
        <StatCard title="Bloqueados" value={blockedCount.toLocaleString()} subtitle="BLOCKED" icon={Icons.alert} variant="error" />
        <StatCard title="Elegibles" value={eligibleCount.toLocaleString()} subtitle="ELIGIBLE" icon={Icons.check} variant="success" />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        
        {!data || data.items.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-3 text-green-500">
              {Icons.check}
            </div>
            <p className="text-slate-600 font-medium">No hay registros pendientes</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Person Key</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Driver ID</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Scout</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Origin</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Milestone</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Monto</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Estado</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Razón Bloqueo</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.items.map((item, idx) => (
                    <tr key={`${item.person_key || idx}`} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4 text-sm font-mono text-slate-600">
                        {item.person_key ? item.person_key.substring(0, 8) + '...' : '—'}
                      </td>
                      <td className="py-3 px-4 text-sm font-mono text-slate-600">
                        {item.driver_id ? item.driver_id.substring(0, 12) + '...' : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {item.scout_id ? (
                          <Badge variant="info">Scout {item.scout_id}</Badge>
                        ) : (
                          <Badge variant="error">Sin scout</Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">{item.origin_tag || '—'}</td>
                      <td className="py-3 px-4 text-center">
                        {item.milestone_reached > 0 ? (
                          <Badge variant="success">M{item.milestone_reached}</Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right text-sm font-medium text-slate-700">
                        ${item.amount_payable.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant={
                          item.payment_status === 'ELIGIBLE' ? 'success' :
                          item.payment_status === 'PENDING' ? 'warning' :
                          item.payment_status === 'BLOCKED' ? 'error' : 'default'
                        }>
                          {item.payment_status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-500">
                        {item.block_reason || '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {item.person_key ? (
                          <Link href={`/persons/${item.person_key}`} className="text-cyan-600 hover:underline text-sm font-medium">
                            Ver →
                          </Link>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data.pagination.total_pages > 1 && (
              <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
                <span className="text-sm text-slate-600">
                  Página {page} de {data.pagination.total_pages} ({totalItems} registros)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ← Anterior
                  </button>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= data.pagination.total_pages}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Siguiente →
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
