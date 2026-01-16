/**
 * Unmatched - Registros no resueltos del matching
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { getUnmatched, resolveUnmatched, ApiError } from '@/lib/api';
import type { IdentityUnmatched } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Pagination from '@/components/Pagination';
import Modal from '@/components/Modal';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  alert: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  inbox: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
    </svg>
  ),
  search: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  close: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  link: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  ),
};

export default function UnmatchedPage() {
  const [unmatched, setUnmatched] = useState<IdentityUnmatched[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    reason_code: '',
    status: 'OPEN',
  });
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [total, setTotal] = useState(0);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolvePersonKey, setResolvePersonKey] = useState('');
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  async function loadUnmatched() {
    try {
      setLoading(true);
      setError(null);
      const data = await getUnmatched({ ...filters, skip, limit });
      setUnmatched(data);
      setTotal(data.length === limit ? skip + limit + 1 : skip + data.length);
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
    loadUnmatched();
  }, [filters, skip, limit]);

  const handleResolve = async () => {
    if (!resolvingId || !resolvePersonKey) return;

    try {
      setResolving(true);
      await resolveUnmatched(resolvingId, { person_key: resolvePersonKey });
      await loadUnmatched();
      setShowResolveModal(false);
      setResolvePersonKey('');
      setResolvingId(null);
      setNotification({ type: 'success', message: 'Registro resuelto exitosamente' });
      setTimeout(() => setNotification(null), 3000);
    } catch (err) {
      if (err instanceof ApiError) {
        setNotification({ type: 'error', message: `Error: ${err.detail || err.message}` });
      } else {
        setNotification({ type: 'error', message: 'Error desconocido' });
      }
    } finally {
      setResolving(false);
    }
  };

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setSkip(0);
  };

  const handleClearFilters = () => {
    setFilters({ reason_code: '', status: 'OPEN' });
    setSkip(0);
  };

  if (loading && unmatched.length === 0) {
    return <PageLoadingOverlay title="Unmatched" subtitle="Cargando registros sin resolver..." />;
  }

  // Calcular KPIs
  const openCount = unmatched.filter(u => u.status === 'OPEN').length;
  const resolvedCount = unmatched.filter(u => u.status === 'RESOLVED').length;

  // Agrupar por razón
  const reasonCounts = unmatched.reduce((acc, u) => {
    acc[u.reason_code] = (acc[u.reason_code] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const topReason = Object.entries(reasonCounts).sort((a, b) => b[1] - a[1])[0];

  return (
    <div className="space-y-6">
      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${
          notification.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
        }`}>
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? Icons.check : Icons.alert}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Registros Sin Resolver</h1>
          <p className="text-slate-600">Registros que no pudieron ser matcheados automáticamente</p>
        </div>
        <button
          onClick={loadUnmatched}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors text-sm font-medium disabled:opacity-50"
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
          title="Total Registros"
          value={unmatched.length.toLocaleString()}
          subtitle="en esta página"
          icon={Icons.inbox}
          variant="default"
        />
        <StatCard
          title="Pendientes"
          value={openCount.toLocaleString()}
          subtitle="OPEN"
          icon={Icons.alert}
          variant="warning"
        />
        <StatCard
          title="Resueltos"
          value={resolvedCount.toLocaleString()}
          subtitle="RESOLVED"
          icon={Icons.check}
          variant="success"
        />
        <StatCard
          title="Razón Principal"
          value={topReason ? topReason[1].toString() : '—'}
          subtitle={topReason ? topReason[0].replace(/_/g, ' ') : 'N/A'}
          icon={Icons.alert}
          variant="error"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Código de Razón</label>
            <div className="relative">
              <input
                type="text"
                value={filters.reason_code}
                onChange={(e) => handleFilterChange('reason_code', e.target.value)}
                placeholder="NO_CANDIDATES, WEAK_MATCH..."
                className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
              <div className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">{Icons.search}</div>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Estado</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="OPEN">OPEN</option>
              <option value="RESOLVED">RESOLVED</option>
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
            <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {unmatched.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3 text-emerald-500">
              {Icons.check}
            </div>
            <p className="text-slate-600 font-medium">No hay registros sin resolver</p>
            <p className="text-sm text-slate-500 mt-1">Todos los registros han sido matcheados correctamente</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-16">ID</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Tabla Fuente</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">PK Fuente</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Razón</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-24">Estado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-28">Creado</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase w-24">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {unmatched.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 text-sm font-medium text-slate-900">
                      {record.id}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      <code className="px-1.5 py-0.5 bg-slate-100 rounded text-xs">
                        {record.source_table}
                      </code>
                    </td>
                    <td className="py-3 px-4 text-sm font-mono text-slate-600 max-w-xs truncate">
                      {record.source_pk}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        record.reason_code === 'NO_CANDIDATES' 
                          ? 'bg-red-100 text-red-700'
                          : record.reason_code === 'WEAK_MATCH_ONLY'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {record.reason_code.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={record.status === 'OPEN' ? 'warning' : 'success'}>
                        {record.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-500">
                      {new Date(record.created_at).toLocaleDateString('es-PE')}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {record.status === 'OPEN' ? (
                        <button
                          onClick={() => {
                            setResolvingId(record.id);
                            setShowResolveModal(true);
                          }}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
                        >
                          {Icons.link}
                          Resolver
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {unmatched.length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 bg-slate-50">
            <Pagination
              total={total}
              limit={limit}
              offset={skip}
              onPageChange={(newOffset) => setSkip(newOffset)}
            />
          </div>
        )}
      </div>

      {/* Resolve Modal - Usando Portal para overlay correcto */}
      <Modal
        isOpen={showResolveModal}
        onClose={() => {
          setShowResolveModal(false);
          setResolvePersonKey('');
          setResolvingId(null);
        }}
        title="Resolver Registro"
        size="md"
      >
        <div className="p-6">
          <p className="text-sm text-slate-600 mb-4">
            Ingresa el <code className="px-1.5 py-0.5 bg-slate-100 rounded">person_key</code> al cual 
            deseas vincular el registro #{resolvingId}.
          </p>
          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Person Key (UUID)
            </label>
            <input
              type="text"
              value={resolvePersonKey}
              onChange={(e) => setResolvePersonKey(e.target.value)}
              placeholder="123e4567-e89b-12d3-a456-426614174000"
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent text-sm font-mono"
            />
          </div>
        </div>
        <div className="flex gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200">
          <button
            onClick={handleResolve}
            disabled={!resolvePersonKey || resolving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resolving ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : Icons.link}
            {resolving ? 'Resolviendo...' : 'Resolver'}
          </button>
          <button
            onClick={() => {
              setShowResolveModal(false);
              setResolvePersonKey('');
              setResolvingId(null);
            }}
            className="px-4 py-2.5 bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300 transition-colors font-medium"
          >
            Cancelar
          </button>
        </div>
      </Modal>
    </div>
  );
}
