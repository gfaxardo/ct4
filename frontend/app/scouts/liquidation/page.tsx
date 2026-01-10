/**
 * Scout Liquidation Base - Vista base para liquidación de scouts
 */

'use client';

import { useEffect, useState } from 'react';
import { getScoutLiquidationBase, ApiError } from '@/lib/api';
import type { ScoutLiquidationBaseResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function ScoutLiquidationPage() {
  const [data, setData] = useState<ScoutLiquidationBaseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        
        const result = await getScoutLiquidationBase({ page, page_size: 50 });
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

  if (!data) {
    return <div className="text-center py-12">No hay datos disponibles</div>;
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Liquidación Scouts (Base)</h1>
          <p className="text-gray-600 mt-1">
            Vista base para liquidación diaria de scouts. NO ejecuta pagos.
          </p>
        </div>
        <Link
          href="/scouts/attribution-health"
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
        >
          ← Volver
        </Link>
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
                  <th className="px-4 py-3 text-left text-sm font-semibold">Person Key</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Driver ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Scout ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Origin</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Milestone</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Monto</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Estado</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Razón Bloqueo</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.items.map((item, idx) => (
                  <tr key={`${item.person_key || idx}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono">
                      {item.person_key ? item.person_key.substring(0, 8) + '...' : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">{item.driver_id || '-'}</td>
                    <td className="px-4 py-3">
                      {item.scout_id ? (
                        <Badge variant="info">Scout {item.scout_id}</Badge>
                      ) : (
                        <Badge variant="error">Sin scout</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">{item.origin_tag || '-'}</td>
                    <td className="px-4 py-3">
                      {item.milestone_reached > 0 ? (
                        <Badge variant="success">M{item.milestone_reached}</Badge>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      ${item.amount_payable.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          item.payment_status === 'ELIGIBLE' ? 'success' :
                          item.payment_status === 'PENDING' ? 'warning' :
                          item.payment_status === 'BLOCKED' ? 'error' : 'default'
                        }
                      >
                        {item.payment_status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {item.block_reason || '-'}
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
                Página {page} de {data.pagination.total_pages}
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

