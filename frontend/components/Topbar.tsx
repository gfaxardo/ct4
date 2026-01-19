'use client';

import { useState, useRef, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';

const routeTitles: Record<string, { title: string; subtitle?: string }> = {
  '/dashboard': { title: 'Dashboard', subtitle: 'Vista general del sistema' },
  '/pagos': { title: 'Pagos', subtitle: 'Elegibilidad y gestion' },
  '/pagos/cobranza-yango': { title: 'Cobranza Yango', subtitle: 'Gestion de cobranza' },
  '/pagos/yango-cabinet-claims': { title: 'Claims Cabinet', subtitle: 'Claims de Yango Cabinet' },
  '/pagos/yango-cabinet': { title: 'Reconciliacion', subtitle: 'Yango Cabinet' },
  '/pagos/resumen-conductor': { title: 'Resumen Conductor', subtitle: 'Pagos por conductor' },
  '/pagos/driver-matrix': { title: 'Driver Matrix', subtitle: 'Matriz de conductores' },
  '/scouts/attribution-health': { title: 'Atribucion', subtitle: 'Health de scouts' },
  '/scouts/liquidation': { title: 'Liquidaciones', subtitle: 'Scouts' },
  '/scouts/conflicts': { title: 'Conflictos', subtitle: 'Resolucion de conflictos' },
  '/scouts/backlog': { title: 'Backlog', subtitle: 'Pendientes de scouts' },
  '/persons': { title: 'Personas', subtitle: 'Registro de identidad' },
  '/unmatched': { title: 'Unmatched', subtitle: 'Registros sin resolver' },
  '/runs': { title: 'Auditoria', subtitle: 'Historial de ejecuciones' },
  '/ops/alerts': { title: 'Alertas', subtitle: 'Sistema de alertas' },
  '/ops/health': { title: 'Health', subtitle: 'Estado del sistema' },
  '/cabinet-leads/upload': { title: 'Procesar Leads', subtitle: 'Cabinet Leads' },
};

function getCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}

function getCurrentDate() {
  const now = new Date();
  return now.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
}

export default function Topbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const routeInfo = routeTitles[pathname] || { title: 'CT4 Identity', subtitle: 'Sistema de Identidad' };

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'SUPERADMIN': return 'bg-purple-100 text-purple-700';
      case 'ADMIN': return 'bg-blue-100 text-blue-700';
      default: return 'bg-slate-100 text-slate-700';
    }
  };

  return (
    <header className="h-16 fixed top-0 left-64 right-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 tracking-tight">{routeInfo.title}</h1>
          {routeInfo.subtitle && <p className="text-xs text-slate-500">{routeInfo.subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-full">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-emerald-700">Sistema Activo</span>
        </div>
        <div className="h-8 w-px bg-slate-200" />
        <div className="text-right">
          <p className="text-sm font-medium text-slate-700">{getCurrentTime()}</p>
          <p className="text-xs text-slate-400">{getCurrentDate()}</p>
        </div>
        <div className="h-8 w-px bg-slate-200" />
        <div className="relative" ref={menuRef}>
          <button onClick={() => setShowUserMenu(!showUserMenu)} className="flex items-center gap-3 p-1.5 rounded-lg hover:bg-slate-100 transition-colors">
            <div className="w-8 h-8 rounded-full bg-[#ef0000] flex items-center justify-center text-white font-semibold text-sm shadow-sm shadow-[#ef0000]/30">
              {user ? getInitials(user.name) : '?'}
            </div>
            <div className="text-left hidden md:block">
              <p className="text-sm font-medium text-slate-700">{user?.name || 'Usuario'}</p>
              <p className="text-xs text-slate-400">@{user?.username || ''}</p>
            </div>
            <svg className={`w-4 h-4 text-slate-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-lg border border-slate-200 py-2 animate-scaleIn">
              <div className="px-4 py-3 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-[#ef0000] flex items-center justify-center text-white font-bold text-lg shadow-sm shadow-[#ef0000]/30">
                    {user ? getInitials(user.name) : '?'}
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">{user?.name}</p>
                    <p className="text-sm text-slate-500">{user?.email}</p>
                    <span className={`inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded-full ${getRoleColor(user?.role || '')}`}>
                      {user?.role}
                    </span>
                  </div>
                </div>
              </div>
              <div className="py-1">
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  Mi Perfil
                </button>
              </div>
              <div className="border-t border-slate-100 pt-1 mt-1">
                <button onClick={logout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Cerrar Sesion
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
