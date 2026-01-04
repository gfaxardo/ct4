/**
 * Resumen por Conductor - Matriz de drivers con milestones M1/M5/M25
 * 
 * Objetivo: "¿Qué estado tienen los pagos por conductor y milestone?"
 */

'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getDriverMatrix, exportDriverMatrix, ApiError } from '@/lib/api';
import type { DriverMatrixResponse, DriverMatrixRow } from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Badge from '@/components/Badge';
import PaymentsLegend from '@/components/payments/PaymentsLegend';
import MilestoneCell from '@/components/payments/MilestoneCell';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function ResumenConductorPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<DriverMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filtros desde URL o defaults
  const [filters, setFilters] = useState({
    week_from: searchParams.get('week_from') || '',
    week_to: searchParams.get('week_to') || '',
    search: searchParams.get('search') || '',
    only_pending: searchParams.get('only_pending') === 'true',
  });
  
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '50', 10));
  
  // Debounce para search
  const [searchDebounce, setSearchDebounce] = useState<NodeJS.Timeout | null>(null);

  // Actualizar URL cuando cambian filtros
  const updateURL = useCallback((newFilters: typeof filters, newPage: number, newLimit: number) => {
    const params = new URLSearchParams();
    if (newFilters.week_from) params.set('week_from', newFilters.week_from);
    if (newFilters.week_to) params.set('week_to', newFilters.week_to);
    if (newFilters.search) params.set('search', newFilters.search);
    if (newFilters.only_pending) params.set('only_pending', 'true');
    if (newPage > 1) params.set('page', newPage.toString());
    if (newLimit !== 50) params.set('limit', newLimit.toString());
    
    router.push(`/pagos/resumen-conductor?${params.toString()}`);
  }, [router]);

  // Cargar datos
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await getDriverMatrix({
          week_from: filters.week_from || undefined,
          week_to: filters.week_to || undefined,
          search: filters.search || undefined,
          only_pending: filters.only_pending || undefined,
          page,
          limit,
        });

        setData(response);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar datos');
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

    loadData();
  }, [filters, page, limit]);

  // Handler para cambios en filtros con debounce en search
  const handleFilterChange = useCallback((name: string, value: any) => {
    const newFilters = { ...filters, [name]: value };
    setFilters(newFilters);
    
    // Resetear página cuando cambian filtros
    setPage(1);
    
    // Debounce para search
    if (name === 'search') {
      if (searchDebounce) {
        clearTimeout(searchDebounce);
      }
      const timeout = setTimeout(() => {
        updateURL(newFilters, 1, limit);
      }, 300);
      setSearchDebounce(timeout);
    } else {
      updateURL(newFilters, 1, limit);
    }
  }, [filters, limit, updateURL, searchDebounce]);

  // Handler para limpiar filtros
  const handleResetFilters = useCallback(() => {
    const emptyFilters = {
      week_from: '',
      week_to: '',
      search: '',
      only_pending: false,
    };
    setFilters(emptyFilters);
    setPage(1);
    updateURL(emptyFilters, 1, limit);
  }, [limit, updateURL]);

  // Handler para export CSV
  const handleExportCSV = useCallback(async () => {
    try {
      const blob = await exportDriverMatrix({
        week_from: filters.week_from || undefined,
        week_to: filters.week_to || undefined,
        search: filters.search || undefined,
        only_pending: filters.only_pending || undefined,
      });

      // Crear link de descarga
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `driver_matrix_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Error al exportar: ${err.detail || err.message}`);
      } else {
        alert('Error desconocido al exportar');
      }
    }
  }, [filters]);

  // Columnas de la tabla
  const columns = [
    {
      key: 'driver',
      header: 'Driver',
      render: (row: DriverMatrixRow) => (
        <div>
          <div className="font-bold text-gray-900">{row.driver_name || 'Sin nombre'}</div>
          <div className="text-xs text-gray-500">{row.driver_id || '—'}</div>
        </div>
      ),
    },
    {
      key: 'origin_tag',
      header: 'Origen',
      render: (row: DriverMatrixRow) => (
        <Badge variant={row.origin_tag === 'cabinet' ? 'info' : 'default'}>
          {row.origin_tag || '—'}
        </Badge>
      ),
    },
    {
      key: 'connected',
      header: 'Conectado',
      render: (row: DriverMatrixRow) => (
        <div className="flex items-center gap-2">
          {row.connected_flag ? (
            <>
              <span className="text-green-600">✓</span>
              {row.connected_date && (
                <span className="text-sm text-gray-600">
                  {new Date(row.connected_date).toLocaleDateString('es-ES')}
                </span>
              )}
            </>
          ) : (
            <span className="text-gray-400">No</span>
          )}
        </div>
      ),
    },
    {
      key: 'm1',
      header: 'M1',
      render: (row: DriverMatrixRow) => (
        <MilestoneCell
          achieved_flag={row.m1_achieved_flag}
          achieved_date={row.m1_achieved_date}
          expected_amount_yango={row.m1_expected_amount_yango}
          yango_payment_status={row.m1_yango_payment_status}
          window_status={row.m1_window_status}
          overdue_days={row.m1_overdue_days}
        />
      ),
    },
    {
      key: 'm5',
      header: 'M5',
      render: (row: DriverMatrixRow) => (
        <MilestoneCell
          achieved_flag={row.m5_achieved_flag}
          achieved_date={row.m5_achieved_date}
          expected_amount_yango={row.m5_expected_amount_yango}
          yango_payment_status={row.m5_yango_payment_status}
          window_status={row.m5_window_status}
          overdue_days={row.m5_overdue_days}
        />
      ),
    },
    {
      key: 'm25',
      header: 'M25',
      render: (row: DriverMatrixRow) => (
        <MilestoneCell
          achieved_flag={row.m25_achieved_flag}
          achieved_date={row.m25_achieved_date}
          expected_amount_yango={row.m25_expected_amount_yango}
          yango_payment_status={row.m25_yango_payment_status}
          window_status={row.m25_window_status}
          overdue_days={row.m25_overdue_days}
        />
      ),
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Resumen por Conductor</h1>
          <PaymentsLegend />
        </div>
        <button
          onClick={handleExportCSV}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
        >
          Exportar CSV
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Dashboard Cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          <StatCard
            title="Drivers"
            value={data.totals.drivers}
          />
          <StatCard
            title="Expected Yango"
            value={`S/ ${data.totals.expected_yango_sum.toFixed(2)}`}
          />
          <StatCard
            title="Paid"
            value={`S/ ${data.totals.paid_sum.toFixed(2)}`}
          />
          <StatCard
            title="Receivable"
            value={`S/ ${data.totals.receivable_sum.toFixed(2)}`}
          />
          <StatCard
            title="Expired"
            value={data.totals.expired_count}
            subtitle="claims vencidos"
          />
          <StatCard
            title="In Window"
            value={data.totals.in_window_count}
            subtitle="claims en ventana"
          />
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Semana Desde
            </label>
            <input
              type="date"
              value={filters.week_from}
              onChange={(e) => handleFilterChange('week_from', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Semana Hasta
            </label>
            <input
              type="date"
              value={filters.week_to}
              onChange={(e) => handleFilterChange('week_to', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buscar
            </label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="driver_id, person_key, nombre"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Solo Pendientes
            </label>
            <div className="flex items-center h-10">
              <input
                type="checkbox"
                checked={filters.only_pending}
                onChange={(e) => handleFilterChange('only_pending', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label className="ml-2 text-sm text-gray-700">Mostrar solo pendientes</label>
            </div>
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleResetFilters}
            className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Limpiar Filtros
          </button>
        </div>
      </div>

      {/* Tabla */}
      <DataTable
        data={data?.rows || []}
        columns={columns}
        loading={loading}
        emptyMessage="No hay drivers que coincidan con los filtros"
      />

      {/* Paginación */}
      {!loading && data && data.rows.length > 0 && (
        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-700">
              Mostrando {((page - 1) * limit) + 1} a {Math.min(page * limit, data.meta.total_rows)} de {data.meta.total_rows} resultados
            </span>
            <select
              value={limit}
              onChange={(e) => {
                const newLimit = parseInt(e.target.value, 10);
                setLimit(newLimit);
                setPage(1);
                updateURL(filters, 1, newLimit);
              }}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm"
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
              <option value="500">500</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const newPage = Math.max(1, page - 1);
                setPage(newPage);
                updateURL(filters, newPage, limit);
              }}
              disabled={page === 1}
              className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Anterior
            </button>
            <span className="text-sm text-gray-700">
              Página {page} de {Math.ceil(data.meta.total_rows / limit)}
            </span>
            <button
              onClick={() => {
                const newPage = Math.min(Math.ceil(data.meta.total_rows / limit), page + 1);
                setPage(newPage);
                updateURL(filters, newPage, limit);
              }}
              disabled={page >= Math.ceil(data.meta.total_rows / limit)}
              className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResumenConductorPage() {
  return (
    <Suspense fallback={<div className="px-4 py-6">Cargando...</div>}>
      <ResumenConductorPageContent />
    </Suspense>
  );
}

