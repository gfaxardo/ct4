/**
 * Upload CSV de Cabinet Leads
 * 
 * Permite subir CSV de leads y procesarlos automáticamente
 */

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { uploadCabinetLeadsCSV, getCabinetLeadsDiagnostics, ApiError } from '@/lib/api';
import type { CabinetLeadsUploadResponse, CabinetLeadsDiagnostics } from '@/lib/api';

export default function CabinetLeadsUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CabinetLeadsUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoProcess, setAutoProcess] = useState(true);
  const [skipAlreadyProcessed, setSkipAlreadyProcessed] = useState(true);
  const [diagnostics, setDiagnostics] = useState<CabinetLeadsDiagnostics | null>(null);
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(true);
  const router = useRouter();

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const loadDiagnostics = async () => {
    try {
      setLoadingDiagnostics(true);
      const diag = await getCabinetLeadsDiagnostics();
      setDiagnostics(diag);
    } catch (err: any) {
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
      // Recargar diagnóstico después del upload
      await loadDiagnostics();

      // Si el procesamiento automático está habilitado, redirigir después de un delay
      if (autoProcess && data.stats.total_inserted > 0) {
        setTimeout(() => {
          router.push('/runs');
        }, 3000);
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.detail || err.message || 'Error al subir el archivo');
      } else {
        setError(err.message || 'Error al subir el archivo');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Cargar Leads Cabinet (CSV)</h1>

      {/* Panel de Diagnóstico */}
      {loadingDiagnostics ? (
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-gray-600">Cargando diagnóstico...</p>
        </div>
      ) : diagnostics && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
          <h2 className="font-semibold text-blue-900 mb-3">📊 Estado del Sistema</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium">Tabla existe:</span>{' '}
              <span className={diagnostics.table_exists ? 'text-green-700' : 'text-red-700'}>
                {diagnostics.table_exists ? '✅ Sí' : '❌ No'}
              </span>
            </div>
            <div>
              <span className="font-medium">Registros en tabla:</span>{' '}
              <span className="text-gray-700">{diagnostics.table_row_count.toLocaleString()}</span>
            </div>
            {diagnostics.max_lead_date_in_table && (
              <div>
                <span className="font-medium">Última fecha en tabla:</span>{' '}
                <span className="text-gray-700">{diagnostics.max_lead_date_in_table}</span>
              </div>
            )}
            {diagnostics.max_event_date_in_lead_events && (
              <div>
                <span className="font-medium">Última fecha procesada (lead_events):</span>{' '}
                <span className="text-green-700">{diagnostics.max_event_date_in_lead_events}</span>
              </div>
            )}
            {diagnostics.max_snapshot_date_in_identity_links && (
              <div>
                <span className="font-medium">Última fecha procesada (identity_links):</span>{' '}
                <span className="text-green-700">{diagnostics.max_snapshot_date_in_identity_links}</span>
              </div>
            )}
            {diagnostics.recommended_start_date && (
              <div className="col-span-2 bg-yellow-50 border border-yellow-200 rounded p-3 mt-2">
                <span className="font-semibold text-yellow-900">💡 Recomendación:</span>{' '}
                <span className="text-yellow-800">
                  Subir datos desde el <strong>{diagnostics.recommended_start_date}</strong> en adelante
                  {skipAlreadyProcessed && ' (se aplicará automáticamente si "Saltar ya procesados" está activado)'}
                </span>
              </div>
            )}
            {diagnostics.processed_external_ids_count > 0 && (
              <div className="col-span-2">
                <span className="font-medium">External IDs ya procesados:</span>{' '}
                <span className="text-gray-700">{diagnostics.processed_external_ids_count.toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Selector de archivo */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Seleccionar archivo CSV
          </label>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100"
            disabled={uploading}
          />
          {file && (
            <p className="mt-2 text-sm text-gray-600">
              Archivo seleccionado: {file.name} ({(file.size / 1024).toFixed(2)} KB)
            </p>
          )}
        </div>

        {/* Opción de saltar datos ya procesados */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="skipAlreadyProcessed"
            checked={skipAlreadyProcessed}
            onChange={(e) => setSkipAlreadyProcessed(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
            disabled={uploading}
          />
          <label htmlFor="skipAlreadyProcessed" className="text-sm font-medium">
            Saltar datos ya procesados (solo procesar registros nuevos basado en fechas ya procesadas)
          </label>
        </div>

        {/* Opción de procesamiento automático */}
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="autoProcess"
            checked={autoProcess}
            onChange={(e) => setAutoProcess(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded"
            disabled={uploading}
          />
          <label htmlFor="autoProcess" className="text-sm font-medium">
            Procesar automáticamente después del upload (ejecuta ingesta de identidad, atribución y refresh de vistas)
          </label>
        </div>

        {/* Botón de upload */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {uploading ? 'Subiendo y procesando...' : 'Subir CSV'}
        </button>

        {/* Resultado */}
        {result && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded">
            <h3 className="font-semibold text-green-800 mb-2">✅ Upload exitoso</h3>
            <div className="text-sm text-green-700 space-y-1">
              <p>Registros insertados: <strong>{result.stats.total_inserted}</strong></p>
              <p>Registros ignorados (duplicados): <strong>{result.stats.total_ignored}</strong></p>
              {result.stats.skipped_by_date !== undefined && result.stats.skipped_by_date > 0 && (
                <p className="text-blue-700">
                  Registros saltados por fecha (ya procesados): <strong>{result.stats.skipped_by_date}</strong>
                </p>
              )}
              {result.stats.date_cutoff_used && (
                <p className="text-gray-600 text-xs">
                  Fecha de corte usada: <strong>{result.stats.date_cutoff_used}</strong>
                </p>
              )}
              <p>Total procesado: <strong>{result.stats.total_rows}</strong></p>
              {result.stats.errors_count > 0 && (
                <p className="text-yellow-700">
                  Errores: <strong>{result.stats.errors_count}</strong>
                </p>
              )}
              {result.stats.auto_process && (
                <p className="mt-2 font-medium">
                  ⏳ Procesamiento automático iniciado. Redirigiendo a corridas...
                </p>
              )}
            </div>
            {result.errors.length > 0 && (
              <div className="mt-3 text-xs text-red-700">
                <p className="font-semibold">Errores encontrados:</p>
                <ul className="list-disc list-inside mt-1">
                  {result.errors.map((err, idx) => (
                    <li key={idx}>{err}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded">
            <h3 className="font-semibold text-red-800 mb-2">❌ Error</h3>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </div>

      {/* Instrucciones */}
      <div className="mt-6 bg-gray-50 rounded-lg p-6">
        <h2 className="font-semibold mb-3">Instrucciones</h2>
        <ul className="text-sm text-gray-700 space-y-2 list-disc list-inside">
          <li>El CSV debe tener las columnas: <code className="bg-gray-200 px-1 rounded">external_id</code>, <code className="bg-gray-200 px-1 rounded">lead_created_at</code>, <code className="bg-gray-200 px-1 rounded">first_name</code>, <code className="bg-gray-200 px-1 rounded">last_name</code>, etc.</li>
          <li>El formato de fecha debe ser: <code className="bg-gray-200 px-1 rounded">YYYY-MM-DDTHH:MM:SS</code> o <code className="bg-gray-200 px-1 rounded">YYYY-MM-DD</code></li>
          <li>Si activas "Procesar automáticamente", se ejecutará:
            <ul className="list-disc list-inside ml-6 mt-1">
              <li>Ingesta de identidad (matching de leads con personas)</li>
              <li>Atribución de leads (creación de eventos en lead_events)</li>
              <li>Refresh de vistas materializadas (claims y financial)</li>
            </ul>
          </li>
          <li>Los registros duplicados (mismo <code className="bg-gray-200 px-1 rounded">external_id</code>) se ignorarán automáticamente</li>
          <li>El procesamiento puede tardar varios minutos para archivos grandes</li>
        </ul>
      </div>
    </div>
  );
}

