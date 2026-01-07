/**
 * HealthGlobalStatus - Badge grande con estado global y contadores
 */

'use client';

import { useState, useEffect } from 'react';
import { getOpsHealthGlobal, ApiError } from '@/lib/api';
import type { HealthGlobalResponse } from '@/lib/types';
import Badge from '@/components/Badge';

function getGlobalStatusBadge(status: string) {
  switch (status) {
    case 'OK':
      return (
        <Badge variant="success" className="text-lg px-4 py-2">
          {status}
        </Badge>
      );
    case 'WARN':
      return (
        <Badge variant="warning" className="text-lg px-4 py-2">
          {status}
        </Badge>
      );
    case 'ERROR':
      return (
        <Badge variant="error" className="text-lg px-4 py-2">
          {status}
        </Badge>
      );
    default:
      return (
        <Badge className="text-lg px-4 py-2">
          {status}
        </Badge>
      );
  }
}

export default function HealthGlobalStatus() {
  const [globalStatus, setGlobalStatus] = useState<HealthGlobalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadGlobalStatus() {
      setLoading(true);
      setError(null);
      try {
        const response: HealthGlobalResponse = await getOpsHealthGlobal();
        setGlobalStatus(response);
      } catch (e) {
        if (e instanceof ApiError) {
          setError(`Error: ${e.detail || e.statusText}`);
        } else {
          setError('Error desconocido al cargar estado global');
        }
        console.error('Error loading global health status:', e);
      } finally {
        setLoading(false);
      }
    }

    loadGlobalStatus();
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="text-center py-4">
          <div className="text-gray-500 text-sm">Cargando estado global...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-red-800 text-sm">{error}</div>
        </div>
      </div>
    );
  }

  if (!globalStatus) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div>
            <div className="text-sm text-gray-600 mb-2">Estado Global</div>
            {getGlobalStatusBadge(globalStatus.global_status)}
          </div>
        </div>
        <div className="flex items-center space-x-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{globalStatus.error_count}</div>
            <div className="text-xs text-gray-600">Errores</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">{globalStatus.warn_count}</div>
            <div className="text-xs text-gray-600">Advertencias</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{globalStatus.ok_count}</div>
            <div className="text-xs text-gray-600">OK</div>
          </div>
        </div>
      </div>
    </div>
  );
}









