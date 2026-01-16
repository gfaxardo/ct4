/**
 * Sidebar - Navegación moderna con diseño glassmorphism
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  pending?: boolean;
  children?: NavItem[];
}

// Iconos SVG modernos
const Icons = {
  dashboard: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm10 0a1 1 0 011-1h4a1 1 0 011 1v2a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zm0 6a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1v-7zM4 13a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z" />
    </svg>
  ),
  money: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  target: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  ),
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  settings: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  chevron: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
  dot: (
    <span className="w-1.5 h-1.5 rounded-full bg-current opacity-50" />
  ),
};

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: Icons.dashboard,
  },
  {
    label: 'Pagos',
    href: '#',
    icon: Icons.money,
    children: [
      { label: 'Cobranza Yango', href: '/pagos/cobranza-yango', icon: Icons.dot },
      { label: 'Claims Cabinet', href: '/pagos/yango-cabinet-claims', icon: Icons.dot },
      { label: 'Reconciliación', href: '/pagos/yango-cabinet', icon: Icons.dot },
      { label: 'Elegibilidad', href: '/pagos', icon: Icons.dot },
      { label: 'Resumen Conductor', href: '/pagos/resumen-conductor', icon: Icons.dot },
      { label: 'Driver Matrix', href: '/pagos/driver-matrix', icon: Icons.dot },
      { label: 'Claims', href: '/pagos/claims', icon: Icons.dot, pending: true },
    ],
  },
  {
    label: 'Scouts',
    href: '#',
    icon: Icons.target,
    children: [
      { label: 'Atribución', href: '/scouts/attribution-health', icon: Icons.dot },
      { label: 'Liquidaciones', href: '/scouts/liquidation', icon: Icons.dot },
      { label: 'Conflictos', href: '/scouts/conflicts', icon: Icons.dot },
      { label: 'Backlog', href: '/scouts/backlog', icon: Icons.dot },
    ],
  },
  {
    label: 'Identidad',
    href: '#',
    icon: Icons.users,
    children: [
      { label: 'Personas', href: '/persons', icon: Icons.dot },
      { label: 'Unmatched', href: '/unmatched', icon: Icons.dot },
      { label: 'Auditoría / Runs', href: '/runs', icon: Icons.dot },
    ],
  },
  {
    label: 'Ops / Health',
    href: '#',
    icon: Icons.settings,
    children: [
      { label: 'Alerts', href: '/ops/alerts', icon: Icons.dot },
      { label: 'Health', href: '/ops/health', icon: Icons.dot },
      { label: 'Cargar Leads', href: '/cabinet-leads/upload', icon: Icons.dot },
    ],
  },
];

function NavLink({ item, pathname, isChild = false }: { item: NavItem; pathname: string; isChild?: boolean }) {
  const isActive = pathname === item.href;
  const hasActiveChild = item.children?.some(child => pathname === child.href);
  const isPending = item.pending === true;

  if (isPending) {
    return (
      <div className={`
        flex items-center gap-3 px-3 py-2 rounded-lg text-sm
        text-slate-500 cursor-not-allowed opacity-60
        ${isChild ? 'ml-6' : ''}
      `}>
        {item.icon}
        <span>{item.label}</span>
        <span className="ml-auto text-[10px] font-medium uppercase tracking-wider bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
          Pronto
        </span>
      </div>
    );
  }

  if (item.children) {
    return (
      <div className={`
        flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
        ${hasActiveChild ? 'text-cyan-400' : 'text-slate-300'}
        transition-colors duration-200
      `}>
        <span className={hasActiveChild ? 'text-cyan-400' : 'text-slate-400'}>
          {item.icon}
        </span>
        <span>{item.label}</span>
      </div>
    );
  }

  return (
    <Link
      href={item.href}
      className={`
        flex items-center gap-3 px-3 py-2 rounded-lg text-sm
        transition-all duration-200 group
        ${isChild ? 'ml-6' : ''}
        ${isActive
          ? 'bg-gradient-to-r from-cyan-500/20 to-transparent text-cyan-400 font-medium'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
        }
      `}
    >
      <span className={`
        transition-colors duration-200
        ${isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-400'}
      `}>
        {item.icon}
      </span>
      <span>{item.label}</span>
      {isActive && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
      )}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="
      w-64 h-screen fixed left-0 top-0 z-40
      bg-gradient-to-b from-slate-900 via-slate-900 to-slate-800
      border-r border-slate-800
      flex flex-col
      custom-scrollbar overflow-y-auto
    ">
      {/* Logo & Brand */}
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="
            w-10 h-10 rounded-xl
            bg-gradient-to-br from-cyan-400 to-emerald-400
            flex items-center justify-center
            shadow-lg shadow-cyan-500/20
          ">
            <span className="text-lg font-bold text-slate-900">CT</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">CT4 Identity</h1>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => (
          <div key={item.label} className="animate-fade-in">
            <NavLink item={item} pathname={pathname} />
            {item.children && (
              <div className="mt-1 space-y-0.5">
                {item.children.map((child) => (
                  <NavLink 
                    key={child.href} 
                    item={child} 
                    pathname={pathname} 
                    isChild 
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-400 to-purple-500 flex items-center justify-center">
            <span className="text-xs font-bold text-white">OP</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-300 truncate">Operador</p>
            <p className="text-xs text-slate-500">Admin</p>
          </div>
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="Conectado" />
        </div>
      </div>
    </aside>
  );
}
