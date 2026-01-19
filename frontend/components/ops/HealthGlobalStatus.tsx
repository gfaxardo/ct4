/**
 * HealthGlobalStatus - Banner con estado global del sistema
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useState, useEffect } from 'react';
import { getOpsHealthGlobal, ApiError } from '@/lib/api';
import type { HealthGlobalResponse } from '@/lib/types';

// Icons
const Icons = {
  check: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  warning: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  error: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  info: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

function getStatusStyles(status: string) {
  switch (status) {
    case 'OK':
      return {
        bg: 'bg-emerald-50 border-emerald-200',
        icon: Icons.check,
        iconColor: 'text-emerald-500',
        badgeBg: 'bg-emerald-500',
        text: 'text-emerald-800',
      };
    case 'WARN':
    case 'WARNING':
      return {
        bg: 'bg-amber-50 border-amber-200',
        icon: Icons.warning,
        iconColor: 'text-amber-500',
        badgeBg: 'bg-amber-500',
        text: 'text-amber-800',
      };
    case 'ERROR':
      return {
        bg: 'bg-red-50 border-red-200',
        icon: Icons.error,
        iconColor: 'text-red-500',
        badgeBg: 'bg-red-500',
        text: 'text-red-800',
      };
    default:
      return {
        bg: 'bg-slate-50 border-slate-200',
        icon: Icons.info,
        iconColor: 'text-slate-500',
        badgeBg: 'bg-slate-500',
        text: 'text-slate-800',
      };
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
          setError(e.detail || e.statusText || 'Error al cargar estado');
        } else {
          setError('Error desconocido');
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
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
        <div className="flex items-center justify-center gap-3 py-2">
          <div className="w-5 h-5 border-2 border-[#ef0000] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-500">Cargando estado global...</span>
        </div>
      </div>
    );
  }

  // Si hay error, mostrar banner informativo en lugar de error
  if (error || !globalStatus) {
    return (
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
            {Icons.info}
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-700">Estado Global</p>
            <p className="text-xs text-slate-500">
              Las vistas de health requieren configuración adicional
            </p>
          </div>
          <div className="flex items-center gap-4 text-center">
            <div>
              <p className="text-lg font-bold text-slate-400">—</p>
              <p className="text-xs text-slate-500">Errores</p>
            </div>
            <div>
              <p className="text-lg font-bold text-slate-400">—</p>
              <p className="text-xs text-slate-500">Warnings</p>
            </div>
            <div>
              <p className="text-lg font-bold text-slate-400">—</p>
              <p className="text-xs text-slate-500">OK</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const styles = getStatusStyles(globalStatus.global_status);

  return (
    <div className={`rounded-xl border p-4 mb-6 ${styles.bg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`flex-shrink-0 w-12 h-12 rounded-full ${styles.badgeBg} flex items-center justify-center text-white`}>
            {styles.icon}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-600">Estado Global del Sistema</p>
            <p className={`text-xl font-bold ${styles.text}`}>
              {globalStatus.global_status === 'OK' ? 'Sistema Operativo' :
               globalStatus.global_status === 'WARN' ? 'Advertencias Detectadas' :
               globalStatus.global_status === 'ERROR' ? 'Errores Críticos' :
               globalStatus.global_status}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{globalStatus.error_count}</p>
            <p className="text-xs text-slate-600">Errores</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-amber-600">{globalStatus.warn_count}</p>
            <p className="text-xs text-slate-600">Warnings</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-emerald-600">{globalStatus.ok_count}</p>
            <p className="text-xs text-slate-600">OK</p>
          </div>
        </div>
      </div>
    </div>
  );
}
