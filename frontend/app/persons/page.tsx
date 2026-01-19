/**
 * Personas - Listado de personas en el registro canónico
 * Diseño moderno consistente con el resto del sistema
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getPersons, ApiError } from '@/lib/api';
import type { IdentityRegistry } from '@/lib/types';
import Badge from '@/components/Badge';
import StatCard from '@/components/StatCard';
import Pagination from '@/components/Pagination';
import { PageLoadingOverlay } from '@/components/Skeleton';

// Icons
const Icons = {
  users: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
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
  search: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  refresh: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

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
  const [limit] = useState(50);
  const [total, setTotal] = useState(0);

  async function loadPersons() {
    try {
      setLoading(true);
      setError(null);
      const data = await getPersons({ ...filters, skip, limit });
      setPersons(data);
      setTotal(data.length === limit ? skip + limit + 1 : skip + data.length);
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

  useEffect(() => {
    loadPersons();
  }, [filters, skip, limit]);

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setSkip(0);
  };

  const handleClearFilters = () => {
    setFilters({ phone: '', document: '', license: '', name: '', confidence_level: '' });
    setSkip(0);
  };

  if (loading && persons.length === 0) {
    return <PageLoadingOverlay title="Personas" subtitle="Cargando registro de identidad..." />;
  }

  // Calcular KPIs
  const highCount = persons.filter(p => p.confidence_level === 'HIGH').length;
  const mediumCount = persons.filter(p => p.confidence_level === 'MEDIUM').length;
  const lowCount = persons.filter(p => p.confidence_level === 'LOW').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Registro de Personas</h1>
          <p className="text-slate-600">Registro canónico de identidad del sistema</p>
        </div>
        <button
          onClick={loadPersons}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-[#ef0000] text-white rounded-lg hover:bg-[#cc0000] transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : Icons.refresh}
          Actualizar
        </button>
      </div>

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

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Personas"
          value={persons.length.toLocaleString()}
          subtitle="en esta página"
          icon={Icons.users}
          variant="default"
        />
        <StatCard
          title="Confianza Alta"
          value={highCount.toLocaleString()}
          subtitle="HIGH"
          icon={Icons.check}
          variant="success"
        />
        <StatCard
          title="Confianza Media"
          value={mediumCount.toLocaleString()}
          subtitle="MEDIUM"
          icon={Icons.alert}
          variant="warning"
        />
        <StatCard
          title="Confianza Baja"
          value={lowCount.toLocaleString()}
          subtitle="LOW"
          icon={Icons.alert}
          variant="error"
        />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Teléfono</label>
            <div className="relative">
              <input
                type="text"
                value={filters.phone}
                onChange={(e) => handleFilterChange('phone', e.target.value)}
                placeholder="+51..."
                className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
              />
              <div className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400">{Icons.search}</div>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Documento</label>
            <input
              type="text"
              value={filters.document}
              onChange={(e) => handleFilterChange('document', e.target.value)}
              placeholder="DNI..."
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Licencia</label>
            <input
              type="text"
              value={filters.license}
              onChange={(e) => handleFilterChange('license', e.target.value)}
              placeholder="Licencia..."
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Nombre</label>
            <input
              type="text"
              value={filters.name}
              onChange={(e) => handleFilterChange('name', e.target.value)}
              placeholder="Buscar..."
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Confianza</label>
            <select
              value={filters.confidence_level}
              onChange={(e) => handleFilterChange('confidence_level', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-[#ef0000] focus:border-transparent"
            >
              <option value="">Todos</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
          </div>
        </div>
        <div className="mt-3 flex justify-end">
          <button
            onClick={handleClearFilters}
            className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800"
          >
            Limpiar filtros
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
            <div className="w-8 h-8 border-3 border-[#ef0000] border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {persons.length === 0 ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3 text-slate-400">
              {Icons.users}
            </div>
            <p className="text-slate-600 font-medium">No se encontraron personas</p>
            <p className="text-sm text-slate-500 mt-1">Ajusta los filtros de búsqueda</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Person Key</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Nombre</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Teléfono</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Documento</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Licencia</th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Confianza</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase">Creado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {persons.map((person) => (
                  <tr
                    key={person.person_key}
                    className="hover:bg-slate-50/50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/persons/${person.person_key}`)}
                  >
                    <td className="py-3 px-4 text-sm font-mono text-[#ef0000] hover:underline">
                      {person.person_key.substring(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-sm font-medium text-slate-900">
                      {person.primary_full_name || '—'}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {person.primary_phone || '—'}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {person.primary_document || '—'}
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-600">
                      {person.primary_license || '—'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant={
                        person.confidence_level === 'HIGH' ? 'success' :
                        person.confidence_level === 'MEDIUM' ? 'warning' : 'error'
                      }>
                        {person.confidence_level}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-500">
                      {new Date(person.created_at).toLocaleDateString('es-ES')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {persons.length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 bg-slate-50">
            <Pagination
              total={total}
              limit={limit}
              offset={skip}
              onPageChange={(newOffset) => setSkip(newOffset)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
