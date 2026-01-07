/**
 * Ops Alerts - Listado de alertas operacionales
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué alertas operacionales hay en el sistema?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getOpsAlerts, acknowledgeAlert, ApiError } from '@/lib/api';
import type { OpsAlertRow, AlertSeverity } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function OpsAlertsPage() {
  const [alerts, setAlerts] = useState<OpsAlertRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);
  const [filters, setFilters] = useState<{
    severity: string;
    acknowledged: string;
    week_label: string;
  }>({
    severity: '',
    acknowledged: '',
    week_label: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: {
        limit: number;
        offset: number;
        severity?: AlertSeverity;
        acknowledged?: boolean;
        week_label?: string;
      } = {
        limit,
        offset,
      };

      if (filters.severity) {
        params.severity = filters.severity as AlertSeverity;
      }

      if (filters.acknowledged) {
        params.acknowledged = filters.acknowledged === 'true';
      }

      if (filters.week_label) {
        params.week_label = filters.week_label;
      }

      const data = await getOpsAlerts(params);

      setAlerts(data.items);
      setTotal(data.total);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 500) {
          setError('Error al cargar alertas');
        } else {
          setError(`Error ${err.status}: ${err.detail || err.message}`);
        }
      } else {
        setError('Error desconocido');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [filters, offset, limit]);

  const handleAcknowledge = async (alertId: number) => {
    try {
      setAcknowledgingId(alertId);
      await acknowledgeAlert(alertId);
      // Refrescar listado manteniendo filtros y paginación
      await loadAlerts();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error al reconocer alerta: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido al reconocer alerta');
      }
    } finally {
      setAcknowledgingId(null);
    }
  };

  const filterFields = [
    {
      name: 'severity',
      label: 'Severidad',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: 'info', label: 'Info' },
        { value: 'warning', label: 'Warning' },
        { value: 'error', label: 'Error' },
      ],
    },
    {
      name: 'acknowledged',
      label: 'Reconocida',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: 'false', label: 'No' },
        { value: 'true', label: 'Sí' },
      ],
    },
    {
      name: 'week_label',
      label: 'Semana (YYYY-WNN)',
      type: 'text' as const,
      placeholder: 'Ej: 2025-W51',
    },
  ];

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSeverityBadgeVariant = (severity: AlertSeverity): 'success' | 'warning' | 'error' | 'info' => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'info';
    }
  };

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (row: OpsAlertRow) => (
        <span className="font-mono text-sm">{row.id}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Creada',
      render: (row: OpsAlertRow) => formatDate(row.created_at),
    },
    {
      key: 'severity',
      header: 'Severidad',
      render: (row: OpsAlertRow) => (
        <Badge variant={getSeverityBadgeVariant(row.severity)}>
          {row.severity.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: 'alert_type',
      header: 'Tipo',
      render: (row: OpsAlertRow) => (
        <span className="text-sm text-gray-700">{row.alert_type}</span>
      ),
    },
    {
      key: 'message',
      header: 'Mensaje',
      render: (row: OpsAlertRow) => (
        <span className="text-sm">{row.message}</span>
      ),
    },
    {
      key: 'week_label',
      header: 'Semana',
      render: (row: OpsAlertRow) => (
        <span className="text-sm font-mono">{row.week_label || '-'}</span>
      ),
    },
    {
      key: 'acknowledged',
      header: 'Reconocida',
      render: (row: OpsAlertRow) => (
        <span className="text-sm">{row.acknowledged ? 'Sí' : 'No'}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row: OpsAlertRow) => (
        !row.acknowledged ? (
          <button
            onClick={() => handleAcknowledge(row.id)}
            disabled={acknowledgingId === row.id}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {acknowledgingId === row.id ? 'Reconociendo...' : 'Reconocer'}
          </button>
        ) : (
          <span className="text-sm text-gray-400">-</span>
        )
      ),
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Alertas Operacionales</h1>

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
          setFilters({ severity: '', acknowledged: '', week_label: '' });
          setOffset(0);
        }}
      />

      <DataTable
        data={alerts}
        columns={columns}
        loading={loading}
        emptyMessage="No se encontraron alertas que coincidan con los filtros"
      />

      {!loading && alerts.length > 0 && (
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









