/**
 * MvHealthPanel - Panel para mostrar salud de Materialized Views
 * 
 * Muestra tabla con información de MVs: schema, nombre, tamaño, último refresh, estado
 * Filtros: schema_name, stale_only
 */

'use client';

import { useState, useEffect } from 'react';
import {
  getOpsMvHealth,
  ApiError,
} from '@/lib/api';
import type {
  MvHealthResponse,
  MvHealthRow,
} from '@/lib/types';
import DataTable from '@/components/DataTable';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

const DEFAULT_LIMIT = 50;
const DEFAULT_OFFSET = 0;

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('es-ES');
  } catch {
    return dateStr;
  }
}

function formatSize(sizeMb: number | null): string {
  if (sizeMb === null || sizeMb === undefined) return '—';
  if (sizeMb < 1) return `${(sizeMb * 1024).toFixed(2)} KB`;
  if (sizeMb < 1024) return `${sizeMb.toFixed(2)} MB`;
  return `${(sizeMb / 1024).toFixed(2)} GB`;
}

function formatMinutes(minutes: number | null): string {
  if (minutes === null || minutes === undefined) return '—';
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`;
}

function getRefreshStatusBadge(
  status: string | null,
  minutesSinceRefresh: number | null,
  isPopulated: boolean | null
) {
  if (isPopulated === false) {
    return <Badge variant="error">No poblada</Badge>;
  }
  
  if (status === 'FAILED') {
    return <Badge variant="error">FAILED</Badge>;
  }
  
  if (status === 'SUCCESS') {
    if (minutesSinceRefresh === null) {
      return <Badge variant="warning">Sin refresh</Badge>;
    }
    if (minutesSinceRefresh > 1440) {
      return <Badge variant="warning">Stale</Badge>;
    }
    return <Badge variant="success">OK</Badge>;
  }
  
  // Sin status (no hay log)
  if (minutesSinceRefresh === null) {
    return <Badge variant="warning">Sin log</Badge>;
  }
  
  if (minutesSinceRefresh > 1440) {
    return <Badge variant="warning">Stale</Badge>;
  }
  
  return <Badge variant="success">OK</Badge>;
}

export default function MvHealthPanel() {
  const [data, setData] = useState<MvHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schemaName, setSchemaName] = useState('');
  const [staleOnly, setStaleOnly] = useState(false);
  const [offset, setOffset] = useState(DEFAULT_OFFSET);
  const [retryKey, setRetryKey] = useState(0);

  // Load data
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const response = await getOpsMvHealth({
          limit: DEFAULT_LIMIT,
          offset,
          schema_name: schemaName || undefined,
          stale_only: staleOnly || undefined,
        });
        if (!cancelled) {
          setData(response);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setError(`Error ${err.status}: ${err.detail || err.message}`);
          } else {
            setError('Error desconocido');
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [offset, schemaName, staleOnly, retryKey]);

  const columns = [
    {
      key: 'schema_name',
      header: 'Schema',
    },
    {
      key: 'mv_name',
      header: 'MV Name',
    },
    {
      key: 'size_mb',
      header: 'Tamaño',
      render: (row: MvHealthRow) => formatSize(row.size_mb),
    },
    {
      key: 'is_populated',
      header: 'Poblada',
      render: (row: MvHealthRow) => (
        <Badge variant={row.is_populated ? 'success' : 'error'}>
          {row.is_populated ? 'Sí' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'last_refresh_at',
      header: 'Último Refresh',
      render: (row: MvHealthRow) => formatDateTime(row.last_refresh_at),
    },
    {
      key: 'minutes_since_refresh',
      header: 'Hace',
      render: (row: MvHealthRow) => formatMinutes(row.minutes_since_refresh),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row: MvHealthRow) => getRefreshStatusBadge(
        row.last_refresh_status,
        row.minutes_since_refresh,
        row.is_populated
      ),
    },
    {
      key: 'last_refresh_error',
      header: 'Error',
      render: (row: MvHealthRow) => row.last_refresh_error || '—',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Schema
            </label>
            <input
              type="text"
              value={schemaName}
              onChange={(e) => {
                setSchemaName(e.target.value);
                setOffset(0);
              }}
              placeholder="ops, canon..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={staleOnly}
                onChange={(e) => {
                  setStaleOnly(e.target.checked);
                  setOffset(0);
                }}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Solo stale (&gt;24h o sin refresh)
              </span>
            </label>
          </div>
          <div className="flex items-end justify-end">
            <button
              onClick={() => setRetryKey((k) => k + 1)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Actualizar
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Tabla */}
      {loading && !data && (
        <div className="text-center py-12">Cargando...</div>
      )}

      {data && (
        <>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <DataTable
              columns={columns}
              data={data.items}
              loading={loading}
            />
          </div>

          {/* Paginación */}
          {data.total > DEFAULT_LIMIT && (
            <Pagination
              total={data.total}
              limit={DEFAULT_LIMIT}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
            />
          )}

          {/* Resumen */}
          <div className="text-sm text-gray-600">
            Mostrando {data.items.length} de {data.total} MVs
          </div>
        </>
      )}
    </div>
  );
}
