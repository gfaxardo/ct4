/**
 * Runs - Listado de corridas de identidad
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué corridas de identidad se han ejecutado?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getIdentityRuns, ApiError } from '@/lib/api';
import type { IdentityRunRow, IngestionRunStatus, IngestionJobType } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function RunsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<IdentityRunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<{
    status: string;
    job_type: string;
  }>({
    status: '',
    job_type: 'identity_run',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    async function loadRuns() {
      try {
        setLoading(true);
        setError(null);

        const params: {
          limit: number;
          offset: number;
          status?: IngestionRunStatus;
          job_type?: IngestionJobType;
        } = {
          limit,
          offset,
        };

        if (filters.status) {
          params.status = filters.status as IngestionRunStatus;
        }

        if (filters.job_type) {
          params.job_type = filters.job_type as IngestionJobType;
        }

        const data = await getIdentityRuns(params);

        setRuns(data.items);
        setTotal(data.total);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 500) {
            setError('Error al cargar corridas');
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

    loadRuns();
  }, [filters, offset, limit]);

  const filterFields = [
    {
      name: 'status',
      label: 'Estado',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: 'RUNNING', label: 'En Ejecución' },
        { value: 'COMPLETED', label: 'Completado' },
        { value: 'FAILED', label: 'Fallido' },
      ],
    },
    {
      name: 'job_type',
      label: 'Tipo de Job',
      type: 'select' as const,
      options: [
        { value: 'identity_run', label: 'Identity Run' },
        { value: 'drivers_index_refresh', label: 'Drivers Index Refresh' },
      ],
    },
  ];

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadgeVariant = (status: IngestionRunStatus): 'success' | 'warning' | 'error' | 'info' => {
    switch (status) {
      case 'COMPLETED':
        return 'success';
      case 'RUNNING':
        return 'info';
      case 'FAILED':
        return 'error';
      default:
        return 'warning';
    }
  };

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (row: IdentityRunRow) => (
        <button
          onClick={() => router.push(`/runs/${row.id}`)}
          className="text-blue-600 hover:text-blue-800 underline font-mono"
        >
          {row.id}
        </button>
      ),
    },
    {
      key: 'started_at',
      header: 'Inicio',
      render: (row: IdentityRunRow) => formatDate(row.started_at),
    },
    {
      key: 'completed_at',
      header: 'Fin',
      render: (row: IdentityRunRow) => formatDate(row.completed_at),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row: IdentityRunRow) => (
        <Badge variant={getStatusBadgeVariant(row.status)}>
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'job_type',
      header: 'Tipo',
      render: (row: IdentityRunRow) => (
        <span className="text-sm text-gray-600">{row.job_type}</span>
      ),
    },
    {
      key: 'incremental',
      header: 'Incremental',
      render: (row: IdentityRunRow) => (
        <span className="text-sm">{row.incremental ? 'Sí' : 'No'}</span>
      ),
    },
    {
      key: 'cabinet_processed',
      header: 'Cabinet: Procesados',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono">
          {row.stats?.cabinet_leads?.processed ?? '-'}
        </span>
      ),
    },
    {
      key: 'cabinet_matched',
      header: 'Cabinet: Matched',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono text-green-600">
          {row.stats?.cabinet_leads?.matched ?? '-'}
        </span>
      ),
    },
    {
      key: 'cabinet_unmatched',
      header: 'Cabinet: Unmatched',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono text-red-600">
          {row.stats?.cabinet_leads?.unmatched ?? '-'}
        </span>
      ),
    },
    {
      key: 'scouting_processed',
      header: 'Scouting: Procesados',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono">
          {row.stats?.scouting_daily?.processed ?? '-'}
        </span>
      ),
    },
    {
      key: 'scouting_matched',
      header: 'Scouting: Matched',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono text-green-600">
          {row.stats?.scouting_daily?.matched ?? '-'}
        </span>
      ),
    },
    {
      key: 'scouting_unmatched',
      header: 'Scouting: Unmatched',
      render: (row: IdentityRunRow) => (
        <span className="text-sm font-mono text-red-600">
          {row.stats?.scouting_daily?.unmatched ?? '-'}
        </span>
      ),
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Corridas de Identidad</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => {
          setFilters(values as typeof filters);
          setOffset(0); // Reset offset when filters change
        }}
        onReset={() => {
          setFilters({ status: '', job_type: 'identity_run' });
          setOffset(0);
        }}
      />

      <DataTable
        data={runs}
        columns={columns}
        loading={loading}
        emptyMessage="No se encontraron corridas que coincidan con los filtros"
      />

      {!loading && runs.length > 0 && (
        <Pagination
          total={total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}
