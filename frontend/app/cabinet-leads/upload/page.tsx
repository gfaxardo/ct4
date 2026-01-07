/**
 * Upload CSV de Cabinet Leads
 * 
 * Permite subir CSV de leads y procesarlos automáticamente
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { uploadCabinetLeadsCSV, ApiError } from '@/lib/api';
import type { CabinetLeadsUploadResponse } from '@/lib/api';

export default function CabinetLeadsUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CabinetLeadsUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoProcess, setAutoProcess] = useState(true);
  const router = useRouter();

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
      const data = await uploadCabinetLeadsCSV(file, autoProcess);
      setResult(data);

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


