/**
 * Orphans - Drivers Huérfanos (Cuarentena)
 * 
 * Objetivo: "¿Qué drivers están en cuarentena sin leads asociados?"
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getOrphans, getOrphansMetrics, runOrphansFix, ApiError } from '@/lib/api';
import type { OrphanDriver, OrphansListResponse, OrphansMetricsResponse } from '@/lib/types';
import Badge from '@/components/Badge';

export default function OrphansPage() {
  const [orphans, setOrphans] = useState<OrphanDriver[]>([]);
  const [metrics, setMetrics] = useState<OrphansMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: '',
    detected_reason: '',
    driver_id: '',
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [fixRunning, setFixRunning] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [orphansData, metricsData] = await Promise.all([
        getOrphans({
          page,
          page_size: pageSize,
          status: filters.status || undefined,
          detected_reason: filters.detected_reason || undefined,
          driver_id: filters.driver_id || undefined,
        }),
        getOrphansMetrics(),
      ]);

      setOrphans(orphansData.orphans);
      setTotal(orphansData.total);
      setTotalPages(orphansData.total_pages);
      setMetrics(metricsData);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400) {
          setError('Filtros inválidos');
        } else if (err.status === 500) {
          setError('Error al cargar orphans');
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
    loadData();
  }, [page, pageSize, filters.status, filters.detected_reason, filters.driver_id]);

  // Auto-refresh si está habilitado
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadData();
      }, 30000); // Refresh cada 30 segundos
      setRefreshInterval(interval as unknown as number);
      return () => {
        if (refreshInterval) {
          clearInterval(refreshInterval as unknown as NodeJS.Timeout);
        }
      };
    } else {
      if (refreshInterval) {
        clearInterval(refreshInterval as unknown as NodeJS.Timeout);
        setRefreshInterval(null);
      }
    }
  }, [autoRefresh]);

  const handleRunFix = async (execute: boolean = false) => {
    try {
      setFixRunning(true);
      setError(null);
      const result = await runOrphansFix({ execute, limit: 100 });
      // Recargar datos después del fix
      if (result && !result.dry_run) {
        setTimeout(() => {
          loadData();
        }, 2000);
      }
      alert(`Fix ${execute ? 'ejecutado' : 'dry-run'} completado. Ver consola para detalles.`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error al ejecutar fix: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido al ejecutar fix');
      }
    } finally {
      setFixRunning(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      quarantined: 'bg-red-100 text-red-800',
      resolved_relinked: 'bg-green-100 text-green-800',
      resolved_created_lead: 'bg-blue-100 text-blue-800',
      purged: 'bg-gray-100 text-gray-800',
    };
    return (
      <Badge className={colors[status] || 'bg-gray-100 text-gray-800'}>
        {status.replace('_', ' ').toUpperCase()}
      </Badge>
    );
  };

  const getReasonBadge = (reason: string) => {
    const colors: Record<string, string> = {
      no_lead_no_events: 'bg-red-100 text-red-800',
      no_lead_has_events_repair_failed: 'bg-orange-100 text-orange-800',
      legacy_driver_without_origin: 'bg-yellow-100 text-yellow-800',
      manual_detection: 'bg-blue-100 text-blue-800',
    };
    return (
      <Badge className={colors[reason] || 'bg-gray-100 text-gray-800'}>
        {reason.replace(/_/g, ' ')}
      </Badge>
    );
  };

  if (loading && !orphans.length) {
    return <div className="text-center py-12">Cargando...</div>;
  }

  if (error && !orphans.length) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Drivers Huérfanos (Orphans)</h1>
        <div className="flex gap-2 items-center">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={() => loadData()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
          >
            Refrescar
          </button>
        </div>
      </div>

      {/* Métricas Resumidas */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
            <div className="text-sm text-gray-600 mb-1">Total</div>
            <div className="text-2xl font-bold text-gray-900">{metrics.total_orphans}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="text-sm text-gray-600 mb-1">En Cuarentena</div>
            <div className="text-2xl font-bold text-red-800">{metrics.quarantined}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="text-sm text-gray-600 mb-1">Resueltos</div>
            <div className="text-2xl font-bold text-green-800">
              {metrics.resolved_relinked + metrics.resolved_created_lead}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="text-sm text-gray-600 mb-1">Con Lead Events</div>
            <div className="text-2xl font-bold text-blue-800">{metrics.with_lead_events}</div>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select
              value={filters.status}
              onChange={(e) => {
                setFilters({ ...filters, status: e.target.value });
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todos</option>
              <option value="quarantined">Quarantined</option>
              <option value="resolved_relinked">Resolved (Relinked)</option>
              <option value="resolved_created_lead">Resolved (Created Lead)</option>
              <option value="purged">Purged</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Razón</label>
            <select
              value={filters.detected_reason}
              onChange={(e) => {
                setFilters({ ...filters, detected_reason: e.target.value });
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Todas</option>
              <option value="no_lead_no_events">No Lead, No Events</option>
              <option value="no_lead_has_events_repair_failed">Repair Failed</option>
              <option value="legacy_driver_without_origin">Legacy Driver</option>
              <option value="manual_detection">Manual Detection</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Driver ID</label>
            <input
              type="text"
              value={filters.driver_id}
              onChange={(e) => {
                setFilters({ ...filters, driver_id: e.target.value });
                setPage(1);
              }}
              placeholder="Buscar por driver_id..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={() => {
                setFilters({ status: '', detected_reason: '', driver_id: '' });
                setPage(1);
              }}
              className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
            >
              Limpiar Filtros
            </button>
          </div>
        </div>
      </div>

      {/* Acciones */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold mb-2">Acciones</h2>
            <p className="text-sm text-gray-600">
              Ejecutar script de limpieza para corregir drivers huérfanos
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleRunFix(false)}
              disabled={fixRunning}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              {fixRunning ? 'Ejecutando...' : 'Run Dry-Run'}
            </button>
            <button
              onClick={() => {
                if (confirm('¿Estás seguro de ejecutar el fix? Esto aplicará cambios en la base de datos.')) {
                  handleRunFix(true);
                }
              }}
              disabled={fixRunning}
              className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              {fixRunning ? 'Ejecutando...' : 'Ejecutar Fix'}
            </button>
          </div>
        </div>
      </div>

      {/* Tabla de Orphans */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold">
            Listado de Orphans ({total} total)
          </h2>
          {metrics && metrics.last_updated_at && (
            <div className="text-xs text-gray-500">
              Última actualización: {new Date(metrics.last_updated_at).toLocaleString()}
            </div>
          )}
        </div>
        {loading && orphans.length > 0 && (
          <div className="px-6 py-2 bg-blue-50 text-blue-800 text-sm">
            Actualizando...
          </div>
        )}
        {error && (
          <div className="px-6 py-2 bg-red-50 text-red-800 text-sm">
            {error}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Driver ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Person Key
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Razón
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Regla
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Lead Events
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Detected At
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orphans.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                    {loading ? 'Cargando...' : 'No se encontraron orphans con los filtros seleccionados'}
                  </td>
                </tr>
              ) : (
                orphans.map((orphan) => (
                  <tr key={orphan.driver_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {orphan.driver_id.substring(0, 20)}...
                      </code>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {orphan.person_key ? (
                        <Link
                          href={`/persons/${orphan.person_key}`}
                          className="text-blue-600 hover:text-blue-900 underline"
                        >
                          {orphan.person_key.substring(0, 8)}...
                        </Link>
                      ) : (
                        <span className="text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {getStatusBadge(orphan.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {getReasonBadge(orphan.detected_reason)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {orphan.creation_rule || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        {orphan.lead_events_count > 0 ? (
                          <span className="text-green-700 font-medium">
                            ✓ {orphan.lead_events_count}
                          </span>
                        ) : (
                          <span className="text-red-700 font-medium">✗ 0</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {new Date(orphan.detected_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {orphan.person_key && (
                        <Link
                          href={`/persons/${orphan.person_key}`}
                          className="text-blue-600 hover:text-blue-900 underline"
                        >
                          Ver Detalle
                        </Link>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {/* Paginación */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Mostrando {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, total)} de {total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed text-sm"
              >
                Anterior
              </button>
              <span className="px-4 py-2 text-sm text-gray-700">
                Página {page} de {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed text-sm"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Breakdown por Estado y Razón */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Desglose por Estado</h2>
            <div className="space-y-2">
              {Object.entries(metrics.by_status)
                .filter(([_, count]) => count > 0)
                .map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600 capitalize">{status.replace('_', ' ')}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Desglose por Razón</h2>
            <div className="space-y-2">
              {Object.entries(metrics.by_reason)
                .filter(([_, count]) => count > 0)
                .map(([reason, count]) => (
                  <div key={reason} className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">{reason.replace(/_/g, ' ')}</span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



