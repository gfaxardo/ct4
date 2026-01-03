/**
 * Liquidaciones Scouts
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué items de liquidación scouts están abiertos y listos para pagar?"
 */

'use client';

import { useEffect, useState } from 'react';
import { getScoutSummary, getScoutOpenItems, ApiError } from '@/lib/api';
import type { ScoutSummaryResponse, ScoutOpenItemsResponse } from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function LiquidacionesPage() {
  const [summary, setSummary] = useState<ScoutSummaryResponse | null>(null);
  const [openItems, setOpenItems] = useState<ScoutOpenItemsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    week_start_monday: '',
    scout_id: '',
    confidence: 'policy',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, itemsData] = await Promise.all([
          getScoutSummary({
            week_start: filters.week_start_monday ? new Date(filters.week_start_monday).toISOString().split('T')[0] : undefined,
            scout_id: filters.scout_id ? parseInt(filters.scout_id) : undefined,
          }),
          getScoutOpenItems({
            week_start_monday: filters.week_start_monday || undefined,
            scout_id: filters.scout_id ? parseInt(filters.scout_id) : undefined,
            confidence: filters.confidence,
            limit,
            offset,
          }),
        ]);

        setSummary(summaryData);
        setOpenItems(itemsData);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar liquidaciones');
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
    {
      name: 'scout_id',
      label: 'Scout ID',
      type: 'number' as const,
    },
    {
      name: 'confidence',
      label: 'Confianza',
      type: 'select' as const,
      options: [
        { value: 'policy', label: 'Policy' },
        { value: 'high', label: 'High' },
        { value: 'medium', label: 'Medium' },
        { value: 'unknown', label: 'Unknown' },
      ],
    },
  ];

  type OpenItem = ScoutOpenItemsResponse['items'][0];

  const itemsColumns = [
    { key: 'payment_item_key', header: 'Item Key' },
    { key: 'person_key', header: 'Person Key' },
    { key: 'lead_origin', header: 'Origen' },
    { key: 'scout_id', header: 'Scout ID' },
    { key: 'acquisition_scout_name', header: 'Scout Atribuido' },
    {
      key: 'attribution_confidence',
      header: 'Confianza',
      render: (row: OpenItem) => (
        <Badge variant={row.attribution_confidence === 'high' ? 'success' : 'warning'}>
          {row.attribution_confidence || '—'}
        </Badge>
      ),
    },
    { key: 'milestone_value', header: 'Milestone' },
    {
      key: 'payable_date',
      header: 'Payable Date',
      render: (row: OpenItem) =>
        row.payable_date ? new Date(row.payable_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'amount',
      header: 'Monto',
      render: (row: OpenItem) =>
        `${row.amount} ${row.currency || ''}`,
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Liquidaciones Scouts</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <StatCard
            title="Monto Pagable"
            value={`${Number(summary.totals.payable_amount).toFixed(2)}`}
          />
          <StatCard
            title="Items Pagables"
            value={summary.totals.payable_items}
          />
          <StatCard
            title="Drivers Pagables"
            value={summary.totals.payable_drivers}
          />
          <StatCard
            title="Scouts Pagables"
            value={summary.totals.payable_scouts}
          />
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => setFilters(values as typeof filters)}
        onReset={() => {
          setFilters({ week_start_monday: '', scout_id: '', confidence: 'policy' });
          setOffset(0);
        }}
      />

      <DataTable
        data={openItems?.items || []}
        columns={itemsColumns}
        loading={loading}
        emptyMessage="No hay items abiertos que coincidan con los filtros"
      />

      {!loading && openItems && openItems.items.length > 0 && (
        <Pagination
          total={openItems.total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}
