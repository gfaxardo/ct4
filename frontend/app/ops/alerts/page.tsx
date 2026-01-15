/**
 * Ops Alerts - Centro de alertas operacionales
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { getOpsAlerts, acknowledgeAlert, ApiError } from '@/lib/api';
import type { OpsAlertRow, AlertSeverity } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Pagination from '@/components/Pagination';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  bell: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  info: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  checkSmall: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
};

export default function OpsAlertsPage() {
  const [alerts, setAlerts] = useState<OpsAlertRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);
  const [filters, setFilters] = useState({
    severity: '',
    acknowledged: '',
    week_label: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [total, setTotal] = useState(0);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

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
      } = { limit, offset };

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
        setError(`Error ${err.status}: ${err.detail || err.message}`);
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
      await loadAlerts();
      setNotification({ type: 'success', message: 'Alerta reconocida exitosamente' });
      setTimeout(() => setNotification(null), 3000);
    } catch (err) {
      if (err instanceof ApiError) {
        setNotification({ type: 'error', message: `Error: ${err.detail || err.message}` });
      } else {
        setNotification({ type: 'error', message: 'Error desconocido' });
      }
    } finally {
      setAcknowledgingId(null);
    }
  };

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setOffset(0);
  };

  const handleClearFilters = () => {
    setFilters({ severity: '', acknowledged: '', week_label: '' });
    setOffset(0);
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSeverityBadgeVariant = (severity: AlertSeverity): 'success' | 'warning' | 'error' | 'info' => {
    switch (severity) {
      case 'error': return 'error';
      case 'warning': return 'warning';
      case 'info': return 'info';
      default: return 'info';
    }
  };

  const getSeverityIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'error': return Icons.error;
      case 'warning': return Icons.warning;
      case 'info': return Icons.info;
      default: return Icons.info;
    }
  };

  if (loading && alerts.length === 0) {
    return <PageLoadingOverlay title="Alertas" subtitle="Cargando alertas operacionales..." />;
  }

  // Calcular KPIs
  const errorCount = alerts.filter(a => a.severity === 'error').length;
  const warningCount = alerts.filter(a => a.severity === 'warning').length;
  const pendingCount = alerts.filter(a => !a.acknowledged).length;

  return (
    <div className="space-y-6">
      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${
          notification.type === 'success' ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
        }`}>
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? Icons.check : Icons.error}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Centro de Alertas</h1>
          <p className="text-slate-600">Monitoreo de alertas operacionales del sistema</p>
        </div>
        <button
          onClick={loadAlerts}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : Icons.refresh}
          Actualizar
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="text-red-500">{Icons.error}</div>
            <div>
              <p className="font-medium text-red-800">Error</p>
              <p className="text-sm text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Alertas"
          value={total.toLocaleString()}
          subtitle="en el sistema"
          icon={Icons.bell}
          variant="default"
        />
        <StatCard
          title="Errores"
          value={errorCount.toLocaleString()}
          subtitle="críticos"
          icon={Icons.error}
          variant="error"
        />
        <StatCard
          title="Advertencias"
          value={warningCount.toLocaleString()}
          subtitle="requieren atención"
          icon={Icons.warning}
          variant="warning"
        />
        <StatCard
          title="Pendientes"
          value={pendingCount.toLocaleString()}
          subtitle="sin reconocer"
          icon={Icons.bell}
          variant="info"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Severidad</label>
            <select
              value={filters.severity}
              onChange={(e) => handleFilterChange('severity', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Estado</label>
            <select
              value={filters.acknowledged}
              onChange={(e) => handleFilterChange('acknowledged', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="false">Pendientes</option>
              <option value="true">Reconocidas</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Semana</label>
            <input
              type="text"
              value={filters.week_label}
              onChange={(e) => handleFilterChange('week_label', e.target.value)}
              placeholder="2025-W51"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent font-mono"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleClearFilters}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              Limpiar filtros
            </button>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {alerts.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-3 text-emerald-500">
              {Icons.check}
            </div>
            <p className="text-slate-600 font-medium">Sin alertas activas</p>
            <p className="text-sm text-slate-500 mt-1">El sistema está operando normalmente</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 hover:bg-slate-50/50 transition-colors ${
                  !alert.acknowledged ? 'bg-slate-50/30' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Severity Icon */}
                  <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                    alert.severity === 'error' ? 'bg-red-100 text-red-600' :
                    alert.severity === 'warning' ? 'bg-amber-100 text-amber-600' :
                    'bg-blue-100 text-blue-600'
                  }`}>
                    {getSeverityIcon(alert.severity)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={getSeverityBadgeVariant(alert.severity)}>
                        {alert.severity.toUpperCase()}
                      </Badge>
                      <span className="text-xs text-slate-500">{alert.alert_type}</span>
                      {alert.week_label && (
                        <span className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {alert.week_label}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-900 font-medium mb-1">{alert.message}</p>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>ID: {alert.id}</span>
                      <span>{formatDate(alert.created_at)}</span>
                      {alert.acknowledged && (
                        <span className="flex items-center gap-1 text-emerald-600">
                          {Icons.checkSmall} Reconocida
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action */}
                  <div className="flex-shrink-0">
                    {!alert.acknowledged ? (
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        disabled={acknowledgingId === alert.id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors disabled:opacity-50"
                      >
                        {acknowledgingId === alert.id ? (
                          <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        ) : Icons.checkSmall}
                        {acknowledgingId === alert.id ? 'Procesando...' : 'Reconocer'}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-400 italic">Resuelta</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {alerts.length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 bg-slate-50">
            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
