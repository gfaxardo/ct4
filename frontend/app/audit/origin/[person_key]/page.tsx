'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getOriginAuditDetail, resolveOriginViolation, markAsLegacy, ApiError } from '@/lib/api';
import type { OriginAuditRow } from '@/lib/types';

export default function OriginAuditDetailPage() {
  const params = useParams();
  const personKey = params.person_key as string;
  
  const [data, setData] = useState<OriginAuditRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const result = await getOriginAuditDetail(personKey);
        setData(result);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Error ${err.status}: ${err.detail || err.message}`);
        } else {
          setError('Error desconocido');
        }
      } finally {
        setLoading(false);
      }
    }

    if (personKey) {
      loadData();
    }
  }, [personKey]);

  const handleResolve = async () => {
    if (!data) return;
    
    setResolving(true);
    try {
      await resolveOriginViolation(personKey, {
        resolution_status: 'resolved_manual',
        origin_tag: data.origin_tag as any,
        origin_source_id: data.origin_source_id || '',
        notes: 'Resuelto desde UI',
      });
      // Recargar datos
      const result = await getOriginAuditDetail(personKey);
      setData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.detail || err.message}`);
      }
    } finally {
      setResolving(false);
    }
  };

  const handleMarkLegacy = async () => {
    if (!data) return;
    
    setResolving(true);
    try {
      await markAsLegacy(personKey, {
        notes: 'Marcado como legacy desde UI',
      });
      // Recargar datos
      const result = await getOriginAuditDetail(personKey);
      setData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.detail || err.message}`);
      }
    } finally {
      setResolving(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12">Cargando...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!data) {
    return <div className="text-center py-12">Persona no encontrada</div>;
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <Link href="/audit/origin" className="text-blue-600 hover:underline">
          ← Volver a Auditoría
        </Link>
      </div>

      <h1 className="text-3xl font-bold mb-6">Detalle de Auditoría</h1>

      {/* Información Principal */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Información de Persona</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Person Key</label>
            <p className="text-sm">{data.person_key}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Driver ID</label>
            <p className="text-sm">{data.driver_id || '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">First Seen At</label>
            <p className="text-sm">{data.first_seen_at ? new Date(data.first_seen_at).toLocaleString() : '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Has Lead Links</label>
            <p className="text-sm">{data.has_lead_links ? 'Sí' : 'No'}</p>
          </div>
        </div>
      </div>

      {/* Información de Origen */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Información de Origen</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Origin Tag</label>
            <p className="text-sm">
              {data.origin_tag ? (
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                  {data.origin_tag}
                </span>
              ) : (
                '-'
              )}
            </p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Origin Source ID</label>
            <p className="text-sm">{data.origin_source_id || '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Origin Confidence</label>
            <p className="text-sm">{data.origin_confidence ? `${data.origin_confidence.toFixed(2)}%` : '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Origin Created At</label>
            <p className="text-sm">{data.origin_created_at ? new Date(data.origin_created_at).toLocaleString() : '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Ruleset Version</label>
            <p className="text-sm">{data.ruleset_version || '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Decided By</label>
            <p className="text-sm">{data.decided_by || '-'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Resolution Status</label>
            <p className="text-sm">
              {data.resolution_status ? (
                <span
                  className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    data.resolution_status === 'resolved_auto' || data.resolution_status === 'resolved_manual'
                      ? 'bg-green-100 text-green-800'
                      : data.resolution_status === 'pending_review'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {data.resolution_status}
                </span>
              ) : (
                '-'
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Violación */}
      {data.violation_flag && (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-red-800">Violación Detectada</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-red-700">Razón</label>
              <p className="text-sm text-red-800">{data.violation_reason || 'Desconocida'}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-red-700">Acción Recomendada</label>
              <p className="text-sm text-red-800">{data.recommended_action || '-'}</p>
            </div>
          </div>
          
          {/* Acciones */}
          <div className="mt-4 flex gap-4">
            <button
              onClick={handleResolve}
              disabled={resolving}
              className="px-4 py-2 bg-green-600 text-white rounded-md disabled:opacity-50"
            >
              {resolving ? 'Resolviendo...' : 'Resolver Violación'}
            </button>
            {data.recommended_action === 'mark_legacy' && (
              <button
                onClick={handleMarkLegacy}
                disabled={resolving}
                className="px-4 py-2 bg-yellow-600 text-white rounded-md disabled:opacity-50"
              >
                {resolving ? 'Marcando...' : 'Marcar como Legacy'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Evidencia */}
      {data.origin_evidence && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Evidencia</h2>
          <pre className="bg-gray-50 p-4 rounded-md overflow-auto text-xs">
            {JSON.stringify(data.origin_evidence, null, 2)}
          </pre>
        </div>
      )}

      {/* Links Summary */}
      {data.links_summary && data.links_summary.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Resumen de Links</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source Table</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source PK</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Rule</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Match Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Linked At</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.links_summary.map((link, idx) => (
                  <tr key={idx}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{link.source_table}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{link.source_pk}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{link.match_rule}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{link.match_score}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {link.linked_at ? new Date(link.linked_at).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

