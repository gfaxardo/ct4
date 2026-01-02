/**
 * Health - Panel de salud del sistema con múltiples tabs
 * 
 * Tabs:
 * - Identity: Salud del sistema de identidad canónica (implementado)
 * - Raw: Salud de datos RAW (PENDING)
 * - MV Health: Salud de materialized views (PENDING)
 * - Checks: Checks de integridad (PENDING)
 */

'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import IdentitySystemHealthPanel from '@/components/ops/IdentitySystemHealthPanel';
import RawDataHealthPanel from '@/components/ops/RawDataHealthPanel';
import MvHealthPanel from '@/components/ops/MvHealthPanel';
import HealthChecksPanel from '@/components/ops/HealthChecksPanel';
import HealthGlobalStatus from '@/components/ops/HealthGlobalStatus';

type TabId = 'identity' | 'raw' | 'mv' | 'checks';

interface Tab {
  id: TabId;
  label: string;
  pending?: boolean;
}

const tabs: Tab[] = [
  { id: 'identity', label: 'Identity' },
  { id: 'raw', label: 'Raw' },
  { id: 'mv', label: 'MV Health' },
  { id: 'checks', label: 'Checks' },
];

function PendingTabPlaceholder({ tabLabel }: { tabLabel: string }) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
      <div className="flex items-center mb-4">
        <span className="text-yellow-800 font-semibold text-lg mr-2">PENDING</span>
        <span className="text-yellow-700 text-sm">Falta implementar</span>
      </div>
      <div className="space-y-2 text-sm text-yellow-800">
        <p>
          <strong>Tab:</strong> {tabLabel}
        </p>
        <p>
          <strong>Estado:</strong> Requiere endpoint/vista para mostrar datos de salud
        </p>
        <p className="mt-4">
          <strong>Documentación:</strong> Ver{' '}
          <code className="text-xs bg-yellow-100 px-1 py-0.5 rounded">docs/frontend/FRONTEND_UI_BLUEPRINT_v1.md</code>
        </p>
      </div>
    </div>
  );
}

function HealthPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  
  // Obtener tab activo desde query params, default 'identity'
  const activeTabId = (searchParams.get('tab') || 'identity') as TabId;
  const activeTab = tabs.find(t => t.id === activeTabId) || tabs[0];

  const handleTabChange = (tabId: TabId) => {
    router.push(`/ops/health?tab=${tabId}`);
  };

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Health</h1>

      {/* Global Status */}
      <HealthGlobalStatus />

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const isActive = tab.id === activeTabId;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
                {tab.pending && (
                  <span className="ml-2 text-xs text-gray-400">(PENDING)</span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTabId === 'identity' && <IdentitySystemHealthPanel />}
        {activeTabId === 'raw' && <RawDataHealthPanel />}
        {activeTabId === 'mv' && <MvHealthPanel />}
        {activeTabId === 'checks' && <HealthChecksPanel />}
      </div>
    </div>
  );
}

export default function HealthPage() {
  return (
    <Suspense fallback={
      <div className="px-4 py-6">
        <h1 className="text-3xl font-bold mb-6">Health</h1>
        <div className="text-center py-12">Cargando...</div>
      </div>
    }>
      <HealthPageContent />
    </Suspense>
  );
}

