/**
 * Scout Attribution Conflicts - Conflictos de Atribución
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { getScoutAttributionConflicts, ApiError } from '@/lib/api';
import type { ScoutAttributionConflictsResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Link from 'next/link';
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
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

export default function ScoutConflictsPage() {
  const [conflicts, setConflicts] = useState<ScoutAttributionConflictsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  async function loadConflicts() {
    try {
      setLoading(true);
      setError(null);
      const data = await getScoutAttributionConflicts({ page, page_size: 50 });
      setConflicts(data);
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
    loadConflicts();
  }, [page]);

  if (loading && !conflicts) {
    return <PageLoadingOverlay title="Conflictos de Atribución" subtitle="Buscando conflictos de scouts..." />;
  }

  const totalConflicts = conflicts?.conflicts?.length || 0;
  const totalPeople = conflicts?.pagination?.total || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Conflictos de Atribución</h1>
          <p className="text-slate-600">Personas con múltiples scouts asignados que requieren resolución manual</p>
        </div>
        <button
          onClick={loadConflicts}
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
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          title="Total Conflictos"
          value={totalPeople.toLocaleString()}
          subtitle="personas afectadas"
          icon={Icons.alert}
          variant={totalPeople === 0 ? 'success' : 'error'}
        />
        <StatCard
          title="Estado"
          value={totalPeople === 0 ? 'Limpio' : 'Atención'}
          subtitle={totalPeople === 0 ? 'Sin conflictos' : 'Requiere revisión'}
          icon={totalPeople === 0 ? Icons.check : Icons.alert}
          variant={totalPeople === 0 ? 'success' : 'warning'}
        />
        <StatCard
          title="Scouts Involucrados"
          value={totalConflicts > 0 ? conflicts?.conflicts?.reduce((sum, c) => sum + (c.scout_ids?.length || 0), 0).toLocaleString() || '0' : '0'}
          subtitle="scouts en conflicto"
          icon={Icons.users}
          variant="info"
        />
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {!conflicts || conflicts.conflicts.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4 text-green-500">
              {Icons.check}
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">¡Sin conflictos!</h3>
            <p className="text-slate-500">No hay personas con múltiples scouts asignados</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Person Key</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Scouts en Conflicto</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Fuentes</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Primera Fecha</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Última Fecha</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {conflicts.conflicts.map((conflict) => (
                    <tr key={conflict.person_key} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4 text-sm font-mono text-slate-600">
                        {conflict.person_key.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {conflict.scout_ids.map((scoutId) => (
                            <Badge key={scoutId} variant="warning">
                              Scout {scoutId}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {conflict.sources?.join(', ') || '—'}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {conflict.first_event_date ? new Date(conflict.first_event_date).toLocaleDateString('es-ES') : '—'}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {conflict.last_event_date ? new Date(conflict.last_event_date).toLocaleDateString('es-ES') : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Link href={`/persons/${conflict.person_key}`} className="text-[#ef0000] hover:underline text-sm font-medium">
                          Resolver →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {conflicts.pagination.total_pages > 1 && (
              <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
                <span className="text-sm text-slate-600">
                  Página {page} de {conflicts.pagination.total_pages}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    ← Anterior
                  </button>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= conflicts.pagination.total_pages}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-50"
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
