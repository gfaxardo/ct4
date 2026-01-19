/**
 * Procesar Nuevos Leads - Cabinet
 * Detecta y procesa automáticamente nuevos registros
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { getPendingLeadsCount, processNewLeads, getIdentityRuns, getAutoProcessorStatus, ApiError } from '@/lib/api';
import type { PendingLeadsCount, ProcessNewLeadsResponse, AutoProcessorStatus } from '@/lib/api';
import StatCard from '@/components/StatCard';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Formatear fecha de manera legible (sin conversión de timezone)
const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '—';
  // Parsear la fecha directamente sin timezone para evitar conversión
  const parts = dateStr.split('T')[0].split('-');
  if (parts.length !== 3) return dateStr;
  
  const year = parseInt(parts[0]);
  const month = parseInt(parts[1]) - 1; // JavaScript months are 0-indexed
  const day = parseInt(parts[2]);
  
  const months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  return `${day} ${months[month]} ${year}`;
};

// Icons
const Icons = {
  play: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  database: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
  calendar: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  clock: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  alert: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  spinner: (
    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
  ),
};

// Pasos del procesamiento
const PROCESS_STEPS = [
  { id: 1, name: 'Refrescando índice de drivers', duration: '~10s' },
  { id: 2, name: 'Procesando leads (matching)', duration: '~2-3min' },
  { id: 3, name: 'Poblando eventos', duration: '~1-2min' },
  { id: 4, name: 'Actualizando vistas materializadas', duration: '~30s' },
];

export default function ProcessLeadsPage() {
  const [pendingInfo, setPendingInfo] = useState<PendingLeadsCount | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [result, setResult] = useState<ProcessNewLeadsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshIndex, setRefreshIndex] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [autoProcessorStatus, setAutoProcessorStatus] = useState<AutoProcessorStatus | null>(null);
  const router = useRouter();

  const loadPendingCount = useCallback(async () => {
    try {
      setLoading(true);
      const [data, status] = await Promise.all([
        getPendingLeadsCount(),
        getAutoProcessorStatus().catch(() => null)
      ]);
      setPendingInfo(data);
      setAutoProcessorStatus(status);
      setError(null);
    } catch (err: unknown) {
      console.error('Error cargando pendientes:', err);
      if (err instanceof ApiError) {
        setError(err.detail || err.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Verificar estado de la última corrida
  const checkRunStatus = useCallback(async () => {
    try {
      const runs = await getIdentityRuns({ limit: 1, job_type: 'identity_run' });
      if (runs.items && runs.items.length > 0) {
        const lastRun = runs.items[0];
        if (lastRun.status === 'running') {
          setProcessing(true);
          // Estimar el paso basado en el tiempo transcurrido
          const startTime = new Date(lastRun.started_at).getTime();
          const elapsed = Math.floor((Date.now() - startTime) / 1000);
          setElapsedTime(elapsed);
          
          // Estimar paso basado en tiempo
          if (elapsed < 15) setCurrentStep(1);
          else if (elapsed < 180) setCurrentStep(2);
          else if (elapsed < 300) setCurrentStep(3);
          else setCurrentStep(4);
        } else if (lastRun.status === 'completed' && processing) {
          // Procesamiento terminó
          setProcessing(false);
          setCurrentStep(0);
          loadPendingCount();
        }
      }
    } catch (err) {
      console.error('Error verificando estado:', err);
    }
  }, [processing, loadPendingCount]);

  useEffect(() => {
    loadPendingCount();
    checkRunStatus();
  }, [loadPendingCount, checkRunStatus]);

  // Auto-refresh cada 30 segundos si no está procesando
  useEffect(() => {
    if (!autoRefresh || processing) return;
    
    const interval = setInterval(() => {
      loadPendingCount();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, processing, loadPendingCount]);

  // Durante procesamiento, actualizar cada 5 segundos
  useEffect(() => {
    if (!processing) return;
    
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 5);
      checkRunStatus();
      loadPendingCount();
    }, 5000);
    
    return () => clearInterval(interval);
  }, [processing, checkRunStatus, loadPendingCount]);

  const handleProcess = async () => {
    try {
      setProcessing(true);
      setCurrentStep(1);
      setElapsedTime(0);
      setError(null);
      setResult(null);
      
      const response = await processNewLeads(refreshIndex);
      setResult(response);
      
      if (response.status === 'no_pending') {
        setProcessing(false);
        setCurrentStep(0);
      }
      // Si está procesando, el polling se encargará de actualizar
    } catch (err: unknown) {
      setProcessing(false);
      setCurrentStep(0);
      if (err instanceof ApiError) {
        setError(err.detail || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  if (loading && !pendingInfo) {
    return <PageLoadingOverlay title="Procesar Leads" subtitle="Verificando nuevos registros..." />;
  }

  const pendingCount = pendingInfo?.pending_count || 0;
  const hasPending = pendingInfo?.has_pending || false;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Procesar Nuevos Leads</h1>
          <p className="text-slate-600">Detectar y procesar automáticamente registros nuevos</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 text-[#ef0000] rounded"
            />
            Auto-refresh
          </label>
          <button
            onClick={loadPendingCount}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium disabled:opacity-50"
          >
            {loading ? Icons.spinner : Icons.refresh}
            Actualizar
          </button>
        </div>
      </div>

      {/* Status KPIs */}
      {pendingInfo && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            title="En Tabla"
            value={pendingInfo.total_in_table.toLocaleString()}
            subtitle="con external_id"
            icon={Icons.database}
            variant="default"
          />
          <StatCard
            title="Vinculados"
            value={(pendingInfo.total_in_links || 0).toLocaleString()}
            subtitle="identity_links"
            icon={Icons.check}
            variant="success"
          />
          <StatCard
            title="Sin Match"
            value={(pendingInfo.total_in_unmatched || 0).toLocaleString()}
            subtitle="identity_unmatched"
            icon={Icons.alert}
            variant="warning"
          />
          <StatCard
            title="Pendientes"
            value={pendingCount.toLocaleString()}
            subtitle={hasPending ? "por procesar" : "todo al día"}
            icon={hasPending ? Icons.clock : Icons.check}
            variant={hasPending ? "error" : "success"}
          />
          <StatCard
            title="Último Lead"
            value={formatDate(pendingInfo.max_lead_date)}
            subtitle="fecha más reciente"
            icon={Icons.calendar}
            variant="default"
          />
        </div>
      )}

      {/* Processing Progress */}
      {processing && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            {Icons.spinner}
            <div>
              <p className="font-semibold text-red-900">Procesando leads...</p>
              <p className="text-sm text-[#cc0000]">
                Tiempo transcurrido: {Math.floor(elapsedTime / 60)}:{(elapsedTime % 60).toString().padStart(2, '0')}
              </p>
            </div>
          </div>
          
          {/* Steps Progress */}
          <div className="space-y-3">
            {PROCESS_STEPS.map((step) => (
              <div key={step.id} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  currentStep > step.id 
                    ? 'bg-emerald-500 text-white' 
                    : currentStep === step.id 
                    ? 'bg-[#ef0000] text-white animate-pulse' 
                    : 'bg-slate-200 text-slate-500'
                }`}>
                  {currentStep > step.id ? '✓' : step.id}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${
                    currentStep >= step.id ? 'text-red-900' : 'text-slate-400'
                  }`}>
                    {step.name}
                  </p>
                </div>
                <span className="text-xs text-slate-500">{step.duration}</span>
              </div>
            ))}
          </div>
          
          <div className="mt-4 pt-4 border-t border-red-200">
            <p className="text-xs text-[#cc0000]">
              💡 Puedes ir a <button onClick={() => router.push('/runs')} className="underline font-medium">Corridas</button> para ver el detalle del procesamiento
            </p>
          </div>
        </div>
      )}

      {/* Main Action Card */}
      {!processing && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
          {hasPending ? (
            <>
              {/* Pending Alert */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <div className="text-amber-500">{Icons.alert}</div>
                  <div>
                    <p className="font-semibold text-amber-800">
                      {pendingCount.toLocaleString()} registros nuevos detectados
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      Hay leads en la tabla que aún no han sido procesados por el sistema de identidad.
                      {pendingInfo?.last_processed_date && (
                        <> Último procesamiento: <strong>{formatDate(pendingInfo.last_processed_date)}</strong></>
                      )}
                    </p>
                  </div>
                </div>
              </div>

              {/* Options */}
              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
                  <input
                    type="checkbox"
                    checked={refreshIndex}
                    onChange={(e) => setRefreshIndex(e.target.checked)}
                    className="w-4 h-4 text-[#ef0000] rounded focus:ring-[#ef0000]"
                    disabled={processing}
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-900">Actualizar índice de drivers</p>
                    <p className="text-xs text-slate-500">Refrescar drivers_index antes de procesar (recomendado)</p>
                  </div>
                </label>
              </div>

              {/* Process Button */}
              <button
                onClick={handleProcess}
                disabled={processing}
                className="w-full flex items-center justify-center gap-2 px-4 py-4 bg-[#ef0000] text-white rounded-xl hover:bg-[#cc0000] transition-colors font-semibold text-lg disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                {Icons.play}
                Procesar {pendingCount.toLocaleString()} Leads Nuevos
              </button>
            </>
          ) : (
            /* All caught up */
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-slate-900 mb-2">Todo está al día</h2>
              <p className="text-slate-600">
                No hay leads nuevos pendientes de procesar.
                {pendingInfo?.last_processed_date && (
                  <> Último procesamiento: <strong>{formatDate(pendingInfo.last_processed_date)}</strong></>
                )}
              </p>
            </div>
          )}

          {/* Result */}
          {result && result.status === 'no_pending' && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="text-blue-500">{Icons.check}</div>
                <div>
                  <p className="font-medium text-blue-800">Sin pendientes</p>
                  <p className="text-sm text-blue-600 mt-1">{result.message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="text-red-500">{Icons.alert}</div>
                <div>
                  <p className="font-medium text-red-800">Error</p>
                  <p className="text-sm text-red-600 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Auto-Processor Status */}
      {autoProcessorStatus && (
        <div className={`rounded-xl border p-6 ${
          autoProcessorStatus.enabled && autoProcessorStatus.running 
            ? 'bg-emerald-50 border-emerald-200' 
            : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-slate-900 flex items-center gap-2">
              <svg className="w-5 h-5 text-[#ef0000]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Auto-Procesamiento
            </h2>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
              autoProcessorStatus.enabled && autoProcessorStatus.running
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-slate-200 text-slate-600'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                autoProcessorStatus.enabled && autoProcessorStatus.running ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
              }`}></span>
              {autoProcessorStatus.enabled && autoProcessorStatus.running ? 'Activo' : 'Inactivo'}
            </span>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Intervalo</span>
              <p className="font-medium text-slate-900">{autoProcessorStatus.interval_minutes} minutos</p>
            </div>
            <div>
              <span className="text-slate-500">Próxima ejecución</span>
              <p className="font-medium text-slate-900">
                {autoProcessorStatus.next_run 
                  ? new Date(autoProcessorStatus.next_run).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })
                  : '—'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Estado actual</span>
              <p className="font-medium text-slate-900">
                {autoProcessorStatus.is_processing ? 'Procesando...' : 'En espera'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Última ejecución</span>
              <p className="font-medium text-slate-900">
                {autoProcessorStatus.last_run 
                  ? formatDate(autoProcessorStatus.last_run.timestamp)
                  : 'Nunca'}
              </p>
            </div>
          </div>
          
          {autoProcessorStatus.last_run && (
            <div className={`mt-4 pt-4 border-t ${
              autoProcessorStatus.enabled ? 'border-emerald-200' : 'border-slate-200'
            }`}>
              <p className="text-xs text-slate-600">
                <span className="font-medium">Última corrida:</span>{' '}
                {autoProcessorStatus.last_run.status === 'completed' && '✅ Completada'}
                {autoProcessorStatus.last_run.status === 'no_pending' && '✓ Sin pendientes'}
                {autoProcessorStatus.last_run.status === 'error' && `❌ Error: ${autoProcessorStatus.last_run.error}`}
                {autoProcessorStatus.last_run.duration_seconds && 
                  ` (${Math.round(autoProcessorStatus.last_run.duration_seconds)}s)`
                }
              </p>
            </div>
          )}
          
          <div className="mt-4 pt-4 border-t border-slate-200/50">
            <p className="text-xs text-slate-500">
              💡 El sistema revisa automáticamente cada {autoProcessorStatus.interval_minutes} minutos si hay leads nuevos y los procesa sin intervención manual.
            </p>
          </div>
        </div>
      )}

      {/* Info Panel */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-900 mb-4">¿Cómo funciona?</h2>
        <div className="space-y-3 text-sm text-slate-600">
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">1</span>
            <p>El sistema compara los registros en <code className="bg-white px-1.5 py-0.5 rounded border text-xs">module_ct_cabinet_leads</code> con los ya procesados</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">2</span>
            <p>Los leads nuevos se procesan a través del motor de identidad (~2-3 min para 800+ registros)</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">3</span>
            <p>Se actualizan las vistas materializadas automáticamente</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">4</span>
            <p>El progreso se puede monitorear en <button onClick={() => router.push('/runs')} className="text-[#ef0000] hover:text-[#cc0000] font-medium underline">Identidad → Auditoría / Runs</button></p>
          </div>
          <div className="flex items-start gap-2 mt-4 pt-4 border-t border-slate-200">
            <span className="flex-shrink-0 w-5 h-5 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs">⚡</span>
            <p><strong>Automático:</strong> El backend revisa cada 5 minutos si hay leads nuevos y los procesa automáticamente. Solo usa el botón manual si necesitas procesar inmediatamente.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
