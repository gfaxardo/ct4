/**
 * IdentitySystemHealthPanel - Panel reutilizable para mostrar salud del sistema de identidad
 * Extraído de /ops/data-health para reutilización en /ops/health
 */

'use client';

import { useEffect, useState } from 'react';
import { getOpsDataHealth, ApiError } from '@/lib/api';
import type { IdentitySystemHealthRow } from '@/lib/types';
import StatCard from '@/components/StatCard';
import Badge from '@/components/Badge';

export default function IdentitySystemHealthPanel() {
  const [health, setHealth] = useState<IdentitySystemHealthRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const data = await getOpsDataHealth();
        setHealth(data);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Error ${err.status}: ${err.detail || err.message}`);
        } else {
          setError('Error desconocido al cargar salud del sistema');
        }
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="text-center py-12">Cargando...</div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="text-center py-12">No hay datos disponibles</div>
    );
  }

  // Calcular estado general (solo visual)
  const getOverallStatus = (): 'OK' | 'WARNING' | 'ERROR' => {
    const hasNoAlerts = health.active_alerts_count === 0;
    const hoursSinceLastRun = health.hours_since_last_completed_run;
    const isRecentRun = hoursSinceLastRun === null || hoursSinceLastRun <= 24;
    const isNotFailed = health.last_run_status !== 'FAILED';
    
    // ERROR: last_run_status='FAILED' OR hours_since_last_completed_run>72
    if (health.last_run_status === 'FAILED' || (hoursSinceLastRun !== null && hoursSinceLastRun > 72)) {
      return 'ERROR';
    }
    
    // WARNING: active_alerts_count>0 OR hours_since_last_completed_run>24
    if (health.active_alerts_count > 0 || (hoursSinceLastRun !== null && hoursSinceLastRun > 24)) {
      return 'WARNING';
    }
    
    // OK: active_alerts_count=0 AND (hours_since_last_completed_run is null OR <=24) AND last_run_status!='FAILED'
    if (hasNoAlerts && isRecentRun && isNotFailed) {
      return 'OK';
    }
    
    return 'WARNING';
  };

  const overallStatus = getOverallStatus();
  const statusVariant = overallStatus === 'OK' ? 'success' : overallStatus === 'WARNING' ? 'warning' : 'error';

  return (
    <div>
      {/* StatCards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          title="Estado General"
          value={<Badge variant={statusVariant}>{overallStatus}</Badge>}
        />
        <StatCard
          title="Última Corrida"
          value={health.last_run_id ? `#${health.last_run_id}` : '-'}
          subtitle={health.last_run_status}
        />
        <StatCard
          title="Última Completada"
          value={
            health.last_run_completed_at
              ? new Date(health.last_run_completed_at).toLocaleString('es-ES')
              : '-'
          }
        />
        <StatCard
          title="Horas desde Última"
          value={health.hours_since_last_completed_run !== null ? `${health.hours_since_last_completed_run}h` : '-'}
        />
        <StatCard
          title="Alertas Activas"
          value={health.active_alerts_count}
        />
        <StatCard
          title="Unmatched Abiertos"
          value={health.unmatched_open_count}
        />
        <StatCard
          title="Personas"
          value={health.total_persons.toLocaleString()}
        />
        <StatCard
          title="Links"
          value={health.total_links.toLocaleString()}
        />
      </div>

      {/* Bloques key/value */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Alertas por severidad */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Alertas por Severidad</h2>
          {Object.keys(health.active_alerts_by_severity).length === 0 ? (
            <p className="text-gray-500 text-sm">No hay alertas activas</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(health.active_alerts_by_severity).map(([severity, count]) => (
                <div key={severity} className="flex justify-between items-center">
                  <span className="text-sm font-medium capitalize">{severity}</span>
                  <Badge variant={severity === 'error' ? 'error' : severity === 'warning' ? 'warning' : 'info'}>
                    {count}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Unmatched por razón */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Unmatched por Razón</h2>
          {Object.keys(health.unmatched_open_by_reason).length === 0 ? (
            <p className="text-gray-500 text-sm">No hay unmatched abiertos</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(health.unmatched_open_by_reason).map(([reason, count]) => (
                <div key={reason} className="flex justify-between items-center">
                  <span className="text-sm font-medium">{reason}</span>
                  <span className="text-sm text-gray-600">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Links por fuente */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Links por Fuente</h2>
          {Object.keys(health.links_by_source).length === 0 ? (
            <p className="text-gray-500 text-sm">No hay links</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(health.links_by_source).map(([source, count]) => (
                <div key={source} className="flex justify-between items-center">
                  <span className="text-sm font-medium">{source}</span>
                  <span className="text-sm text-gray-600">{count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

