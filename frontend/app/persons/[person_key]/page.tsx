/**
 * Person Detail - Detalle de persona
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué información tiene esta persona y a qué fuentes está vinculada?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getPerson, ApiError } from '@/lib/api';
import type { PersonDetail } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Badge from '@/components/Badge';

export default function PersonDetailPage() {
  const params = useParams();
  const router = useRouter();
  const personKey = params.person_key as string;
  const [personDetail, setPersonDetail] = useState<PersonDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPerson() {
      try {
        setLoading(true);
        setError(null);
        const data = await getPerson(personKey);
        setPersonDetail(data);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setError('Persona no encontrada');
          } else if (err.status === 500) {
            setError('Error al cargar detalle de persona');
          } else {
            setError(`Error ${err.status}: ${err.detail || err.message}`);
          }
        } else {
          setError('Error desconocido');
        }
      } finally {
        setLoading(false);
      }
    }

    if (personKey) {
      loadPerson();
    }
  }, [personKey]);

  if (loading) {
    return <div className="text-center py-12">Cargando detalle de persona...</div>;
  }

  if (error) {
    return (
      <div className="px-4 py-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-800 mb-4">{error}</p>
          {error === 'Persona no encontrada' && (
            <button
              onClick={() => router.push('/persons')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Volver a Personas
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!personDetail) {
    return <div className="text-center py-12">Persona no encontrada</div>;
  }

  const { person, links, driver_links, has_driver_conversion } = personDetail;

  const linksColumns = [
    { key: 'source_table', header: 'Tabla Fuente' },
    { key: 'source_pk', header: 'PK Fuente' },
    { key: 'match_rule', header: 'Regla de Match' },
    { key: 'match_score', header: 'Score' },
    {
      key: 'confidence_level',
      header: 'Confianza',
      render: (row: typeof links[0]) => (
        <Badge
          variant={
            row.confidence_level === 'HIGH'
              ? 'success'
              : row.confidence_level === 'MEDIUM'
              ? 'warning'
              : 'error'
          }
        >
          {row.confidence_level}
        </Badge>
      ),
    },
    {
      key: 'snapshot_date',
      header: 'Snapshot',
      render: (row: typeof links[0]) => new Date(row.snapshot_date).toLocaleDateString('es-ES'),
    },
    {
      key: 'linked_at',
      header: 'Vinculado',
      render: (row: typeof links[0]) => new Date(row.linked_at).toLocaleDateString('es-ES'),
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <button
          onClick={() => router.push('/persons')}
          className="text-blue-600 hover:text-blue-800 mb-4"
        >
          ← Volver a Personas
        </button>
        <h1 className="text-3xl font-bold">Detalle de Persona</h1>
      </div>

      {/* Person Card */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Información de la Persona</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Person Key</p>
            <p className="font-mono text-sm">{person.person_key}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Confianza</p>
            <Badge
              variant={
                person.confidence_level === 'HIGH'
                  ? 'success'
                  : person.confidence_level === 'MEDIUM'
                  ? 'warning'
                  : 'error'
              }
            >
              {person.confidence_level}
            </Badge>
          </div>
          <div>
            <p className="text-sm text-gray-500">Nombre Completo</p>
            <p>{person.primary_full_name || '—'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Teléfono</p>
            <p>{person.primary_phone || '—'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Documento</p>
            <p>{person.primary_document || '—'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Licencia</p>
            <p>{person.primary_license || '—'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Creado</p>
            <p>{new Date(person.created_at).toLocaleString('es-ES')}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Actualizado</p>
            <p>{new Date(person.updated_at).toLocaleString('es-ES')}</p>
          </div>
        </div>
      </div>

      {/* Driver Conversion Badge */}
      <div className="mb-6">
        {has_driver_conversion ? (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800">✓ Tiene conversión a driver</p>
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-gray-800">✗ Sin conversión a driver</p>
          </div>
        )}
      </div>

      {/* Links Table */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4">Links ({links.length})</h2>
        {links.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">Esta persona no tiene links asociados</p>
          </div>
        ) : (
          <DataTable data={links} columns={linksColumns} />
        )}
      </div>

      {/* Driver Links Section */}
      {driver_links && driver_links.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Driver Links ({driver_links.length})</h2>
          <DataTable data={driver_links} columns={linksColumns} />
        </div>
      )}
    </div>
  );
}
