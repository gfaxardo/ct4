/**
 * Unmatched - Registros no matcheados
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué registros no pudieron ser matcheados?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getUnmatched, resolveUnmatched, ApiError } from '@/lib/api';
import type { IdentityUnmatched, UnmatchedResolveRequest } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function UnmatchedPage() {
  const [unmatched, setUnmatched] = useState<IdentityUnmatched[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    reason_code: '',
    status: 'OPEN',
  });
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(100);
  const [total, setTotal] = useState(0);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolvePersonKey, setResolvePersonKey] = useState('');
  const [showResolveModal, setShowResolveModal] = useState(false);

  useEffect(() => {
    async function loadUnmatched() {
      try {
        setLoading(true);
        setError(null);

        const data = await getUnmatched({
          ...filters,
          skip,
          limit,
        });

        setUnmatched(data);
        setTotal(data.length === limit ? skip + limit + 1 : skip + data.length);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Estado inválido');
          } else if (err.status === 500) {
            setError('Error al cargar unmatched');
          } else {
            setError(`Error ${err.status}: ${err.detail || err.message}`);
          }
        } else {
          setError('Error desconocido');
        }
      } finally {
        setLoading(false);
      }
    }

    loadUnmatched();
  }, [filters, skip, limit]);

  const handleResolve = async () => {
    if (!resolvingId || !resolvePersonKey) return;

    try {
      await resolveUnmatched(resolvingId, { person_key: resolvePersonKey });
      // Recargar datos
      const data = await getUnmatched({ ...filters, skip, limit });
      setUnmatched(data);
      setShowResolveModal(false);
      setResolvePersonKey('');
      setResolvingId(null);
      alert('Registro resuelto exitosamente');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          alert('Registro no encontrado o Persona no encontrada');
        } else if (err.status === 500) {
          alert('Error al resolver unmatched');
        } else {
          alert(`Error ${err.status}: ${err.detail || err.message}`);
        }
      } else {
        alert('Error desconocido');
      }
    }
  };

  const filterFields = [
    {
      name: 'reason_code',
      label: 'Código de Razón',
      type: 'text' as const,
    },
    {
      name: 'status',
      label: 'Estado',
      type: 'select' as const,
      options: [
        { value: 'OPEN', label: 'OPEN' },
        { value: 'RESOLVED', label: 'RESOLVED' },
      ],
    },
  ];

  const columns = [
    { key: 'id', header: 'ID' },
    { key: 'source_table', header: 'Tabla Fuente' },
    { key: 'source_pk', header: 'PK Fuente' },
    { key: 'reason_code', header: 'Razón' },
    {
      key: 'status',
      header: 'Estado',
      render: (row: IdentityUnmatched) => (
        <Badge variant={row.status === 'OPEN' ? 'warning' : 'success'}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Creado',
      render: (row: IdentityUnmatched) => new Date(row.created_at).toLocaleDateString('es-ES'),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row: IdentityUnmatched) =>
        row.status === 'OPEN' ? (
          <button
            onClick={() => {
              setResolvingId(row.id);
              setShowResolveModal(true);
            }}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Resolver
          </button>
        ) : null,
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Unmatched</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => setFilters(values as typeof filters)}
        onReset={() => {
          setFilters({ reason_code: '', status: 'OPEN' });
          setSkip(0);
        }}
      />

      <DataTable
        data={unmatched}
        columns={columns}
        loading={loading}
        emptyMessage="No hay registros unmatched que coincidan con los filtros"
      />

      {!loading && unmatched.length > 0 && (
        <Pagination
          total={total}
          limit={limit}
          offset={skip}
          onPageChange={(newOffset) => setSkip(newOffset)}
        />
      )}

      {/* Resolve Modal */}
      {showResolveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Resolver Unmatched</h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Person Key (UUID)
              </label>
              <input
                type="text"
                value={resolvePersonKey}
                onChange={(e) => setResolvePersonKey(e.target.value)}
                placeholder="123e4567-e89b-12d3-a456-426614174000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleResolve}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Resolver
              </button>
              <button
                onClick={() => {
                  setShowResolveModal(false);
                  setResolvePersonKey('');
                  setResolvingId(null);
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
