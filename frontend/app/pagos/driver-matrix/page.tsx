/**
 * Driver Matrix - Matriz de drivers con milestones M1/M5/M25
 * 
 * Objetivo: "¿Qué drivers tienen qué milestones y cuál es su estado de pago?"
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getOpsDriverMatrix, ApiError } from '@/lib/api';
import type { DriverMatrixRow, OpsDriverMatrixResponse } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Badge from '@/components/Badge';
import Pagination from '@/components/Pagination';
import MilestoneCell from '@/components/payments/MilestoneCell';
import PaymentsLegend from '@/components/payments/PaymentsLegend';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function DriverMatrixPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<DriverMatrixRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<OpsDriverMatrixResponse['meta'] | null>(null);
  
  // Filtros desde URL o estado inicial
  const [filters, setFilters] = useState({
    origin_tag: searchParams.get('origin_tag') || '',
    only_pending: searchParams.get('only_pending') === 'true',
    order: (searchParams.get('order') as 'week_start_desc' | 'week_start_asc' | 'lead_date_desc' | 'lead_date_asc') || 'week_start_desc',
    search: searchParams.get('search') || '',
  });
  
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '200'));
  const [offset, setOffset] = useState(parseInt(searchParams.get('offset') || '0'));

  // Debounce para search
  const [searchDebounced, setSearchDebounced] = useState(filters.search);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(filters.search);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  // Actualizar URL cuando cambian filtros
  const updateURL = useCallback((newFilters: typeof filters, newLimit: number, newOffset: number) => {
    const params = new URLSearchParams();
    if (newFilters.origin_tag) params.set('origin_tag', newFilters.origin_tag);
    if (newFilters.only_pending) params.set('only_pending', 'true');
    if (newFilters.order !== 'week_start_desc') params.set('order', newFilters.order);
    if (newFilters.search) params.set('search', newFilters.search);
    if (newLimit !== 200) params.set('limit', newLimit.toString());
    if (newOffset !== 0) params.set('offset', newOffset.toString());
    
    const query = params.toString();
    router.push(`/pagos/driver-matrix${query ? `?${query}` : ''}`, { scroll: false });
  }, [router]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await getOpsDriverMatrix({
          origin_tag: filters.origin_tag || undefined,
          only_pending: filters.only_pending || undefined,
          order: filters.order,
          limit,
          offset,
        });

        setData(response.data);
        setMeta(response.meta);

        // Filtrar client-side por search si hay
        if (searchDebounced) {
          const filtered = response.data.filter((row) => {
            const searchLower = searchDebounced.toLowerCase();
            return (
              row.driver_name?.toLowerCase().includes(searchLower) ||
              row.driver_id?.toLowerCase().includes(searchLower) ||
              row.person_key?.toLowerCase().includes(searchLower)
            );
          });
          setData(filtered);
        }
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
  }, [filters.origin_tag, filters.only_pending, filters.order, limit, offset, searchDebounced]);

  const handleFilterChange = (key: keyof typeof filters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    setOffset(0); // Reset offset cuando cambian filtros
    updateURL(newFilters, limit, 0);
  };

  const handleResetFilters = () => {
    const newFilters = {
      origin_tag: '',
      only_pending: false,
      order: 'week_start_desc' as const,
      search: '',
    };
    setFilters(newFilters);
    setOffset(0);
    setLimit(200);
    updateURL(newFilters, 200, 0);
  };

  const handleExportCSV = () => {
    // Export client-side desde los datos cargados
    if (data.length === 0) {
      alert('No hay datos para exportar');
      return;
    }

    // Headers CSV
    const headers = [
      'driver_id',
      'person_key',
      'driver_name',
      'lead_date',
      'week_start',
      'origin_tag',
      'connected_flag',
      'connected_date',
      'm1_achieved_flag',
      'm1_achieved_date',
      'm1_expected_amount_yango',
      'm1_yango_payment_status',
      'm1_window_status',
      'm1_overdue_days',
      'm5_achieved_flag',
      'm5_achieved_date',
      'm5_expected_amount_yango',
      'm5_yango_payment_status',
      'm5_window_status',
      'm5_overdue_days',
      'm25_achieved_flag',
      'm25_achieved_date',
      'm25_expected_amount_yango',
      'm25_yango_payment_status',
      'm25_window_status',
      'm25_overdue_days',
      'scout_due_flag',
      'scout_paid_flag',
      'scout_amount',
    ];

    // Convertir datos a CSV
    const csvRows = [
      headers.join(','),
      ...data.map((row) =>
        headers
          .map((header) => {
            const value = (row as any)[header];
            if (value === null || value === undefined) return '';
            if (typeof value === 'boolean') return value ? 'true' : 'false';
            if (typeof value === 'string' && value.includes(',')) return `"${value}"`;
            return String(value);
          })
          .join(',')
      ),
    ];

    const csvContent = csvRows.join('\n');
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' }); // BOM para Excel
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `driver-matrix-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyAPIURL = () => {
    const params = new URLSearchParams();
    if (filters.origin_tag) params.set('origin_tag', filters.origin_tag);
    if (filters.only_pending) params.set('only_pending', 'true');
    if (filters.order !== 'week_start_desc') params.set('order', filters.order);
    if (limit !== 200) params.set('limit', limit.toString());
    if (offset !== 0) params.set('offset', offset.toString());

    const query = params.toString();
    const url = `${API_BASE_URL}/api/v1/ops/payments/driver-matrix${query ? `?${query}` : ''}`;
    navigator.clipboard.writeText(url);
    alert('URL copiada al portapapeles');
  };

  const copyDriverId = (driverId: string) => {
    navigator.clipboard.writeText(driverId);
  };

  const columns = [
    {
      key: 'driver',
      header: 'Driver',
      render: (row: DriverMatrixRow) => (
        <div>
          <div className="font-bold">{row.driver_name || '—'}</div>
          {row.driver_id && (
            <div 
              className="text-xs text-gray-500 cursor-pointer hover:text-blue-600"
              onClick={() => copyDriverId(row.driver_id!)}
              title="Click para copiar"
            >
              {row.driver_id.length > 20 ? `${row.driver_id.substring(0, 20)}...` : row.driver_id}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'week_start',
      header: 'Week Start',
      render: (row: DriverMatrixRow) =>
        row.week_start ? new Date(row.week_start).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'origin_tag',
      header: 'Origin',
      render: (row: DriverMatrixRow) =>
        row.origin_tag ? (
          <Badge variant={row.origin_tag === 'cabinet' ? 'info' : 'default'}>
            {row.origin_tag}
          </Badge>
        ) : (
          '—'
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
    {
      key: 'connected',
      header: 'Conectado',
      render: (row: DriverMatrixRow) => (
        <div>
          {row.connected_flag ? (
            <div>
              <span className="text-green-600">✓</span>
              {row.connected_date && (
                <div className="text-xs text-gray-500">
                  {new Date(row.connected_date).toLocaleDateString('es-ES')}
                </div>
              )}
            </div>
          ) : (
            <span className="text-gray-400">No</span>
          )}
        </div>
      ),
    },
    {
      key: 'scout',
      header: 'Scout',
      render: (row: DriverMatrixRow) => {
        if (row.scout_due_flag === null && row.scout_paid_flag === null && row.scout_amount === null) {
          return '—';
        }
        return (
          <div className="text-sm">
            {row.scout_due_flag && <div>Due: ✓</div>}
            {row.scout_paid_flag && <div>Paid: ✓</div>}
            {row.scout_amount !== null && (
              <div>S/ {Number(row.scout_amount).toFixed(2)}</div>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Driver Matrix</h1>
          <PaymentsLegend />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopyAPIURL}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 font-medium"
          >
            Copiar URL API
          </button>
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
          >
            Exportar CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Origin Tag</label>
            <select
              value={filters.origin_tag}
              onChange={(e) => handleFilterChange('origin_tag', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="cabinet">cabinet</option>
              <option value="fleet_migration">fleet_migration</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Only Pending</label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={filters.only_pending}
                onChange={(e) => handleFilterChange('only_pending', e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm">Solo pendientes</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Orden</label>
            <select
              value={filters.order}
              onChange={(e) => handleFilterChange('order', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="week_start_desc">Week Start (DESC)</option>
              <option value="week_start_asc">Week Start (ASC)</option>
              <option value="lead_date_desc">Lead Date (DESC)</option>
              <option value="lead_date_asc">Lead Date (ASC)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Buscar Driver</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="Nombre o ID"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>
        </div>

        <div className="mt-4">
          <button
            onClick={handleResetFilters}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium"
          >
            Limpiar Filtros
          </button>
        </div>
      </div>

      {/* Info total */}
      {meta && (
        <div className="mb-4 text-sm text-gray-600">
          Total: <span className="font-semibold">{meta.total}</span> drivers | 
          Mostrando: <span className="font-semibold">{meta.returned}</span> | 
          Página: <span className="font-semibold">{Math.floor(offset / limit) + 1}</span>
        </div>
      )}

      <DataTable
        data={data}
        columns={columns}
        loading={loading}
        emptyMessage="No hay drivers que coincidan con los filtros"
      />

      {/* Paginación */}
      {!loading && meta && data.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-700">Page size:</label>
              <select
                value={limit}
                onChange={(e) => {
                  const newLimit = parseInt(e.target.value);
                  setLimit(newLimit);
                  setOffset(0);
                  updateURL(filters, newLimit, 0);
                }}
                className="px-3 py-1 border border-gray-300 rounded-md"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="200">200</option>
              </select>
            </div>
          </div>
          <Pagination
            total={meta.total}
            limit={limit}
            offset={offset}
            onPageChange={(newOffset) => {
              setOffset(newOffset);
              updateURL(filters, limit, newOffset);
            }}
          />
        </div>
      )}
    </div>
  );
}

