/**
 * Scout Attribution Conflicts - Conflictos de Atribución
 */

'use client';

import { useEffect, useState } from 'react';
import { getScoutAttributionConflicts, ApiError } from '@/lib/api';
import type { ScoutAttributionConflictsResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function ScoutConflictsPage() {
  const [conflicts, setConflicts] = useState<ScoutAttributionConflictsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
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

    loadConflicts();
  }, [page]);

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

  if (!conflicts) {
    return <div className="text-center py-12">No hay datos disponibles</div>;
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Conflictos de Atribución Scout</h1>
          <p className="text-gray-600 mt-1">
            Personas con múltiples scouts asignados
          </p>
        </div>
        <Link
          href="/scouts/attribution-health"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
        >
          ← Volver
        </Link>
      </div>

      {conflicts.conflicts.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-800 text-lg">✅ No hay conflictos</p>
        </div>
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Person Key</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Scouts</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Fuentes</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Primera Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Última Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {conflicts.conflicts.map((conflict) => (
                  <tr key={conflict.person_key} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono">{conflict.person_key}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {conflict.scout_ids.map((scoutId) => (
                          <Badge key={scoutId} variant="warning">
                            Scout {scoutId}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {conflict.sources.join(', ')}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {conflict.first_event_date ? new Date(conflict.first_event_date).toLocaleDateString('es-ES') : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {conflict.last_event_date ? new Date(conflict.last_event_date).toLocaleDateString('es-ES') : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/persons/${conflict.person_key}`}
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

          {conflicts.pagination.total_pages > 1 && (
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-600">
                Página {page} de {conflicts.pagination.total_pages}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= conflicts.pagination.total_pages}
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

