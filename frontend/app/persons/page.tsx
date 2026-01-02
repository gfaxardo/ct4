/**
 * Persons - Listado de personas
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué personas están en el registro canónico?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getPersons, ApiError } from '@/lib/api';
import type { IdentityRegistry } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function PersonsPage() {
  const router = useRouter();
  const [persons, setPersons] = useState<IdentityRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    phone: '',
    document: '',
    license: '',
    name: '',
    confidence_level: '',
  });
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(100);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    async function loadPersons() {
      try {
        setLoading(true);
        setError(null);

        const data = await getPersons({
          ...filters,
          skip,
          limit,
        });

        setPersons(data);
        // Nota: El endpoint retorna array directo, no tiene total
        // Por ahora asumimos que si hay datos, hay más páginas
        setTotal(data.length === limit ? skip + limit + 1 : skip + data.length);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Nivel de confianza inválido');
          } else if (err.status === 500) {
            setError('Error al cargar personas');
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

    loadPersons();
  }, [filters, skip, limit]);

  const filterFields = [
    { name: 'phone', label: 'Teléfono', type: 'text' as const, placeholder: 'Ej: +51987654321' },
    { name: 'document', label: 'Documento', type: 'text' as const },
    { name: 'license', label: 'Licencia', type: 'text' as const },
    { name: 'name', label: 'Nombre', type: 'text' as const },
    {
      name: 'confidence_level',
      label: 'Confianza',
      type: 'select' as const,
      options: [
        { value: 'HIGH', label: 'HIGH' },
        { value: 'MEDIUM', label: 'MEDIUM' },
        { value: 'LOW', label: 'LOW' },
      ],
    },
  ];

  const columns = [
    {
      key: 'person_key',
      header: 'Person Key',
      render: (row: IdentityRegistry) => (
        <button
          onClick={() => router.push(`/persons/${row.person_key}`)}
          className="text-blue-600 hover:text-blue-800 underline"
        >
          {row.person_key}
        </button>
      ),
    },
    { key: 'primary_full_name', header: 'Nombre Completo' },
    { key: 'primary_phone', header: 'Teléfono' },
    { key: 'primary_document', header: 'Documento' },
    { key: 'primary_license', header: 'Licencia' },
    {
      key: 'confidence_level',
      header: 'Confianza',
      render: (row: IdentityRegistry) => (
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
      key: 'created_at',
      header: 'Creado',
      render: (row: IdentityRegistry) => new Date(row.created_at).toLocaleDateString('es-ES'),
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Personas</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => setFilters(values as typeof filters)}
        onReset={() => {
          setFilters({ phone: '', document: '', license: '', name: '', confidence_level: '' });
          setSkip(0);
        }}
      />

      <DataTable
        data={persons}
        columns={columns}
        loading={loading}
        emptyMessage="No se encontraron personas que coincidan con los filtros"
      />

      {!loading && persons.length > 0 && (
        <Pagination
          total={total}
          limit={limit}
          offset={skip}
          onPageChange={(newOffset) => setSkip(newOffset)}
        />
      )}
    </div>
  );
}
