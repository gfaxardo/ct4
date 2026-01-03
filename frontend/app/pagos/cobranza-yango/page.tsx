/**
 * Yango - Cobranza
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué items de cobranza Yango están pendientes de pago?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getYangoSummary,
  getYangoReceivableItems,
  ApiError,
} from '@/lib/api';
import type {
  YangoSummaryResponse,
  YangoReceivableItemsResponse,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';
import PaymentsLegend from '@/components/payments/PaymentsLegend';

export default function CobranzaYangoPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<YangoSummaryResponse | null>(null);
  const [items, setItems] = useState<YangoReceivableItemsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    week_start_monday: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, itemsData] = await Promise.all([
          getYangoSummary({
            week_start: filters.week_start_monday ? new Date(filters.week_start_monday).toISOString().split('T')[0] : undefined,
          }),
          getYangoReceivableItems({
            week_start_monday: filters.week_start_monday || undefined,
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
            setError('Error al cargar cobranza Yango');
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
      name: 'week_start_monday',
      label: 'Semana (Lunes)',
      type: 'date' as const,
    },
  ];

  type ReceivableItem = YangoReceivableItemsResponse['items'][0];

  const itemsColumns = [
    {
      key: 'driver_id',
      header: 'Driver ID',
      render: (row: ReceivableItem) =>
        row.driver_id ? (
          <button
            onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
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
      key: 'pay_week_start_monday',
      header: 'Semana',
      render: (row: ReceivableItem) =>
        row.pay_week_start_monday ? new Date(row.pay_week_start_monday).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'payable_date',
      header: 'Payable Date',
      render: (row: ReceivableItem) =>
        row.payable_date ? new Date(row.payable_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'achieved_date',
      header: 'Achieved Date',
      render: (row: ReceivableItem) =>
        row.achieved_date ? new Date(row.achieved_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: ReceivableItem) =>
        row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—',
    },
    { key: 'lead_origin', header: 'Origen' },
    { key: 'milestone_value', header: 'Milestone' },
    {
      key: 'amount',
      header: 'Monto',
      render: (row: ReceivableItem) =>
        `${row.amount} ${row.currency || ''}`,
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Yango - Cobranza</h1>
        <PaymentsLegend />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <StatCard
            title="Monto Receivable"
            value={`${Number(summary.totals.receivable_amount).toFixed(2)}`}
          />
          <StatCard
            title="Items Receivable"
            value={summary.totals.receivable_items}
          />
          <StatCard
            title="Drivers Receivable"
            value={summary.totals.receivable_drivers}
          />
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => setFilters(values as typeof filters)}
        onReset={() => {
          setFilters({ week_start_monday: '' });
          setOffset(0);
        }}
      />

      <DataTable
        data={items?.items || []}
        columns={itemsColumns}
        loading={loading}
        emptyMessage="No hay items de cobranza que coincidan con los filtros"
      />

      {!loading && items && items.items.length > 0 && (
        <Pagination
          total={items.total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}

