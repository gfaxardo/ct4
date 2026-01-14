/**
 * Topbar - Barra superior con diseño glassmorphism moderno
 */

'use client';

import { usePathname } from 'next/navigation';

// Mapa de rutas a títulos
const routeTitles: Record<string, { title: string; subtitle?: string }> = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Vista general del sistema' },
  '/pagos': { title: 'Pagos', subtitle: 'Elegibilidad y gestión' },
  '/pagos/cobranza-yango': { title: 'Cobranza Yango', subtitle: 'Gestión de cobranza' },
  '/pagos/yango-cabinet-claims': { title: 'Claims Cabinet', subtitle: 'Claims de Yango Cabinet' },
  '/pagos/yango-cabinet': { title: 'Reconciliación', subtitle: 'Yango Cabinet' },
  '/pagos/resumen-conductor': { title: 'Resumen Conductor', subtitle: 'Pagos por conductor' },
  '/pagos/driver-matrix': { title: 'Driver Matrix', subtitle: 'Matriz de conductores' },
  '/scouts/attribution-health': { title: 'Atribución', subtitle: 'Health de scouts' },
  '/scouts/liquidation': { title: 'Liquidaciones', subtitle: 'Scouts' },
  '/scouts/conflicts': { title: 'Conflictos', subtitle: 'Resolución de conflictos' },
  '/scouts/backlog': { title: 'Backlog', subtitle: 'Pendientes de scouts' },
  '/persons': { title: 'Personas', subtitle: 'Registro de identidad' },
  '/unmatched': { title: 'Unmatched', subtitle: 'Registros sin resolver' },
  '/runs': { title: 'Auditoría', subtitle: 'Historial de ejecuciones' },
  '/ops/alerts': { title: 'Alertas', subtitle: 'Sistema de alertas' },
  '/ops/health': { title: 'Health', subtitle: 'Estado del sistema' },
  '/cabinet-leads/upload': { title: 'Cargar Leads', subtitle: 'Importar Cabinet Leads' },
  '/orphans': { title: 'Huérfanos', subtitle: 'Drivers sin leads asociados' },
};

function getCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function getCurrentDate() {
  const now = new Date();
  return now.toLocaleDateString('es-ES', { 
    weekday: 'short', 
    day: 'numeric', 
    month: 'short' 
  });
}

export default function Topbar() {
  const pathname = usePathname();
  const routeInfo = routeTitles[pathname] || { title: 'CT4 Identity', subtitle: 'Sistema de Identidad' };

  return (
    <header className="
      h-16 fixed top-0 left-64 right-0 z-30
      bg-white/80 backdrop-blur-xl
      border-b border-slate-200/60
      flex items-center justify-between px-6
    ">
      {/* Left: Page Title */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
            {routeInfo.title}
          </h1>
          {routeInfo.subtitle && (
            <p className="text-xs text-slate-500">{routeInfo.subtitle}</p>
          )}
        </div>
      </div>

      {/* Right: Actions & Status */}
      <div className="flex items-center gap-4">
        {/* Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-emerald-700">Sistema Activo</span>
        </div>

        {/* Separator */}
        <div className="h-8 w-px bg-slate-200" />

        {/* Date & Time */}
        <div className="text-right">
          <p className="text-sm font-medium text-slate-700">{getCurrentTime()}</p>
          <p className="text-xs text-slate-400">{getCurrentDate()}</p>
        </div>

        {/* Quick Actions */}
        <button className="
          p-2 rounded-lg text-slate-400 
          hover:bg-slate-100 hover:text-slate-600
          transition-colors duration-200
        " title="Notificaciones">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        </button>

        <button className="
          p-2 rounded-lg text-slate-400 
          hover:bg-slate-100 hover:text-slate-600
          transition-colors duration-200
        " title="Configuración">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </header>
  );
}
