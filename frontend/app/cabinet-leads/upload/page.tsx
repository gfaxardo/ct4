/**
 * Upload CSV de Cabinet Leads
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { uploadCabinetLeadsCSV, getCabinetLeadsDiagnostics, ApiError } from '@/lib/api';
import type { CabinetLeadsUploadResponse, CabinetLeadsDiagnostics } from '@/lib/api';
import StatCard from '@/components/StatCard';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  upload: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
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
  alert: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  file: (
    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

export default function CabinetLeadsUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CabinetLeadsUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoProcess, setAutoProcess] = useState(true);
  const [skipAlreadyProcessed, setSkipAlreadyProcessed] = useState(true);
  const [diagnostics, setDiagnostics] = useState<CabinetLeadsDiagnostics | null>(null);
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(true);
  const [dragActive, setDragActive] = useState(false);
  const router = useRouter();

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const loadDiagnostics = async () => {
    try {
      setLoadingDiagnostics(true);
      const diag = await getCabinetLeadsDiagnostics();
      setDiagnostics(diag);
    } catch (err: unknown) {
      console.error('Error cargando diagnóstico:', err);
    } finally {
      setLoadingDiagnostics(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Por favor selecciona un archivo CSV');
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const data = await uploadCabinetLeadsCSV(file, autoProcess, skipAlreadyProcessed);
      setResult(data);
      await loadDiagnostics();

      if (autoProcess && data.stats.total_inserted > 0) {
        setTimeout(() => {
          router.push('/runs');
        }, 3000);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message || 'Error al subir el archivo');
      } else if (err instanceof Error) {
        setError(err.message || 'Error al subir el archivo');
      } else {
        setError('Error desconocido');
      }
    } finally {
      setUploading(false);
    }
  };

  if (loadingDiagnostics) {
    return <PageLoadingOverlay title="Cargar Leads" subtitle="Cargando diagnóstico del sistema..." />;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Cargar Leads Cabinet</h1>
          <p className="text-slate-600">Importa leads desde archivo CSV para procesamiento</p>
        </div>
        <button
          onClick={loadDiagnostics}
          disabled={loadingDiagnostics}
          className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loadingDiagnostics ? (
            <div className="w-4 h-4 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" />
          ) : Icons.refresh}
          Actualizar Estado
        </button>
      </div>

      {/* System Status KPIs */}
      {diagnostics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            title="Estado Tabla"
            value={diagnostics.table_exists ? 'OK' : 'Error'}
            subtitle={diagnostics.table_exists ? 'Tabla disponible' : 'No existe'}
            icon={Icons.database}
            variant={diagnostics.table_exists ? 'success' : 'error'}
          />
          <StatCard
            title="Registros"
            value={diagnostics.table_row_count.toLocaleString()}
            subtitle="en module_ct_cabinet_leads"
            icon={Icons.database}
            variant="default"
          />
          <StatCard
            title="Última Fecha"
            value={diagnostics.max_lead_date_in_table?.split('T')[0] || '—'}
            subtitle="en tabla leads"
            icon={Icons.calendar}
            variant="default"
          />
          <StatCard
            title="IDs Procesados"
            value={diagnostics.processed_external_ids_count.toLocaleString()}
            subtitle="external_ids únicos"
            icon={Icons.check}
            variant="success"
          />
        </div>
      )}

      {/* Recommendation Banner */}
      {diagnostics?.recommended_start_date && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="text-amber-500">{Icons.alert}</div>
            <div>
              <p className="font-medium text-amber-800">Recomendación</p>
              <p className="text-sm text-amber-700 mt-1">
                Subir datos desde el <strong>{diagnostics.recommended_start_date}</strong> en adelante.
                {skipAlreadyProcessed && ' Los registros anteriores se omitirán automáticamente.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
        {/* Drag & Drop Zone */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            dragActive 
              ? 'border-cyan-500 bg-cyan-50' 
              : file 
              ? 'border-emerald-300 bg-emerald-50' 
              : 'border-slate-200 hover:border-slate-300'
          }`}
        >
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={uploading}
          />
          
          <div className="flex flex-col items-center">
            <div className={`w-14 h-14 rounded-full flex items-center justify-center mb-4 ${
              file ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'
            }`}>
              {file ? Icons.check : Icons.file}
            </div>
            
            {file ? (
              <>
                <p className="text-sm font-medium text-slate-900">{file.name}</p>
                <p className="text-xs text-slate-500 mt-1">{(file.size / 1024).toFixed(2)} KB</p>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); setResult(null); }}
                  className="mt-2 text-xs text-red-600 hover:text-red-700"
                >
                  Cambiar archivo
                </button>
              </>
            ) : (
              <>
                <p className="text-sm font-medium text-slate-900">
                  Arrastra un archivo CSV aquí
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  o haz clic para seleccionar
                </p>
              </>
            )}
          </div>
        </div>

        {/* Options */}
        <div className="space-y-3">
          <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
            <input
              type="checkbox"
              checked={skipAlreadyProcessed}
              onChange={(e) => setSkipAlreadyProcessed(e.target.checked)}
              className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
              disabled={uploading}
            />
            <div>
              <p className="text-sm font-medium text-slate-900">Saltar registros ya procesados</p>
              <p className="text-xs text-slate-500">Solo procesar registros nuevos basado en fechas</p>
            </div>
          </label>
          
          <label className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg cursor-pointer hover:bg-slate-100 transition-colors">
            <input
              type="checkbox"
              checked={autoProcess}
              onChange={(e) => setAutoProcess(e.target.checked)}
              className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
              disabled={uploading}
            />
            <div>
              <p className="text-sm font-medium text-slate-900">Procesar automáticamente</p>
              <p className="text-xs text-slate-500">Ejecutar ingesta, atribución y refresh de vistas</p>
            </div>
          </label>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors font-medium disabled:bg-slate-300 disabled:cursor-not-allowed"
        >
          {uploading ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Procesando...
            </>
          ) : (
            <>
              {Icons.upload}
              Subir CSV
            </>
          )}
        </button>

        {/* Result */}
        {result && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="text-emerald-500">{Icons.check}</div>
              <div className="flex-1">
                <p className="font-medium text-emerald-800">Upload exitoso</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-emerald-700">Insertados:</span>{' '}
                    <strong>{result.stats.total_inserted}</strong>
                  </div>
                  <div>
                    <span className="text-emerald-700">Ignorados:</span>{' '}
                    <strong>{result.stats.total_ignored}</strong>
                  </div>
                  {result.stats.skipped_by_date !== undefined && result.stats.skipped_by_date > 0 && (
                    <div>
                      <span className="text-blue-700">Saltados por fecha:</span>{' '}
                      <strong>{result.stats.skipped_by_date}</strong>
                    </div>
                  )}
                  <div>
                    <span className="text-emerald-700">Total procesado:</span>{' '}
                    <strong>{result.stats.total_rows}</strong>
                  </div>
                </div>
                {result.stats.auto_process && (
                  <p className="mt-3 text-sm text-emerald-700 font-medium">
                    ⏳ Redirigiendo a corridas...
                  </p>
                )}
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

      {/* Instructions */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-900 mb-4">Instrucciones</h2>
        <div className="space-y-3 text-sm text-slate-600">
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">1</span>
            <p>El CSV debe tener las columnas: <code className="bg-white px-1.5 py-0.5 rounded border text-xs">external_id</code>, <code className="bg-white px-1.5 py-0.5 rounded border text-xs">lead_created_at</code>, <code className="bg-white px-1.5 py-0.5 rounded border text-xs">first_name</code>, <code className="bg-white px-1.5 py-0.5 rounded border text-xs">last_name</code>, etc.</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">2</span>
            <p>Formato de fecha: <code className="bg-white px-1.5 py-0.5 rounded border text-xs">YYYY-MM-DDTHH:MM:SS</code> o <code className="bg-white px-1.5 py-0.5 rounded border text-xs">YYYY-MM-DD</code></p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">3</span>
            <p>Los registros duplicados (mismo <code className="bg-white px-1.5 py-0.5 rounded border text-xs">external_id</code>) se ignorarán automáticamente</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-slate-200 rounded-full flex items-center justify-center text-xs font-medium">4</span>
            <p>El procesamiento puede tardar varios minutos para archivos grandes</p>
          </div>
        </div>
      </div>
    </div>
  );
}
