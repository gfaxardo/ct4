/**
 * Cobranza Yango con Scout - Claims de cobranza con información de scout
 */

'use client';

import { useEffect, useState } from 'react';
import { getYangoCollectionWithScout, ApiError } from '@/lib/api';
import type { YangoCollectionWithScoutResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function ScoutCobranzaYangoPage() {
  const [data, setData] = useState<YangoCollectionWithScoutResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    scout_missing_only: false,
    conflicts_only: false,
  });

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        
        const result = await getYangoCollectionWithScout({
          page,
          page_size: 50,
          ...filters,
        });
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
  }, [page, filters]);

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

  if (!data) {
    return <div className="text-center py-12">No hay datos disponibles</div>;
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Cobranza Yango (con Scout)</h1>
          <p className="text-gray-600 mt-1">
            Claims de cobranza con información de atribución scout
          </p>
        </div>
        <Link
          href="/scouts/attribution-health"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
        >
          ← Volver
        </Link>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-2">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.scout_missing_only}
            onChange={(e) => {
              setFilters({ ...filters, scout_missing_only: e.target.checked });
              setPage(1);
            }}
            className="rounded"
          />
          <span className="text-sm">Solo missing scout</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={filters.conflicts_only}
            onChange={(e) => {
              setFilters({ ...filters, conflicts_only: e.target.checked });
              setPage(1);
            }}
            className="rounded"
          />
          <span className="text-sm">Solo conflictos</span>
        </label>
      </div>

      {data.items.length === 0 ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-800 text-lg">✅ No hay registros</p>
        </div>
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Driver ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Nombre</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Milestone</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Scout</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Calidad</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Monto</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Estado Pago</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.items.map((item, idx) => (
                  <tr key={`${item.driver_id}-${item.milestone_value}-${idx}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono">{item.driver_id}</td>
                    <td className="px-4 py-3 text-sm">{item.driver_name || '-'}</td>
                    <td className="px-4 py-3">
                      <Badge variant="info">M{item.milestone_value}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      {item.scout_id ? (
                        <Badge variant={item.is_scout_resolved ? 'success' : 'warning'}>
                          Scout {item.scout_id}
                        </Badge>
                      ) : (
                        <Badge variant="error">Sin scout</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          item.scout_quality_bucket === 'SATISFACTORY_LEDGER' ? 'success' :
                          item.scout_quality_bucket === 'MISSING' ? 'error' : 'warning'
                        }
                      >
                        {item.scout_quality_bucket || 'N/A'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      ${item.expected_amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          item.yango_payment_status === 'PAID' ? 'success' :
                          item.yango_payment_status === 'UNPAID' ? 'warning' : 'default'
                        }
                      >
                        {item.yango_payment_status || '-'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {item.person_key ? (
                        <Link
                          href={`/persons/${item.person_key}`}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          Ver detalle →
                        </Link>
                      ) : (
                        <span className="text-gray-400 text-sm">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.pagination.total_pages > 1 && (
            <div className="mt-4 flex justify-between items-center">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-600">
                Página {page} de {data.pagination.total_pages} ({data.pagination.total} total)
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.pagination.total_pages}
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

