/**
 * Scout Attribution Backlog - Backlog por Categorías
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getScoutAttributionBacklog, ApiError } from '@/lib/api';
import type { ScoutAttributionBacklogResponse } from '@/lib/types';
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
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  folder: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

function ScoutBacklogContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const category = searchParams.get('category') || '';
  
  const [backlog, setBacklog] = useState<ScoutAttributionBacklogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  async function loadBacklog() {
    try {
      setLoading(true);
      setError(null);
      const data = await getScoutAttributionBacklog({
        category: category || undefined,
        page,
        page_size: 50,
      });
      setBacklog(data);
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
    loadBacklog();
  }, [category, page]);

  if (loading && !backlog) {
    return <PageLoadingOverlay title="Backlog de Atribución" subtitle="Cargando registros pendientes..." />;
  }

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case 'A': return 'Eventos sin Scout';
      case 'C': return 'Legacy';
      case 'D': return 'Scout no Propagado';
      default: return cat;
    }
  };

  const getCategoryVariant = (cat: string): 'default' | 'warning' | 'error' | 'info' => {
    switch (cat) {
      case 'A': return 'warning';
      case 'C': return 'default';
      case 'D': return 'info';
      default: return 'default';
    }
  };

  const total = backlog?.pagination?.total || 0;
  const catA = backlog?.backlog?.filter(b => b.category === 'A').length || 0;
  const catC = backlog?.backlog?.filter(b => b.category === 'C').length || 0;
  const catD = backlog?.backlog?.filter(b => b.category === 'D').length || 0;

  const handleCategoryChange = (cat: string) => {
    setPage(1);
    if (cat) {
      router.push(`/scouts/backlog?category=${cat}`);
    } else {
      router.push('/scouts/backlog');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Backlog de Atribución</h1>
          <p className="text-slate-600">Registros pendientes de scout por categoría</p>
        </div>
        <button
          onClick={loadBacklog}
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
          title="Total Pendientes"
          value={total.toLocaleString()}
          subtitle="registros"
          icon={Icons.folder}
          variant={total === 0 ? 'success' : 'warning'}
        />
        <StatCard
          title="A: Sin Scout"
          value={catA.toLocaleString()}
          subtitle="eventos sin scout_id"
          icon={Icons.alert}
          variant={catA === 0 ? 'success' : 'warning'}
        />
        <StatCard
          title="C: Legacy"
          value={catC.toLocaleString()}
          subtitle="sin eventos ni scout"
          icon={Icons.clock}
          variant="default"
        />
        <StatCard
          title="D: No Propagado"
          value={catD.toLocaleString()}
          subtitle="scout no en ledger"
          icon={Icons.folder}
          variant="info"
        />
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2">
        {[
          { key: '', label: 'Todas' },
          { key: 'A', label: 'A: Sin Scout' },
          { key: 'C', label: 'C: Legacy' },
          { key: 'D', label: 'D: No Propagado' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleCategoryChange(tab.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              category === tab.key
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {!backlog || backlog.backlog.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4 text-green-500">
              {Icons.check}
            </div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">¡Sin pendientes!</h3>
            <p className="text-slate-500">No hay registros en el backlog{category ? ` para categoría ${category}` : ''}</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Categoría</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Person Key</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Scout</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Fuentes</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Eventos</th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Primera Fecha</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {backlog.backlog.map((item) => (
                    <tr key={item.person_key} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-4">
                        <Badge variant={getCategoryVariant(item.category)}>
                          {item.category}: {getCategoryLabel(item.category)}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-sm font-mono text-slate-600">
                        {item.person_key.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4 text-center">
                        {item.scout_id ? (
                          <Badge variant="info">Scout {item.scout_id}</Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {item.source_tables?.join(', ') || '—'}
                      </td>
                      <td className="py-3 px-4 text-center text-sm font-medium text-slate-700">
                        {item.event_count}
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600">
                        {item.first_event_date ? new Date(item.first_event_date).toLocaleDateString('es-ES') : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Link href={`/persons/${item.person_key}`} className="text-cyan-600 hover:underline text-sm font-medium">
                          Ver →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {backlog.pagination.total_pages > 1 && (
              <div className="border-t border-slate-200 px-4 py-3 flex items-center justify-between bg-slate-50">
                <span className="text-sm text-slate-600">
                  Página {page} de {backlog.pagination.total_pages} ({total} registros)
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
                    disabled={page >= backlog.pagination.total_pages}
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

export default function ScoutBacklogPage() {
  return (
    <Suspense fallback={<PageLoadingOverlay title="Backlog de Atribución" subtitle="Preparando interfaz..." />}>
      <ScoutBacklogContent />
    </Suspense>
  );
}
