/**
 * Yango - Cobranza (Cabinet Financial 14d)
 * Fuente de verdad financiera para CABINET
 * 
 * Objetivo: "¿Qué conductores generan pago de Yango y cuánto nos deben?"
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getCabinetFinancial14d,
  ApiError,
} from '@/lib/api';
import type {
  CabinetFinancialResponse,
  CabinetFinancialRow,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

export default function CobranzaYangoPage() {
  const router = useRouter();
  const [data, setData] = useState<CabinetFinancialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    only_with_debt: true,
    reached_milestone: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await getCabinetFinancial14d({
          only_with_debt: filters.only_with_debt,
          reached_milestone: filters.reached_milestone ? filters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
          limit,
          offset,
          include_summary: true,
          use_materialized: true,
        });

        setData(response);
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
      name: 'only_with_debt',
      label: 'Solo con deuda',
      type: 'checkbox' as const,
    },
    {
      name: 'reached_milestone',
      label: 'Milestone alcanzado',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: 'm1', label: 'Solo M1 (1-4 viajes)' },
        { value: 'm5', label: 'M5 pero no M25 (5-24 viajes)' },
        { value: 'm25', label: 'M25 alcanzado (25+ viajes)' },
      ],
    },
  ];

  const columns = [
    {
      key: 'driver_name',
      header: 'Conductor',
      render: (row: CabinetFinancialRow) =>
        row.driver_name ? (
          <div>
            <div className="font-medium">{row.driver_name}</div>
            <div className="text-xs text-gray-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : (
                '—'
              )}
            </div>
          </div>
        ) : (
          <div>
            <div className="text-gray-400">N/A</div>
            <div className="text-xs text-gray-500">
              {row.driver_id ? (
                <button
                  onClick={() => router.push(`/pagos/cobranza-yango/driver/${row.driver_id}`)}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  {row.driver_id.substring(0, 8)}...
                </button>
              ) : (
                '—'
              )}
            </div>
          </div>
        ),
    },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: CabinetFinancialRow) => (
        <div>
          <div>{row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—'}</div>
          {row.iso_week && (
            <div className="text-xs text-gray-500">Semana: {row.iso_week}</div>
          )}
        </div>
      ),
    },
    {
      key: 'connected_flag',
      header: 'Conectado',
      render: (row: CabinetFinancialRow) => (
        <Badge variant={row.connected_flag ? 'success' : 'warning'}>
          {row.connected_flag ? 'Sí' : 'No'}
        </Badge>
      ),
    },
    {
      key: 'total_trips_14d',
      header: 'Viajes 14d',
      render: (row: CabinetFinancialRow) => row.total_trips_14d || 0,
    },
    {
      key: 'milestones',
      header: 'Milestones',
      render: (row: CabinetFinancialRow) => {
        const milestones = [];
        if (row.reached_m1_14d) milestones.push('M1');
        if (row.reached_m5_14d) milestones.push('M5');
        if (row.reached_m25_14d) milestones.push('M25');
        
        if (milestones.length === 0) {
          return <span className="text-gray-400">—</span>;
        }
        
        return (
          <div className="flex gap-1 flex-wrap">
            {milestones.map((m) => (
              <Badge key={m} variant="info">{m}</Badge>
            ))}
          </div>
        );
      },
    },
    {
      key: 'expected_total_yango',
      header: 'Esperado',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.expected_total_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'total_paid_yango',
      header: 'Pagado',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.total_paid_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'amount_due_yango',
      header: 'Deuda',
      render: (row: CabinetFinancialRow) => {
        const amount = Number(row.amount_due_yango) || 0;
        return (
          <span className={amount > 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>
            S/ {amount.toFixed(2)}
          </span>
        );
      },
    },
    {
      key: 'claims_status',
      header: 'Estado Claims',
      render: (row: CabinetFinancialRow) => {
        const claims = [];
        
        if (row.reached_m1_14d) {
          if (row.claim_m1_exists) {
            claims.push(
              <div key="m1" className="text-xs">
                M1: <Badge variant={row.claim_m1_paid ? 'success' : 'warning'}>
                  {row.claim_m1_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m1" className="text-xs">
                M1: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (row.reached_m5_14d) {
          if (row.claim_m5_exists) {
            claims.push(
              <div key="m5" className="text-xs">
                M5: <Badge variant={row.claim_m5_paid ? 'success' : 'warning'}>
                  {row.claim_m5_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m5" className="text-xs">
                M5: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (row.reached_m25_14d) {
          if (row.claim_m25_exists) {
            claims.push(
              <div key="m25" className="text-xs">
                M25: <Badge variant={row.claim_m25_paid ? 'success' : 'warning'}>
                  {row.claim_m25_paid ? 'Pagado' : 'Pendiente'}
                </Badge>
              </div>
            );
          } else {
            claims.push(
              <div key="m25" className="text-xs">
                M25: <Badge variant="error">Sin claim</Badge>
              </div>
            );
          }
        }
        
        if (claims.length === 0) {
          return <span className="text-gray-400">—</span>;
        }
        
        return <div className="flex flex-col gap-1">{claims}</div>;
      },
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Cobranza Yango - Cabinet Financial 14d</h1>
        <p className="text-gray-600">
          Fuente de verdad financiera para CABINET. Ventana de 14 días desde lead_date.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Summary Cards - Mostrando datos filtrados */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <StatCard
            title="Total Deuda Yango (filtrado)"
            value={`S/ ${(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}`}
          />
          <StatCard
            title="Total Esperado (filtrado)"
            value={`S/ ${(Number(data.summary?.total_expected_yango) || 0).toFixed(2)}`}
          />
          <StatCard
            title="Total Pagado (filtrado)"
            value={`S/ ${(Number(data.summary?.total_paid_yango) || 0).toFixed(2)}`}
          />
          <StatCard
            title="% Cobranza (filtrado)"
            value={`${(Number(data.summary?.collection_percentage) || 0).toFixed(2)}%`}
          />
        </div>
      )}

      {/* Resumen: Filtrado vs Total */}
      {data && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4">Resumen: Filtrado vs Total</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Columna izquierda: Datos filtrados */}
            <div className="bg-white p-4 rounded-lg shadow">
              <h3 className="font-semibold text-gray-700 mb-3 border-b pb-2">
                Datos Filtrados (Mostrados en tabla)
              </h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-gray-600">Total Drivers</div>
                  <div className="text-lg font-bold">{data.meta.total}</div>
                </div>
                <div>
                  <div className="text-gray-600">Con Deuda</div>
                  <div className="text-lg font-bold text-red-600">{data.summary?.drivers_with_debt || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M1 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m1 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M5 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m5 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">M25 Alcanzado</div>
                  <div className="text-lg font-bold">{data.summary?.drivers_m25 || 0}</div>
                </div>
                <div>
                  <div className="text-gray-600">Deuda Total</div>
                  <div className="text-lg font-bold text-red-600">
                    S/ {(Number(data.summary?.total_debt_yango) || 0).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            {/* Columna derecha: Total sin filtros */}
            {data.summary_total && (
              <div className="bg-blue-50 p-4 rounded-lg shadow border-2 border-blue-200">
                <h3 className="font-semibold text-blue-700 mb-3 border-b border-blue-300 pb-2">
                  Total Sin Filtros (Todos los drivers Cabinet)
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-gray-700">Total Drivers</div>
                    <div className="text-lg font-bold text-blue-700">{data.summary_total.total_drivers}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">Con Deuda</div>
                    <div className="text-lg font-bold text-red-600">{data.summary_total.drivers_with_debt}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M1 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m1}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M5 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m5}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">M25 Alcanzado</div>
                    <div className="text-lg font-bold">{data.summary_total.drivers_m25}</div>
                  </div>
                  <div>
                    <div className="text-gray-700">Deuda Total</div>
                    <div className="text-lg font-bold text-red-600">
                      S/ {(Number(data.summary_total.total_debt_yango) || 0).toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <Filters
        fields={filterFields}
        values={filters}
        onChange={(values) => {
          setFilters(values as typeof filters);
          setOffset(0);
        }}
        onReset={() => {
          setFilters({ only_with_debt: true, reached_milestone: '' });
          setOffset(0);
        }}
      />

      <DataTable
        data={data?.data || []}
        columns={columns}
        loading={loading}
        emptyMessage="No hay drivers con deuda pendiente que coincidan con los filtros"
      />

      {!loading && data && data.data.length > 0 && (
        <Pagination
          total={data.meta.total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}
    </div>
  );
}
