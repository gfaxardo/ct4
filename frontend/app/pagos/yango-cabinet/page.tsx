/**
 * Yango - Reconciliación
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Cuál es el estado de reconciliación de pagos Yango?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getYangoReconciliationSummary,
  getYangoReconciliationItems,
  ApiError,
} from '@/lib/api';
import type {
  YangoReconciliationSummaryResponse,
  YangoReconciliationItemsResponse,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function YangoCabinetPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<YangoReconciliationSummaryResponse | null>(null);
  const [items, setItems] = useState<YangoReconciliationItemsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    week_start: '',
    milestone_value: '',
    mode: 'real',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, itemsData] = await Promise.all([
          getYangoReconciliationSummary({
            week_start: filters.week_start || undefined,
            milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
            mode: filters.mode as 'real' | 'assumed',
            limit: 100,
          }),
          getYangoReconciliationItems({
            week_start: filters.week_start || undefined,
            milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
            limit,
            offset,
          }),
        ]);

        setSummary(summaryData);
        setItems(itemsData);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar reconciliación');
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
  }, [filters, offset, limit]);

  const filterFields = [
    {
      name: 'week_start',
      label: 'Semana (Lunes)',
      type: 'date' as const,
    },
    {
      name: 'milestone_value',
      label: 'Milestone',
      type: 'select' as const,
      options: [
        { value: '1', label: '1' },
        { value: '5', label: '5' },
        { value: '25', label: '25' },
      ],
    },
    {
      name: 'mode',
      label: 'Modo',
      type: 'select' as const,
      options: [
        { value: 'real', label: 'Real' },
        { value: 'assumed', label: 'Assumed' },
      ],
    },
  ];

  type SummaryRow = YangoReconciliationSummaryResponse['rows'][0];
  type ItemRow = YangoReconciliationItemsResponse['rows'][0];

  const summaryColumns = [
    {
      key: 'pay_week_start_monday',
      header: 'Semana',
      render: (row: SummaryRow) =>
        row.pay_week_start_monday ? new Date(row.pay_week_start_monday).toLocaleDateString('es-ES') : '—',
    },
    { key: 'milestone_value', header: 'Milestone' },
    {
      key: 'amount_expected_sum',
      header: 'Esperado',
      render: (row: SummaryRow) => row.amount_expected_sum?.toFixed(2) || '—',
    },
    {
      key: 'amount_paid_total_visible',
      header: 'Pagado Visible',
      render: (row: SummaryRow) => row.amount_paid_total_visible?.toFixed(2) || '—',
    },
    {
      key: 'amount_pending_active_sum',
      header: 'Pendiente Activo',
      render: (row: SummaryRow) => row.amount_pending_active_sum?.toFixed(2) || '—',
    },
    {
      key: 'amount_diff',
      header: 'Diferencia',
      render: (row: SummaryRow) => (
        <span className={row.amount_diff && row.amount_diff < 0 ? 'text-red-600' : ''}>
          {row.amount_diff?.toFixed(2) || '—'}
        </span>
      ),
    },
    { key: 'count_expected', header: 'Cant. Esperada' },
    { key: 'count_paid', header: 'Cant. Pagada' },
    { key: 'count_pending_active', header: 'Cant. Pendiente' },
  ];

  const itemsColumns = [
    {
      key: 'driver_id',
      header: 'Driver ID',
      render: (row: ItemRow) =>
        row.driver_id ? (
          <button
            onClick={() => router.push(`/pagos/yango-cabinet/driver/${row.driver_id}`)}
            className="text-blue-600 hover:text-blue-800 underline"
          >
            {row.driver_id}
          </button>
        ) : (
          '—'
        ),
    },
    { key: 'person_key', header: 'Person Key' },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: ItemRow) =>
        row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'pay_week_start_monday',
      header: 'Semana',
      render: (row: ItemRow) =>
        row.pay_week_start_monday ? new Date(row.pay_week_start_monday).toLocaleDateString('es-ES') : '—',
    },
    { key: 'milestone_value', header: 'Milestone' },
    {
      key: 'expected_amount',
      header: 'Esperado',
      render: (row: ItemRow) =>
        row.expected_amount ? `${row.expected_amount} ${row.currency || ''}` : '—',
    },
    {
      key: 'due_date',
      header: 'Due Date',
      render: (row: ItemRow) =>
        row.due_date ? new Date(row.due_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'window_status',
      header: 'Estado Ventana',
      render: (row: ItemRow) =>
        row.window_status ? (
          <Badge variant={row.window_status === 'active' ? 'success' : 'error'}>
            {row.window_status}
          </Badge>
        ) : (
          '—'
        ),
    },
    {
      key: 'paid_status',
      header: 'Estado Pago',
      render: (row: ItemRow) =>
        row.paid_status ? (
          <Badge
            variant={
              row.paid_status.includes('paid') ? 'success' : row.paid_status.includes('pending') ? 'warning' : 'error'
            }
          >
            {row.paid_status}
          </Badge>
        ) : (
          '—'
        ),
    },
    {
      key: 'paid_date',
      header: 'Fecha Pago',
      render: (row: ItemRow) =>
        row.paid_date ? new Date(row.paid_date).toLocaleDateString('es-ES') : '—',
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Yango - Reconciliación</h1>

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
          setFilters({ week_start: '', milestone_value: '', mode: 'real' });
          setOffset(0);
        }}
      />

      {/* Summary Table */}
      {summary && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Resumen por Semana y Milestone</h2>
          <DataTable
            data={summary.rows}
            columns={summaryColumns}
            loading={loading}
            emptyMessage="No hay datos de resumen para los filtros seleccionados"
          />
        </div>
      )}

      {/* Items Table */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Items Detallados</h2>
        <DataTable
          data={items?.rows || []}
          columns={itemsColumns}
          loading={loading}
          emptyMessage="No hay items que coincidan con los filtros"
        />
      </div>

      {!loading && items && items.rows.length > 0 && (
        <Pagination
          total={items.total || items.count}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}
