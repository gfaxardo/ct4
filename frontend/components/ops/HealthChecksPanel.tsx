/**
 * HealthChecksPanel - Panel para mostrar checks de salud del sistema
 * 
 * Tabla con badges y acciones (botón "Ver detalle" que navega a drilldown_url)
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getOpsHealthChecks, ApiError } from '@/lib/api';
import type { HealthCheckRow, HealthChecksResponse } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Badge from '@/components/Badge';

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'error':
      return <Badge variant="error">{severity}</Badge>;
    case 'warning':
      return <Badge variant="warning">{severity}</Badge>;
    case 'info':
      return <Badge variant="info">{severity}</Badge>;
    default:
      return <Badge>{severity}</Badge>;
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'OK':
      return <Badge variant="success">{status}</Badge>;
    case 'WARN':
      return <Badge variant="warning">{status}</Badge>;
    case 'ERROR':
      return <Badge variant="error">{status}</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
}

function formatDateTime(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString('es-ES');
  } catch {
    return dateStr;
  }
}

export default function HealthChecksPanel() {
  const router = useRouter();
  const [checks, setChecks] = useState<HealthCheckRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadChecks() {
      setLoading(true);
      setError(null);
      try {
        const response: HealthChecksResponse = await getOpsHealthChecks();
        setChecks(response.items);
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`Error: ${e.detail || e.statusText}`);
        } else {
          setError('Error desconocido al cargar checks');
        }
        console.error('Error loading health checks:', e);
      } finally {
        setLoading(false);
      }
    }

    loadChecks();
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <div className="text-gray-500">Cargando checks...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800 font-semibold mb-2">Error</div>
          <div className="text-red-700 text-sm">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (checks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <div className="text-gray-500">No hay checks disponibles</div>
        </div>
      </div>
    );
  }

  const columns = [
    {
      key: 'check_key' as const,
      header: 'Check',
      render: (row: HealthCheckRow) => (
        <span className="font-mono text-sm">{row.check_key}</span>
      ),
    },
    {
      key: 'severity' as const,
      header: 'Severidad',
      render: (row: HealthCheckRow) => getSeverityBadge(row.severity),
    },
    {
      key: 'status' as const,
      header: 'Estado',
      render: (row: HealthCheckRow) => getStatusBadge(row.status),
    },
    {
      key: 'message' as const,
      header: 'Mensaje',
      render: (row: HealthCheckRow) => (
        <span className="text-sm">{row.message}</span>
      ),
    },
    {
      key: 'last_evaluated_at' as const,
      header: 'Última Evaluación',
      render: (row: HealthCheckRow) => (
        <span className="text-sm text-gray-600">{formatDateTime(row.last_evaluated_at)}</span>
      ),
    },
    {
      key: 'actions' as const,
      header: 'Acciones',
      render: (row: HealthCheckRow) => {
        if (row.drilldown_url) {
          return (
            <button
              onClick={(e) => {
                e.stopPropagation();
                router.push(row.drilldown_url!);
              }}
              className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:border-gray-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Ver detalle
            </button>
          );
        }
        return <span className="text-gray-400 text-sm">—</span>;
      },
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="mb-4">
        <h2 className="text-xl font-semibold">Health Checks</h2>
        <p className="text-sm text-gray-600 mt-1">
          Checks de integridad del sistema (RAW data, MVs, identidad)
        </p>
      </div>

      <DataTable
        data={checks}
        columns={columns}
      />
    </div>
  );
}
