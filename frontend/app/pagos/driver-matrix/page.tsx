/**
 * Driver Matrix - Matriz de drivers con milestones M1/M5/M25
 * 
 * Objetivo: "¿Qué drivers tienen qué milestones y cuál es su estado de pago?"
 */

'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getOpsDriverMatrix, ApiError } from '@/lib/api';
import type { DriverMatrixRow, OpsDriverMatrixResponse } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Badge from '@/components/Badge';
import Pagination from '@/components/Pagination';
import CompactMilestoneCell from '@/components/payments/CompactMilestoneCell';
import MilestoneCell from '@/components/payments/MilestoneCell';
import PaymentsLegend from '@/components/payments/PaymentsLegend';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

function DriverMatrixPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [data, setData] = useState<DriverMatrixRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<OpsDriverMatrixResponse['meta'] | null>(null);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  
  // Helper para validar origin_tag: acepta 'cabinet', 'fleet_migration', 'unknown' o 'All' (vacío)
  const getValidOriginTag = (value: string | null): string => {
    if (value === 'cabinet' || value === 'fleet_migration' || value === 'unknown') return value;
    if (value === 'All' || value === '') return '';
    return '';
  };

  // Helper para validar funnel_status
  const getValidFunnelStatus = (value: string | null): string => {
    const validStatuses = ['registered_incomplete', 'registered_complete', 'connected_no_trips', 'reached_m1', 'reached_m5', 'reached_m25'];
    if (value && validStatuses.includes(value)) return value;
    return '';
  };

  // Filtros desde URL o estado inicial
  const [filters, setFilters] = useState(() => {
    const originTagParam = searchParams.get('origin_tag');
    const funnelStatusParam = searchParams.get('funnel_status');
    const orderParam = searchParams.get('order') as
      | 'week_start_desc'
      | 'week_start_asc'
      | 'lead_date_desc'
      | 'lead_date_asc'
      | null;
    return {
      origin_tag: getValidOriginTag(originTagParam),
      funnel_status: getValidFunnelStatus(funnelStatusParam),
      only_pending: searchParams.get('only_pending') === 'true',
      order: orderParam || 'week_start_desc',
      search: searchParams.get('search') || '',
    };
  });
  
  // Tab activo (Tabla o KPIs)
  const [activeTab, setActiveTab] = useState(() => {
    const tabParam = searchParams.get('tab');
    return tabParam === 'kpis' ? 'kpis' : 'tabla';
  });
  
  const [limit, setLimit] = useState(() => parseInt(searchParams.get('limit') || '200'));
  const [offset, setOffset] = useState(() => parseInt(searchParams.get('offset') || '0'));

  // Debounce para search
  const [searchDebounced, setSearchDebounced] = useState(filters.search);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(filters.search);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  // Actualizar URL cuando cambian filtros
  const updateURL = useCallback((newFilters: typeof filters, newLimit: number, newOffset: number, newTab?: string) => {
    const params = new URLSearchParams();
    if (newFilters.origin_tag) params.set('origin_tag', newFilters.origin_tag);
    if (newFilters.funnel_status) params.set('funnel_status', newFilters.funnel_status);
    if (newFilters.only_pending) params.set('only_pending', 'true');
    if (newFilters.order !== 'week_start_desc') params.set('order', newFilters.order);
    if (newFilters.search) params.set('search', newFilters.search);
    if (newLimit !== 200) params.set('limit', newLimit.toString());
    if (newOffset !== 0) params.set('offset', newOffset.toString());
    if (newTab && newTab !== 'tabla') params.set('tab', newTab);
    
    const query = params.toString();
    router.push(`/pagos/driver-matrix${query ? `?${query}` : ''}`, { scroll: false });
  }, [router]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Solo enviar filtros al backend si tienen valor (no enviar filtros vacíos que puedan ser restrictivos)
        const backendFilters: any = {
          order: filters.order,
          limit,
          offset,
        };
        
        // Solo agregar filtros opcionales si tienen valor
        if (filters.origin_tag) {
          backendFilters.origin_tag = filters.origin_tag;
        }
        if (filters.funnel_status) {
          backendFilters.funnel_status = filters.funnel_status;
        }
        if (filters.only_pending) {
          backendFilters.only_pending = filters.only_pending;
        }

        const response = await getOpsDriverMatrix(backendFilters);

        // Aplicar filtro de búsqueda client-side después de recibir los datos
        let filteredData = response.data;
        if (searchDebounced) {
          const searchLower = searchDebounced.toLowerCase();
          filteredData = response.data.filter((row) => {
            return (
              row.driver_name?.toLowerCase().includes(searchLower) ||
              row.driver_id?.toLowerCase().includes(searchLower) ||
              row.person_key?.toLowerCase().includes(searchLower)
            );
          });
        }

        setData(filteredData);
        setMeta(response.meta);
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
  }, [filters.origin_tag, filters.funnel_status, filters.only_pending, filters.order, limit, offset, searchDebounced]);

  const handleFilterChange = (key: keyof typeof filters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    setOffset(0); // Reset offset cuando cambian filtros
    updateURL(newFilters, limit, 0, activeTab);
  };
  
  const handleTabChange = (tab: 'tabla' | 'kpis') => {
    setActiveTab(tab);
    updateURL(filters, limit, offset, tab);
  };

  const handleResetFilters = () => {
    const newFilters = {
      origin_tag: '',
      funnel_status: '',
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
      // Columnas operativas de sanity check
      'connection_within_14d_flag',
      'connection_date_within_14d',
      'trips_completed_14d_from_lead',
      'first_trip_date_within_14d',
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

  // Generar key único para cada fila (driver_id + week_start o person_key + week_start)
  const getRowKey = (row: DriverMatrixRow): string => {
    const id = row.driver_id || row.person_key || 'unknown';
    const week = row.week_start || 'no-week';
    return `${id}-${week}`;
  };

  // Toggle expandir fila
  const toggleRowExpand = (row: DriverMatrixRow) => {
    const key = getRowKey(row);
    setExpandedRows((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Componente para columna Driver compacta
  const DriverCell = ({ row }: { row: DriverMatrixRow }) => {
    const [showTooltip, setShowTooltip] = useState(false);
    const [showInconsistencyTooltip, setShowInconsistencyTooltip] = useState(false);
    const hasInconsistency = row.m5_without_m1_flag || row.m25_without_m5_flag;
    
    return (
      <div className="relative">
        <div className="flex items-center gap-1">
          <div className="font-semibold text-sm whitespace-nowrap">{row.driver_name || '—'}</div>
          {row.driver_id && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                copyDriverId(row.driver_id!);
              }}
              className="ml-1 text-xs text-gray-400 hover:text-blue-600"
              title="Copiar ID"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              📋
            </button>
          )}
          {hasInconsistency && (
            <div
              className="relative"
              onMouseEnter={() => setShowInconsistencyTooltip(true)}
              onMouseLeave={() => setShowInconsistencyTooltip(false)}
            >
              <Badge variant="warning" className="text-xs py-0 px-1">
                ⚠ Inconsistencia
              </Badge>
              {showInconsistencyTooltip && (
                <div className="absolute z-50 bottom-full left-0 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-pre-line max-w-xs">
                  {row.milestone_inconsistency_notes || 
                   (row.m5_without_m1_flag ? 'M5 sin M1' : '') + 
                   (row.m25_without_m5_flag ? (row.m5_without_m1_flag ? ', M25 sin M5' : 'M25 sin M5') : '')}
                  {'\n\n'}
                  Claim/status existe para milestone superior pero falta evidencia del milestone anterior en claims; revisar fuente.
                  <div className="absolute top-full left-4 -mt-1">
                    <div className="border-4 border-transparent border-t-gray-900"></div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
        {showTooltip && row.driver_id && (
          <div className="absolute z-50 bottom-full left-0 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-pre max-w-xs">
            {row.driver_id}
            <div className="absolute top-full left-4 -mt-1">
              <div className="border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const columns = [
    {
      key: 'expand',
      header: '',
      className: 'py-2 w-10',
      render: (row: DriverMatrixRow) => {
        const key = getRowKey(row);
        const isExpanded = expandedRows[key] || false;
        return (
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleRowExpand(row);
            }}
            aria-label={isExpanded ? 'Contraer detalles' : 'Expandir detalles'}
            aria-expanded={isExpanded}
            className="p-1 hover:bg-gray-100 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <span
              className={`inline-block text-gray-600 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
            >
              ▶
            </span>
          </button>
        );
      },
    },
    {
      key: 'driver',
      header: 'Driver',
      className: 'py-2',
      render: (row: DriverMatrixRow) => <DriverCell row={row} />,
    },
    {
      key: 'week_start',
      header: 'Week Start',
      className: 'py-2',
      render: (row: DriverMatrixRow) =>
        row.week_start ? new Date(row.week_start).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'origin_tag',
      header: 'Origin',
      className: 'py-2',
      render: (row: DriverMatrixRow) =>
        row.origin_tag ? (
          <Badge variant={row.origin_tag === 'cabinet' ? 'info' : row.origin_tag === 'unknown' ? 'warning' : 'default'}>
            {row.origin_tag}
          </Badge>
        ) : (
          <Badge variant="warning">unknown</Badge>
        ),
    },
    {
      key: 'funnel_status',
      header: 'Estado',
      className: 'py-2',
      render: (row: DriverMatrixRow) => {
        if (!row.funnel_status) return '—';
        const statusLabels: Record<string, string> = {
          'registered_incomplete': 'Reg. Incompleto',
          'registered_complete': 'Reg. Completo',
          'connected_no_trips': 'Conectado',
          'reached_m1': 'M1',
          'reached_m5': 'M5',
          'reached_m25': 'M25',
        };
        const statusColors: Record<string, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
          'registered_incomplete': 'warning',
          'registered_complete': 'info',
          'connected_no_trips': 'default',
          'reached_m1': 'success',
          'reached_m5': 'success',
          'reached_m25': 'success',
        };
        return (
          <Badge variant={statusColors[row.funnel_status] || 'default'}>
            {statusLabels[row.funnel_status] || row.funnel_status}
          </Badge>
        );
      },
    },
    {
      key: 'm1',
      header: 'M1',
      className: 'py-2',
      render: (row: DriverMatrixRow) => (
        <CompactMilestoneCell
          achieved_flag={row.m1_achieved_flag}
          achieved_date={row.m1_achieved_date}
          expected_amount_yango={row.m1_expected_amount_yango}
          yango_payment_status={row.m1_yango_payment_status}
          window_status={row.m1_window_status}
          overdue_days={row.m1_overdue_days}
          label="M1"
        />
      ),
    },
    {
      key: 'm5',
      header: 'M5',
      className: 'py-2',
      render: (row: DriverMatrixRow) => (
        <CompactMilestoneCell
          achieved_flag={row.m5_achieved_flag}
          achieved_date={row.m5_achieved_date}
          expected_amount_yango={row.m5_expected_amount_yango}
          yango_payment_status={row.m5_yango_payment_status}
          window_status={row.m5_window_status}
          overdue_days={row.m5_overdue_days}
          label="M5"
        />
      ),
    },
    {
      key: 'm25',
      header: 'M25',
      className: 'py-2',
      render: (row: DriverMatrixRow) => (
        <CompactMilestoneCell
          achieved_flag={row.m25_achieved_flag}
          achieved_date={row.m25_achieved_date}
          expected_amount_yango={row.m25_expected_amount_yango}
          yango_payment_status={row.m25_yango_payment_status}
          window_status={row.m25_window_status}
          overdue_days={row.m25_overdue_days}
          label="M25"
        />
      ),
    },
    {
      key: 'connected',
      header: 'Conectado',
      className: 'py-2',
      render: (row: DriverMatrixRow) => (
        <div className="text-sm">
          {row.connected_flag ? (
            <span className="text-green-600">✓</span>
          ) : (
            <span className="text-gray-400">No</span>
          )}
        </div>
      ),
    },
    {
      key: 'scout',
      header: 'Scout',
      className: 'py-2',
      render: (row: DriverMatrixRow) => {
        if (row.scout_due_flag === null && row.scout_paid_flag === null && row.scout_amount === null) {
          return <span className="text-gray-400">—</span>;
        }
        return (
          <div className="text-xs whitespace-nowrap">
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
              <option value="unknown">unknown</option>
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

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => handleTabChange('tabla')}
              className={`px-6 py-3 text-sm font-medium ${
                activeTab === 'tabla'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Tabla
            </button>
            <button
              onClick={() => handleTabChange('kpis')}
              className={`px-6 py-3 text-sm font-medium ${
                activeTab === 'kpis'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              KPIs
            </button>
          </nav>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            <button
              onClick={() => handleTabChange('tabla')}
              className={`px-6 py-3 text-sm font-medium ${
                activeTab === 'tabla'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Tabla
            </button>
            <button
              onClick={() => handleTabChange('kpis')}
              className={`px-6 py-3 text-sm font-medium ${
                activeTab === 'kpis'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              KPIs
            </button>
          </nav>
        </div>
      </div>

      {/* Contenido según tab activo */}
      {activeTab === 'tabla' ? (
        <>
          {/* Info total */}
          {meta && (
            <div className="mb-4 text-sm text-gray-600">
              Total: <span className="font-semibold">{meta.total}</span> drivers | 
              Mostrando: <span className="font-semibold">{meta.returned}</span> | 
              Página: <span className="font-semibold">{Math.floor(offset / limit) + 1}</span>
            </div>
          )}

          {/* Tabla personalizada con soporte para filas expandidas */}
          {loading ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">Cargando...</p>
        </div>
      ) : data.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No hay drivers que coincidan con los filtros</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {columns.map((col, idx) => (
                    <th
                      key={idx}
                      className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${col.className || ''}`}
                    >
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.map((row, rowIdx) => {
                  const rowKey = getRowKey(row);
                  const isExpanded = expandedRows[rowKey] || false;
                  return (
                    <>
                      <tr key={rowIdx} className="hover:bg-gray-50">
                        {columns.map((col, colIdx) => (
                          <td
                            key={colIdx}
                            className={`px-6 py-2 whitespace-nowrap text-sm text-gray-900 ${col.className || ''}`}
                          >
                            {col.render ? col.render(row) : '—'}
                          </td>
                        ))}
                      </tr>
                      {isExpanded && (
                        <tr key={`${rowIdx}-expanded`} className="bg-gray-50">
                          <td colSpan={columns.length} className="px-6 py-4">
                            <div className="grid grid-cols-3 gap-4">
                              <div>
                                <h4 className="text-sm font-semibold text-gray-700 mb-2">M1</h4>
                                <MilestoneCell
                                  achieved_flag={row.m1_achieved_flag}
                                  achieved_date={row.m1_achieved_date}
                                  expected_amount_yango={row.m1_expected_amount_yango}
                                  yango_payment_status={row.m1_yango_payment_status}
                                  window_status={row.m1_window_status}
                                  overdue_days={row.m1_overdue_days}
                                />
                              </div>
                              <div>
                                <h4 className="text-sm font-semibold text-gray-700 mb-2">M5</h4>
                                <MilestoneCell
                                  achieved_flag={row.m5_achieved_flag}
                                  achieved_date={row.m5_achieved_date}
                                  expected_amount_yango={row.m5_expected_amount_yango}
                                  yango_payment_status={row.m5_yango_payment_status}
                                  window_status={row.m5_window_status}
                                  overdue_days={row.m5_overdue_days}
                                />
                              </div>
                              <div>
                                <h4 className="text-sm font-semibold text-gray-700 mb-2">M25</h4>
                                <MilestoneCell
                                  achieved_flag={row.m25_achieved_flag}
                                  achieved_date={row.m25_achieved_date}
                                  expected_amount_yango={row.m25_expected_amount_yango}
                                  yango_payment_status={row.m25_yango_payment_status}
                                  window_status={row.m25_window_status}
                                  overdue_days={row.m25_overdue_days}
                                />
                              </div>
                            </div>
                            {/* Información adicional del driver */}
                            <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="font-medium text-gray-700">Driver ID:</span>{' '}
                                <span className="text-gray-600">{row.driver_id || '—'}</span>
                              </div>
                              <div>
                                <span className="font-medium text-gray-700">Person Key:</span>{' '}
                                <span className="text-gray-600">{row.person_key || '—'}</span>
                              </div>
                              {row.lead_date && (
                                <div>
                                  <span className="font-medium text-gray-700">Lead Date:</span>{' '}
                                  <span className="text-gray-600">
                                    {new Date(row.lead_date).toLocaleDateString('es-ES')}
                                  </span>
                                </div>
                              )}
                              {row.connected_date && (
                                <div>
                                  <span className="font-medium text-gray-700">Connected Date:</span>{' '}
                                  <span className="text-gray-600">
                                    {new Date(row.connected_date).toLocaleDateString('es-ES')}
                                  </span>
                                </div>
                              )}
                            </div>
                            {/* Información operativa de sanity check (ventana de 14 días) */}
                            {(row.trips_completed_14d_from_lead !== null || row.connection_within_14d_flag !== null) && (
                              <div className="mt-4 pt-4 border-t border-gray-200">
                                <h5 className="text-sm font-semibold text-gray-700 mb-2">Métricas Operativas (14 días)</h5>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                  {row.connection_within_14d_flag !== null && (
                                    <div>
                                      <span className="font-medium text-gray-700">Conexión en ventana:</span>{' '}
                                      <span className={row.connection_within_14d_flag ? 'text-green-600' : 'text-gray-600'}>
                                        {row.connection_within_14d_flag ? '✓ Sí' : '✗ No'}
                                      </span>
                                    </div>
                                  )}
                                  {row.connection_date_within_14d && (
                                    <div>
                                      <span className="font-medium text-gray-700">Fecha conexión (14d):</span>{' '}
                                      <span className="text-gray-600">
                                        {new Date(row.connection_date_within_14d).toLocaleDateString('es-ES')}
                                      </span>
                                    </div>
                                  )}
                                  {row.trips_completed_14d_from_lead !== null && (
                                    <div>
                                      <span className="font-medium text-gray-700">Viajes en 14 días:</span>{' '}
                                      <span className="text-gray-600 font-semibold">
                                        {row.trips_completed_14d_from_lead}
                                      </span>
                                    </div>
                                  )}
                                  {row.first_trip_date_within_14d && (
                                    <div>
                                      <span className="font-medium text-gray-700">Primer viaje (14d):</span>{' '}
                                      <span className="text-gray-600">
                                        {new Date(row.first_trip_date_within_14d).toLocaleDateString('es-ES')}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

          {/* Paginación - Solo en tab Tabla */}
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
                      updateURL(filters, newLimit, 0, activeTab);
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
                  updateURL(filters, limit, newOffset, activeTab);
                }}
              />
            </div>
          )}
        </>
      ) : (
        /* Tab KPIs */
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">KPIs de Conversión</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-blue-800 mb-2">Funnel (C1)</h3>
              <div className="space-y-2 text-sm">
                <div>Reg. Incompleto: <span className="font-semibold">{data.filter(r => r.funnel_status === 'registered_incomplete').length}</span></div>
                <div>Reg. Completo: <span className="font-semibold">{data.filter(r => r.funnel_status === 'registered_complete').length}</span></div>
                <div>Conectado: <span className="font-semibold">{data.filter(r => r.funnel_status === 'connected_no_trips').length}</span></div>
                <div>M1: <span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m1').length}</span></div>
                <div>M5: <span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m5').length}</span></div>
                <div>M25: <span className="font-semibold">{data.filter(r => r.funnel_status === 'reached_m25').length}</span></div>
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-green-800 mb-2">Claims (C3/C4)</h3>
              <div className="space-y-2 text-sm">
                <div>Expected Yango: <span className="font-semibold">${((data.reduce((sum, r) => sum + (r.m1_expected_amount_yango || 0) + (r.m5_expected_amount_yango || 0) + (r.m25_expected_amount_yango || 0), 0)) / 100).toFixed(2)}</span></div>
                <div>Paid: <span className="font-semibold">${((data.filter(r => r.m1_yango_payment_status === 'PAID' || r.m5_yango_payment_status === 'PAID' || r.m25_yango_payment_status === 'PAID').reduce((sum, r) => sum + (r.m1_expected_amount_yango || 0) + (r.m5_expected_amount_yango || 0) + (r.m25_expected_amount_yango || 0), 0)) / 100).toFixed(2)}</span></div>
                <div>Receivable: <span className="font-semibold">${((data.filter(r => r.m1_yango_payment_status && r.m1_yango_payment_status !== 'PAID' || r.m5_yango_payment_status && r.m5_yango_payment_status !== 'PAID' || r.m25_yango_payment_status && r.m25_yango_payment_status !== 'PAID').reduce((sum, r) => sum + (r.m1_expected_amount_yango || 0) + (r.m5_expected_amount_yango || 0) + (r.m25_expected_amount_yango || 0), 0)) / 100).toFixed(2)}</span></div>
              </div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h3 className="text-sm font-medium text-purple-800 mb-2">Achieved sin Claim</h3>
              <div className="space-y-2 text-sm">
                <div>M1 sin claim: <span className="font-semibold">{data.filter(r => r.m1_achieved_flag && !r.m1_yango_payment_status).length}</span></div>
                <div>M5 sin claim: <span className="font-semibold">{data.filter(r => r.m5_achieved_flag && !r.m5_yango_payment_status).length}</span></div>
                <div>M25 sin claim: <span className="font-semibold">{data.filter(r => r.m25_achieved_flag && !r.m25_yango_payment_status).length}</span></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DriverMatrixPage() {
  return (
    <Suspense fallback={<div className="px-4 py-6">Cargando...</div>}>
      <DriverMatrixPageContent />
    </Suspense>
  );
}

