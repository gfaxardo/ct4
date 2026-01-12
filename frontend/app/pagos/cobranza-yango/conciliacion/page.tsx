/**
 * Yango - Cobranza Conciliación (Vista Admin/Operativa)
 * Vista gemela de Cobranza Yango para conciliación de pagos
 * 
 * Objetivo: "Conciliar pagos esperados vs pagados, con acciones de administración"
 * 
 * NOTA: Esta vista es READ-ONLY respecto a claims (C3). No altera reglas de negocio.
 * Las acciones permitidas son para conciliación (importar ledger, auto-match, excepciones).
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getCabinetFinancial14d,
  exportCabinetFinancial14dCSV,
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

export default function CobranzaYangoConciliacionPage() {
  const router = useRouter();
  const [data, setData] = useState<CabinetFinancialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    only_with_debt: true,
    reached_milestone: '',
    scout_id: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await getCabinetFinancial14d({
          only_with_debt: filters.only_with_debt,
          reached_milestone: filters.reached_milestone ? filters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
          scout_id: filters.scout_id ? parseInt(filters.scout_id) : undefined,
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
            setError('Error al cargar datos de conciliación');
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

  const handleExport = async () => {
    try {
      setExporting(true);
      setError(null);

      const blob = await exportCabinetFinancial14dCSV({
        only_with_debt: filters.only_with_debt,
        reached_milestone: filters.reached_milestone ? filters.reached_milestone as 'm1' | 'm5' | 'm25' : undefined,
        use_materialized: true,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cobranza_yango_conciliacion_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error al exportar: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido al exportar');
      }
    } finally {
      setExporting(false);
    }
  };

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
    {
      name: 'scout_id',
      label: 'Scout ID',
      type: 'number' as const,
    },
  ];

  // Calcular estado de pago basado en claims
  const getPaymentStatus = (row: CabinetFinancialRow): 'unpaid' | 'partial' | 'paid' | 'overpaid' => {
    const expected = Number(row.expected_total_yango) || 0;
    const paid = Number(row.total_paid_yango) || 0;
    
    if (expected === 0) return 'unpaid';
    if (paid === 0) return 'unpaid';
    if (paid >= expected) return paid > expected ? 'overpaid' : 'paid';
    return 'partial';
  };

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
      key: 'scout',
      header: 'Scout',
      render: (row: CabinetFinancialRow) => {
        if (row.scout_id) {
          return (
            <div className="flex flex-col gap-1">
              <Badge variant={row.is_scout_resolved ? 'success' : 'warning'}>
                Scout {row.scout_id}
              </Badge>
              {row.scout_name && (
                <div className="text-xs text-gray-500">{row.scout_name}</div>
              )}
            </div>
          );
        }
        return <Badge variant="error">Sin scout</Badge>;
      },
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
      header: 'Esperado (C3)',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.expected_total_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'total_paid_yango',
      header: 'Pagado (C4)',
      render: (row: CabinetFinancialRow) =>
        `S/ ${(Number(row.total_paid_yango) || 0).toFixed(2)}`,
    },
    {
      key: 'payment_status',
      header: 'Estado Pago',
      render: (row: CabinetFinancialRow) => {
        const status = getPaymentStatus(row);
        const variant = status === 'paid' ? 'success' : status === 'partial' ? 'warning' : status === 'overpaid' ? 'error' : 'error';
        const labels = {
          unpaid: 'No pagado',
          partial: 'Parcial',
          paid: 'Pagado',
          overpaid: 'Sobrepagado',
        };
        return <Badge variant={variant}>{labels[status]}</Badge>;
      },
    },
    {
      key: 'amount_due_yango',
      header: 'Diferencia',
      render: (row: CabinetFinancialRow) => {
        const amount = Number(row.amount_due_yango) || 0;
        return (
          <span className={amount > 0 ? 'text-red-600 font-semibold' : amount < 0 ? 'text-orange-600' : 'text-green-600'}>
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
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Cobranza Yango - Conciliación</h1>
            <p className="text-gray-600">
              Vista admin/operativa para conciliación de pagos. Mismo dataset que Cobranza Yango con columnas adicionales C3/C4.
            </p>
            <p className="text-sm text-gray-500 mt-2">
              <strong>Nota:</strong> Esta vista es READ-ONLY respecto a claims (C3). No altera reglas de negocio.
              Las acciones permitidas son para conciliación (importar ledger, auto-match, excepciones).
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => router.push('/pagos/cobranza-yango')}
              className="px-4 py-2 bg-gray-100 text-gray-700 border border-gray-300 rounded hover:bg-gray-200 flex items-center gap-2 text-sm"
            >
              ← Vista Principal
            </button>
            <button
              onClick={handleExport}
              disabled={exporting || loading}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {exporting ? (
                <>
                  <span className="animate-spin">⏳</span>
                  <span>Exportando...</span>
                </>
              ) : (
                <>
                  <span>📥</span>
                  <span>Exportar CSV</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <StatCard
            title="Total Deuda (filtrado)"
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

      <div className="mb-4 flex items-center justify-between">
        <Filters
          fields={filterFields}
          values={filters}
          onChange={(values) => {
            setFilters(values as typeof filters);
            setOffset(0);
          }}
          onReset={() => {
            setFilters({ only_with_debt: true, reached_milestone: '', scout_id: '' });
            setOffset(0);
          }}
        />
      </div>

      {/* Acciones de conciliación (stub para futuro) */}
      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">Acciones de Conciliación (Próximamente)</h3>
        <div className="flex gap-2">
          <button
            disabled
            className="px-3 py-1 bg-gray-200 text-gray-500 rounded text-sm cursor-not-allowed"
          >
            📤 Importar Ledger
          </button>
          <button
            disabled
            className="px-3 py-1 bg-gray-200 text-gray-500 rounded text-sm cursor-not-allowed"
          >
            🔄 Auto-match Pagos ↔ Claims
          </button>
          <button
            disabled
            className="px-3 py-1 bg-gray-200 text-gray-500 rounded text-sm cursor-not-allowed"
          >
            ⚠️ Marcar Excepciones
          </button>
          <button
            disabled
            className="px-3 py-1 bg-gray-200 text-gray-500 rounded text-sm cursor-not-allowed"
          >
            📋 Ver Evidence Pack
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-2">
          Estas acciones estarán disponibles en una futura iteración.
        </p>
      </div>

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
