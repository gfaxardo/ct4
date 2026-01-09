'use client';

import { useEffect, useState } from 'react';
import { getOriginAlerts, getOriginAuditStats, ApiError } from '@/lib/api';
import type { OriginAlertRow, OriginAuditStats } from '@/lib/types';
import Link from 'next/link';

export default function OriginAlertsPage() {
  const [data, setData] = useState<{ items: OriginAlertRow[]; total: number } | null>(null);
  const [stats, setStats] = useState<OriginAuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    alert_type: '',
    severity: '',
    impact: '',
    resolved_only: false,
  });
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [alertsData, statsData] = await Promise.all([
          getOriginAlerts({
            ...filters,
            skip: page * limit,
            limit,
          }),
          getOriginAuditStats(),
        ]);

        setData(alertsData);
        setStats(statsData);
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
  }, [filters, page]);

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

  if (!data || !stats) {
    return <div className="text-center py-12">No hay datos disponibles</div>;
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'export':
      case 'collection':
        return 'text-red-700 font-bold';
      case 'reporting':
        return 'text-yellow-700';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Alertas de Origen</h1>

      {/* KPIs */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Total Alertas</h3>
            <p className="text-3xl font-bold">{data.total}</p>
          </div>
          <div className="bg-red-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Alta Severidad</h3>
            <p className="text-3xl font-bold text-red-700">{stats.alerts_by_severity.high || 0}</p>
          </div>
          <div className="bg-yellow-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Media Severidad</h3>
            <p className="text-3xl font-bold text-yellow-700">{stats.alerts_by_severity.medium || 0}</p>
          </div>
          <div className="bg-blue-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Baja Severidad</h3>
            <p className="text-3xl font-bold text-blue-700">{stats.alerts_by_severity.low || 0}</p>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de Alerta
            </label>
            <select
              value={filters.alert_type}
              onChange={(e) => setFilters({ ...filters, alert_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todos</option>
              <option value="missing_origin">Missing Origin</option>
              <option value="multiple_origins">Multiple Origins</option>
              <option value="legacy_unclassified">Legacy Unclassified</option>
              <option value="orphan_lead">Orphan Lead</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severidad
            </label>
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todas</option>
              <option value="high">Alta</option>
              <option value="medium">Media</option>
              <option value="low">Baja</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Impacto
            </label>
            <select
              value={filters.impact}
              onChange={(e) => setFilters({ ...filters, impact: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todos</option>
              <option value="export">Export</option>
              <option value="collection">Collection</option>
              <option value="reporting">Reporting</option>
              <option value="none">None</option>
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={filters.resolved_only}
                onChange={(e) => setFilters({ ...filters, resolved_only: e.target.checked })}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Solo resueltas</span>
            </label>
          </div>
        </div>
      </div>

      {/* Tabla de Alertas */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Severidad</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Impacto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acción Recomendada</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.items.map((alert) => (
                <tr
                  key={`${alert.person_key}-${alert.alert_type}`}
                  className={alert.severity === 'high' ? 'bg-red-50' : alert.severity === 'medium' ? 'bg-yellow-50' : 'bg-white'}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/audit/origin/${alert.person_key}`}
                      className="text-blue-600 hover:underline"
                    >
                      {alert.person_key.substring(0, 8)}...
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                      {alert.alert_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(alert.severity)}`}>
                      {alert.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={getImpactColor(alert.impact)}>
                      {alert.impact}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {alert.recommended_action || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {alert.is_resolved_or_muted ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        {alert.resolved_at ? 'Resuelta' : 'Silenciada'}
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                        Abierta
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/audit/origin/${alert.person_key}`}
                      className="text-blue-600 hover:underline mr-4"
                    >
                      Ver detalles
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paginación */}
      <div className="mt-6 flex justify-between items-center">
        <button
          onClick={() => setPage(Math.max(0, page - 1))}
          disabled={page === 0}
          className="px-4 py-2 bg-gray-200 rounded-md disabled:opacity-50"
        >
          Anterior
        </button>
        <span className="text-sm text-gray-600">
          Página {page + 1} de {Math.ceil(data.total / limit)} ({data.total} total)
        </span>
        <button
          onClick={() => setPage(page + 1)}
          disabled={data.items.length < limit}
          className="px-4 py-2 bg-gray-200 rounded-md disabled:opacity-50"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}

