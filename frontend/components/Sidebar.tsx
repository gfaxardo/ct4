/**
 * Sidebar - Navegación según FRONTEND_UI_BLUEPRINT_v1.md
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  label: string;
  href: string;
  icon: string;
  pending?: boolean;
  children?: NavItem[];
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: '📊',
  },
  {
    label: 'Identidad',
    href: '#',
    icon: '👥',
    children: [
      { label: 'Personas', href: '/persons', icon: '' },
      { label: 'Unmatched', href: '/unmatched', icon: '' },
      { label: 'Runs', href: '/runs', icon: '' },
    ],
  },
  {
    label: 'Pagos',
    href: '#',
    icon: '💰',
    children: [
      { label: 'Elegibilidad', href: '/pagos', icon: '' },
      {
        label: 'Yango',
        href: '#',
        icon: '',
        children: [
          { label: 'Reconciliación', href: '/pagos/yango-cabinet', icon: '' },
          { label: 'Cobranza Yango', href: '/pagos/cobranza-yango', icon: '' },
          { label: 'Claims Cabinet', href: '/pagos/yango-cabinet-claims', icon: '' },
        ],
      },
      { label: 'Resumen por Conductor', href: '/pagos/resumen-conductor', icon: '' },
      { label: 'Driver Matrix', href: '/pagos/driver-matrix', icon: '' },
      { label: 'Claims', href: '/pagos/claims', icon: '', pending: true },
    ],
  },
  {
    label: 'Scouts',
    href: '#',
    icon: '🎯',
    children: [
      { label: 'Salud de Atribución', href: '/scouts/attribution-health', icon: '' },
      { label: 'Conflictos', href: '/scouts/conflicts', icon: '' },
      { label: 'Backlog', href: '/scouts/backlog', icon: '' },
      { label: 'Cobranza Yango', href: '/scouts/cobranza-yango', icon: '' },
      { label: 'Liquidación Base', href: '/scouts/liquidation', icon: '' },
    ],
  },
  {
    label: 'Liquidaciones',
    href: '#',
    icon: '💵',
    children: [
      { label: 'Scouts', href: '/liquidaciones', icon: '' },
    ],
  },
  {
    label: 'Ops',
    href: '#',
    icon: '⚙️',
    children: [
      { label: 'Alerts', href: '/ops/alerts', icon: '' },
      { label: 'Health', href: '/ops/health', icon: '' },
      { label: 'Cargar Leads Cabinet', href: '/cabinet-leads/upload', icon: '' },
    ],
  },
];

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const isActive = pathname === item.href;
  const isPending = item.pending === true; // Evaluación explícita: solo true muestra (PENDING)

  if (isPending) {
    return (
      <div className="px-4 py-2 text-sm text-gray-400 cursor-not-allowed">
        {item.label} <span className="text-xs">(PENDING)</span>
      </div>
    );
  }

  if (item.children) {
    return (
      <div className="px-4 py-2 text-sm font-medium text-gray-700">
        {item.icon} {item.label}
      </div>
    );
  }

  return (
    <Link
      href={item.href}
      className={`px-4 py-2 text-sm block ${
        isActive
          ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
          : 'text-gray-700 hover:bg-gray-50'
      }`}
    >
      {item.icon && <span className="mr-2">{item.icon}</span>}
      {item.label}
    </Link>
  );
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 bg-white border-r border-gray-200 h-screen fixed left-0 top-0 overflow-y-auto">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">CT4 Identity</h1>
        <p className="text-xs text-gray-500">Sistema de Identidad Canónica</p>
      </div>
      <nav className="py-4">
        {navItems.map((item) => (
          <div key={item.label}>
            <NavLink item={item} pathname={pathname} />
            {item.children && (
              <div className="ml-4 mt-1">
                {item.children.map((child) => (
                  <div key={child.href}>
                    <NavLink item={child} pathname={pathname} />
                    {child.children && (
                      <div className="ml-4 mt-1">
                        {child.children.map((grandchild) => (
                          <NavLink key={grandchild.href} item={grandchild} pathname={pathname} />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </nav>
    </div>
  );
}



