/**
 * Scout Attribution Backlog - Backlog por Categorías
 */

'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { getScoutAttributionBacklog, ApiError } from '@/lib/api';
import type { ScoutAttributionBacklogResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import Link from 'next/link';

function ScoutBacklogContent() {
  const searchParams = useSearchParams();
  const category = searchParams.get('category') || '';
  
  const [backlog, setBacklog] = useState<ScoutAttributionBacklogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
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

    loadBacklog();
  }, [category, page]);

  if (loading) {
    return <div className="text-center py-12">Cargando...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!backlog) {
    return <div className="text-center py-12">No hay datos disponibles</div>;
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

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Backlog de Atribución Scout</h1>
          <p className="text-gray-600 mt-1">
            Registros pendientes por categoría
          </p>
        </div>
        <Link
          href="/scouts/attribution-health"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
        >
          ← Volver
        </Link>
      </div>

      {/* Category Filter */}
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => {
            setPage(1);
            window.history.pushState({}, '', '/scouts/backlog');
            window.location.reload();
          }}
          className={`px-4 py-2 rounded-md ${
            !category
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Todas
        </button>
        {['A', 'C', 'D'].map((cat) => (
          <button
            key={cat}
            onClick={() => {
              setPage(1);
              window.history.pushState({}, '', `/scouts/backlog?category=${cat}`);
              window.location.reload();
            }}
            className={`px-4 py-2 rounded-md ${
              category === cat
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {getCategoryLabel(cat)}
          </button>
        ))}
      </div>

      {backlog.backlog.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-800 text-lg">✅ No hay registros pendientes</p>
        </div>
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Categoría</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Person Key</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Scout ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Fuentes</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Eventos</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Primera Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {backlog.backlog.map((item) => (
                  <tr key={item.person_key} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Badge variant={getCategoryVariant(item.category)}>
                        {item.category}: {item.category_label}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">{item.person_key}</td>
                    <td className="px-4 py-3">
                      {item.scout_id ? (
                        <Badge variant="info">Scout {item.scout_id}</Badge>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {item.source_tables.join(', ')}
                    </td>
                    <td className="px-4 py-3 text-sm">{item.event_count}</td>
                    <td className="px-4 py-3 text-sm">
                      {item.first_event_date ? new Date(item.first_event_date).toLocaleDateString('es-ES') : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/persons/${item.person_key}`}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        Ver detalle →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {backlog.pagination.total_pages > 1 && (
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-600">
                Página {page} de {backlog.pagination.total_pages} ({backlog.pagination.total} total)
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= backlog.pagination.total_pages}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ScoutBacklogPage() {
  return (
    <Suspense fallback={<div className="text-center py-12">Cargando...</div>}>
      <ScoutBacklogContent />
    </Suspense>
  );
}
