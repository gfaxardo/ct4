/**
 * Pagos - Elegibilidad
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Objetivo: "¿Qué pagos son elegibles y cumplen condiciones?"
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPaymentEligibility, ApiError } from '@/lib/api';
import type { PaymentEligibilityResponse } from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function PagosPage() {
  const [eligibility, setEligibility] = useState<PaymentEligibilityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    origin_tag: '',
    rule_scope: '',
    is_payable: '',
    scout_id: '',
    driver_id: '',
    payable_from: '',
    payable_to: '',
    order_by: 'payable_date',
    order_dir: 'asc',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    async function loadEligibility() {
      try {
        setLoading(true);
        setError(null);

        const data = await getPaymentEligibility({
          origin_tag: filters.origin_tag || undefined,
          rule_scope: filters.rule_scope || undefined,
          is_payable: filters.is_payable ? filters.is_payable === 'true' : undefined,
          scout_id: filters.scout_id ? parseInt(filters.scout_id) : undefined,
          driver_id: filters.driver_id || undefined,
          payable_from: filters.payable_from || undefined,
          payable_to: filters.payable_to || undefined,
          order_by: filters.order_by as 'payable_date' | 'lead_date' | 'amount',
          order_dir: filters.order_dir as 'asc' | 'desc',
          limit,
          offset,
        });

        setEligibility(data);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar elegibilidad');
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

    loadEligibility();
  }, [filters, offset, limit]);

  const filterFields = [
    {
      name: 'origin_tag',
      label: 'Origen',
      type: 'select' as const,
      options: [
        { value: 'cabinet', label: 'Cabinet' },
        { value: 'fleet_migration', label: 'Fleet Migration' },
      ],
    },
    {
      name: 'rule_scope',
      label: 'Scope',
      type: 'select' as const,
      options: [
        { value: 'scout', label: 'Scout' },
        { value: 'partner', label: 'Partner' },
      ],
    },
    {
      name: 'is_payable',
      label: 'Es Pagable',
      type: 'select' as const,
      options: [
        { value: 'true', label: 'Sí' },
        { value: 'false', label: 'No' },
      ],
    },
    {
      name: 'scout_id',
      label: 'Scout ID',
      type: 'number' as const,
    },
    {
      name: 'driver_id',
      label: 'Driver ID',
      type: 'text' as const,
    },
    {
      name: 'payable_from',
      label: 'Payable Desde',
      type: 'date' as const,
    },
    {
      name: 'payable_to',
      label: 'Payable Hasta',
      type: 'date' as const,
    },
    {
      name: 'order_by',
      label: 'Ordenar Por',
      type: 'select' as const,
      options: [
        { value: 'payable_date', label: 'Payable Date' },
        { value: 'lead_date', label: 'Lead Date' },
        { value: 'amount', label: 'Amount' },
      ],
    },
    {
      name: 'order_dir',
      label: 'Dirección',
      type: 'select' as const,
      options: [
        { value: 'asc', label: 'Asc' },
        { value: 'desc', label: 'Desc' },
      ],
    },
  ];

  type EligibilityRow = PaymentEligibilityResponse['rows'][0];

  const columns = [
    { key: 'person_key', header: 'Person Key' },
    { key: 'origin_tag', header: 'Origen' },
    { key: 'scout_id', header: 'Scout ID' },
    { key: 'driver_id', header: 'Driver ID' },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: EligibilityRow) =>
        row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—',
    },
    { key: 'rule_scope', header: 'Scope' },
    { key: 'milestone_trips', header: 'Trips' },
    {
      key: 'amount',
      header: 'Monto',
      render: (row: EligibilityRow) =>
        row.amount ? `${row.amount} ${row.currency || ''}` : '—',
    },
    {
      key: 'is_payable',
      header: 'Es Pagable',
      render: (row: EligibilityRow) => (
        <Badge variant={row.is_payable ? 'success' : 'error'}>
          {row.is_payable ? 'Sí' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'payable_date',
      header: 'Payable Date',
      render: (row: EligibilityRow) =>
        row.payable_date ? new Date(row.payable_date).toLocaleDateString('es-ES') : '—',
    },
  ];

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Pagos</h1>

      {/* Navegación a subrutas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <Link
          href="/pagos/yango-cabinet"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">Reconciliación Yango</h2>
          <p className="text-sm text-gray-600">
            Reconciliación de pagos Yango por semana y milestone
          </p>
        </Link>

        <Link
          href="/pagos/cobranza-yango"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">Cobranza Yango</h2>
          <p className="text-sm text-gray-600">
            Claims exigibles y estado de cobranza
          </p>
        </Link>

        <Link
          href="/pagos/yango-cabinet-claims"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">Claims Cabinet</h2>
          <p className="text-sm text-gray-600">
            Claims exigibles de Yango Cabinet con detalles
          </p>
        </Link>

        <Link
          href="/pagos/resumen-conductor"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">Resumen por Conductor</h2>
          <p className="text-sm text-gray-600">
            Resumen de pagos y milestones por conductor
          </p>
        </Link>

        <Link
          href="/pagos/driver-matrix"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow border border-gray-200"
        >
          <h2 className="text-xl font-semibold mb-2">Driver Matrix</h2>
          <p className="text-sm text-gray-600">
            Matriz por conductor: hitos M1/M5/M25, expected vs paid y ventana de pagos
          </p>
        </Link>
      </div>

      <div className="border-t border-gray-200 pt-8 mt-8">
        <h2 className="text-2xl font-bold mb-6">Elegibilidad de Pagos</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {eligibility && (
        <div className="mb-4 text-sm text-gray-600">
          Total: {eligibility.count} registros
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => setFilters(values as typeof filters)}
        onReset={() => {
          setFilters({
            origin_tag: '',
            rule_scope: '',
            is_payable: '',
            scout_id: '',
            driver_id: '',
            payable_from: '',
            payable_to: '',
            order_by: 'payable_date',
            order_dir: 'asc',
          });
          setOffset(0);
        }}
      />

      <DataTable
        data={eligibility?.rows || []}
        columns={columns}
        loading={loading}
        emptyMessage="No hay pagos elegibles que coincidan con los filtros"
      />

      {!loading && eligibility && eligibility.rows.length > 0 && (
        <Pagination
          total={eligibility.count}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}
