/**
 * Data Health - Salud del sistema de identidad
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado de salud del sistema de identidad canónica?"
 * 
 * Nota: Esta página ahora usa el componente reutilizable IdentitySystemHealthPanel
 * que también se usa en /ops/health?tab=identity
 */

'use client';

import IdentitySystemHealthPanel from '@/components/ops/IdentitySystemHealthPanel';

export default function DataHealthPage() {
  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Salud del Sistema</h1>
      <IdentitySystemHealthPanel />
    </div>
  );
}
