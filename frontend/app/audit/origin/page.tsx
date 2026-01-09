'use client';

import { useEffect, useState } from 'react';
import { getOriginAudit, getOriginAuditStats, ApiError } from '@/lib/api';
import type { OriginAuditRow, OriginAuditStats } from '@/lib/types';
import Link from 'next/link';

export default function OriginAuditPage() {
  const [data, setData] = useState<{ items: OriginAuditRow[]; total: number } | null>(null);
  const [stats, setStats] = useState<OriginAuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    violation_flag: undefined as boolean | undefined,
    violation_reason: '',
    resolution_status: '',
    origin_tag: '',
  });
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [auditData, statsData] = await Promise.all([
          getOriginAudit({
            ...filters,
            skip: page * limit,
            limit,
          }),
          getOriginAuditStats(),
        ]);

        setData(auditData);
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

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Auditoría de Origen Canónico</h1>

      {/* KPIs */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Total Personas</h3>
            <p className="text-3xl font-bold">{stats.total_persons}</p>
          </div>
          <div className="bg-red-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Con Violaciones</h3>
            <p className="text-3xl font-bold text-red-700">{stats.persons_with_violations}</p>
          </div>
          <div className="bg-yellow-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Alta Severidad</h3>
            <p className="text-3xl font-bold text-yellow-700">{stats.alerts_by_severity.high || 0}</p>
          </div>
          <div className="bg-green-50 rounded-lg shadow p-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Resueltas</h3>
            <p className="text-3xl font-bold text-green-700">
              {(stats.resolution_status_distribution.resolved_auto || 0) +
               (stats.resolution_status_distribution.resolved_manual || 0)}
            </p>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Filtros</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Violación
            </label>
            <select
              value={filters.violation_flag === undefined ? '' : filters.violation_flag.toString()}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  violation_flag: e.target.value === '' ? undefined : e.target.value === 'true',
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todos</option>
              <option value="true">Con Violación</option>
              <option value="false">Sin Violación</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Razón de Violación
            </label>
            <select
              value={filters.violation_reason}
              onChange={(e) => setFilters({ ...filters, violation_reason: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todas</option>
              <option value="missing_origin">Missing Origin</option>
              <option value="multiple_origins">Multiple Origins</option>
              <option value="late_origin_link">Late Origin Link</option>
              <option value="orphan_lead">Orphan Lead</option>
              <option value="legacy_driver_unclassified">Legacy Unclassified</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Estado de Resolución
            </label>
            <select
              value={filters.resolution_status}
              onChange={(e) => setFilters({ ...filters, resolution_status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todos</option>
              <option value="pending_review">Pending Review</option>
              <option value="resolved_auto">Resolved Auto</option>
              <option value="resolved_manual">Resolved Manual</option>
              <option value="marked_legacy">Marked Legacy</option>
              <option value="discarded">Discarded</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Origen
            </label>
            <select
              value={filters.origin_tag}
              onChange={(e) => setFilters({ ...filters, origin_tag: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Todos</option>
              <option value="cabinet_lead">Cabinet Lead</option>
              <option value="scout_registration">Scout Registration</option>
              <option value="migration">Migration</option>
              <option value="legacy_external">Legacy External</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabla de Auditoría */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Origen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Violación</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acción</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.items.map((row) => (
                <tr
                  key={row.person_key}
                  className={row.violation_flag ? 'bg-red-50' : 'bg-white'}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/audit/origin/${row.person_key}`}
                      className="text-blue-600 hover:underline"
                    >
                      {row.person_key.substring(0, 8)}...
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{row.driver_id || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {row.origin_tag ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        {row.origin_tag}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {row.resolution_status ? (
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          row.resolution_status === 'resolved_auto' || row.resolution_status === 'resolved_manual'
                            ? 'bg-green-100 text-green-800'
                            : row.resolution_status === 'pending_review'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {row.resolution_status}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {row.violation_flag ? (
                      <div>
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                          {row.violation_reason || 'Violación'}
                        </span>
                        {row.recommended_action && (
                          <div className="text-xs text-gray-600 mt-1">
                            Acción: {row.recommended_action}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-green-600">Sin violación</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link
                      href={`/audit/origin/${row.person_key}`}
                      className="text-blue-600 hover:underline"
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

