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
  getCabinetReconciliation,
  ApiError,
} from '@/lib/api';
import type {
  YangoReconciliationSummaryResponse,
  YangoReconciliationItemsResponse,
  CabinetReconciliationResponse,
  CabinetReconciliationRow,
} from '@/lib/types';
import StatCard from '@/components/StatCard';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';
import PaymentsLegend from '@/components/payments/PaymentsLegend';

// Helper functions para reconciliation_status
function getReconciliationStatusVariant(status: string | null): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (!status) return 'default';
  switch (status) {
    case 'OK':
      return 'success';
    case 'ACHIEVED_NOT_PAID':
      return 'warning';
    case 'PAID_WITHOUT_ACHIEVEMENT':
      return 'info';
    case 'NOT_APPLICABLE':
      return 'default';
    default:
      return 'default';
  }
}

function getReconciliationStatusLabel(status: string | null): string {
  if (!status) return '—';
  const labels: Record<string, string> = {
    'OK': 'OK',
    'ACHIEVED_NOT_PAID': 'Logrado, No Pagado',
    'PAID_WITHOUT_ACHIEVEMENT': 'Pagado, No Logrado',
    'NOT_APPLICABLE': 'No Aplicable',
  };
  return labels[status] || status;
}

function getReconciliationStatusDescription(status: string | null): string {
  if (!status) return '';
  const descriptions: Record<string, string> = {
    'OK': 'El milestone fue logrado operativamente y pagado por Yango.',
    'ACHIEVED_NOT_PAID': 'El milestone fue logrado operativamente pero aún no ha sido pagado por Yango.',
    'PAID_WITHOUT_ACHIEVEMENT': 'Yango pagó este milestone según sus criterios, pero no hay evidencia suficiente en nuestro sistema operativo. Estado válido y esperado.',
    'NOT_APPLICABLE': 'Ni logrado ni pagado.',
  };
  return descriptions[status] || '';
}

// Tipos para flags derivados
type DerivedFlag = 'OUT_OF_SEQUENCE' | 'EARLY_PAYMENT' | 'LATE_PAYMENT' | 'INCOMPLETE_SEQUENCE' | 'SEQUENCE_CORRECTED';

interface RowWithFlags extends CabinetReconciliationRow {
  derivedFlags: DerivedFlag[];
}

// Función para calcular días entre dos fechas
function daysBetween(date1: string | null, date2: string | null): number | null {
  if (!date1 || !date2) return null;
  try {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffTime = Math.abs(d2.getTime() - d1.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

// Función principal para detectar flags derivados
function detectDerivedFlags(
  currentRow: CabinetReconciliationRow,
  allRows: CabinetReconciliationRow[]
): DerivedFlag[] {
  const flags: DerivedFlag[] = [];
  const driverId = currentRow.driver_id;
  const milestoneValue = currentRow.milestone_value;
  const payDate = currentRow.pay_date;
  const achievedDate = currentRow.achieved_date;
  const reconciliationStatus = currentRow.reconciliation_status;
  const paidFlag = currentRow.paid_flag;

  if (!driverId || milestoneValue === null) return flags;

  // Filtrar rows del mismo driver
  const driverRows = allRows.filter(r => r.driver_id === driverId && r.milestone_value !== null);

  // 1) EARLY_PAYMENT
  if (reconciliationStatus === 'PAID_WITHOUT_ACHIEVEMENT' && payDate) {
    if (!achievedDate) {
      flags.push('EARLY_PAYMENT');
    } else {
      const daysDiff = daysBetween(achievedDate, payDate);
      if (daysDiff !== null && daysDiff < 0) {
        // achieved_date es posterior a pay_date
        flags.push('EARLY_PAYMENT');
      }
    }
  }

  // 2) LATE_PAYMENT
  if (achievedDate && payDate) {
    const daysDiff = daysBetween(achievedDate, payDate);
    if (daysDiff !== null && daysDiff > 7) {
      flags.push('LATE_PAYMENT');
    }
  }

  // 3) OUT_OF_SEQUENCE: milestone menor pagado después de uno mayor
  if (paidFlag && payDate) {
    const greaterMilestones = driverRows.filter(
      r => r.milestone_value !== null && 
      r.milestone_value > milestoneValue && 
      r.paid_flag && 
      r.pay_date
    );
    
    for (const greaterRow of greaterMilestones) {
      if (greaterRow.pay_date) {
        const daysDiff = daysBetween(greaterRow.pay_date, payDate);
        if (daysDiff !== null && daysDiff < 0) {
          // pay_date del milestone menor es posterior al pay_date del mayor
          flags.push('OUT_OF_SEQUENCE');
          break;
        }
      }
    }
  }

  // 4) INCOMPLETE_SEQUENCE: milestone mayor pagado pero faltan intermedios
  if (paidFlag && milestoneValue > 1) {
    const expectedMilestones = [1, 5, 25].filter(m => m < milestoneValue);
    const paidMilestones = driverRows
      .filter(r => r.paid_flag && r.milestone_value !== null && expectedMilestones.includes(r.milestone_value))
      .map(r => r.milestone_value!);
    
    // Verificar si faltan milestones intermedios esperados
    const missingMilestones = expectedMilestones.filter(m => !paidMilestones.includes(m));
    if (missingMilestones.length > 0) {
      flags.push('INCOMPLETE_SEQUENCE');
    }
  }

  // 5) SEQUENCE_CORRECTED: verificar si había problemas pero ahora están corregidos
  // Esto requiere analizar si todos los milestones esperados están presentes
  if (paidFlag) {
    const allExpectedMilestones = [1, 5, 25].filter(m => m <= milestoneValue);
    const allPaidMilestones = driverRows
      .filter(r => r.paid_flag && r.milestone_value !== null && allExpectedMilestones.includes(r.milestone_value))
      .map(r => r.milestone_value!)
      .sort((a, b) => a - b);
    
    // Si todos los milestones esperados están pagados y en secuencia
    const hasAllExpected = allExpectedMilestones.every(m => allPaidMilestones.includes(m));
    if (hasAllExpected && allPaidMilestones.length === allExpectedMilestones.length) {
      // Verificar si hay OUT_OF_SEQUENCE o INCOMPLETE_SEQUENCE en otros milestones
      const hasSequenceIssues = driverRows.some(r => {
        if (r.milestone_value === milestoneValue) return false;
        const otherFlags = detectDerivedFlags(r, allRows);
        return otherFlags.includes('OUT_OF_SEQUENCE') || otherFlags.includes('INCOMPLETE_SEQUENCE');
      });
      
      // Si este milestone está bien pero había problemas antes, podría ser corregido
      // Por simplicidad, solo marcamos si este es el milestone más alto y está completo
      if (milestoneValue === Math.max(...allPaidMilestones) && hasSequenceIssues) {
        flags.push('SEQUENCE_CORRECTED');
      }
    }
  }

  return flags;
}

// Función para obtener label y variant de flags derivados
function getDerivedFlagLabel(flag: DerivedFlag): string {
  const labels: Record<DerivedFlag, string> = {
    'OUT_OF_SEQUENCE': 'Fuera de Secuencia',
    'EARLY_PAYMENT': 'Pago Anticipado',
    'LATE_PAYMENT': 'Pago Tardío',
    'INCOMPLETE_SEQUENCE': 'Secuencia Incompleta',
    'SEQUENCE_CORRECTED': 'Secuencia Corregida',
  };
  return labels[flag];
}

function getDerivedFlagVariant(flag: DerivedFlag): 'success' | 'warning' | 'error' | 'info' | 'default' {
  const variants: Record<DerivedFlag, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
    'OUT_OF_SEQUENCE': 'warning',
    'EARLY_PAYMENT': 'info',
    'LATE_PAYMENT': 'warning',
    'INCOMPLETE_SEQUENCE': 'warning',
    'SEQUENCE_CORRECTED': 'success',
  };
  return variants[flag];
}

export default function YangoCabinetPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'summary' | 'reconciliation'>('summary');
  const [summary, setSummary] = useState<YangoReconciliationSummaryResponse | null>(null);
  const [items, setItems] = useState<YangoReconciliationItemsResponse | null>(null);
  const [cabinetReconciliation, setCabinetReconciliation] = useState<CabinetReconciliationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [reconciliationLoading, setReconciliationLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconciliationError, setReconciliationError] = useState<string | null>(null);
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

  // Cargar datos de reconciliación cuando se activa la pestaña
  useEffect(() => {
    if (activeTab === 'reconciliation') {
      async function loadReconciliation() {
        try {
          setReconciliationLoading(true);
          setReconciliationError(null);
          const data = await getCabinetReconciliation({ limit: 50, offset: 0 });
          setCabinetReconciliation(data);
        } catch (err) {
          if (err instanceof ApiError) {
            if (err.status === 400) {
              setReconciliationError('Parámetros inválidos');
            } else if (err.status === 500) {
              setReconciliationError('Error al cargar reconciliación');
            } else {
              setReconciliationError(`Error ${err.status}: ${err.detail || err.message}`);
            }
          } else {
            setReconciliationError('Error desconocido');
          }
        } finally {
          setReconciliationLoading(false);
        }
      }
      loadReconciliation();
    }
  }, [activeTab]);

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
      render: (row: SummaryRow) => row.amount_expected_sum ? Number(row.amount_expected_sum).toFixed(2) : '—',
    },
    {
      key: 'amount_paid_total_visible',
      header: 'Pagado Visible',
      render: (row: SummaryRow) => row.amount_paid_total_visible ? Number(row.amount_paid_total_visible).toFixed(2) : '—',
    },
    {
      key: 'amount_pending_active_sum',
      header: 'Pendiente Activo',
      render: (row: SummaryRow) => row.amount_pending_active_sum ? Number(row.amount_pending_active_sum).toFixed(2) : '—',
    },
    {
      key: 'amount_diff',
      header: 'Diferencia',
      render: (row: SummaryRow) => (
        <span className={row.amount_diff && row.amount_diff < 0 ? 'text-red-600' : ''}>
          {row.amount_diff ? Number(row.amount_diff).toFixed(2) : '—'}
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
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Yango - Reconciliación</h1>
        <PaymentsLegend />
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('summary')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'summary'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Resumen
          </button>
          <button
            onClick={() => setActiveTab('reconciliation')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'reconciliation'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Reconciliación
          </button>
        </nav>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {activeTab === 'summary' && (
        <>
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
        </>
      )}

      {activeTab === 'reconciliation' && (
        <div>
          {reconciliationError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-red-800">{reconciliationError}</p>
            </div>
          )}

          {reconciliationLoading && (
            <div className="mb-6">
              <p>Cargando datos de reconciliación...</p>
            </div>
          )}

          {!reconciliationLoading && !cabinetReconciliation && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Reconciliación de Milestones</h2>
              <p>Sin datos cargados</p>
            </div>
          )}

          {!reconciliationLoading && cabinetReconciliation && (
            <div>
              {/* Panel Informativo */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">ℹ️ Sobre la Reconciliación</h3>
                <p className="text-sm text-blue-800 mb-2">
                  Esta vista muestra el cruce explícito entre milestones <strong>logrados operativamente</strong> (ACHIEVED) 
                  y milestones <strong>pagados por Yango</strong> (PAID). El estado de reconciliación es <strong>explicativo, no correctivo</strong>.
                </p>
                <p className="text-xs text-blue-700 italic">
                  Principio rector: "El pasado no se corrige, se explica". No se recalculan milestones históricos ni se modifican pagos ejecutados.
                </p>
              </div>

              {/* Estadísticas Derivadas */}
              {cabinetReconciliation.rows.length > 0 && (() => {
                const stats = cabinetReconciliation.rows.reduce((acc, row) => {
                  const status = row.reconciliation_status || 'UNKNOWN';
                  acc[status] = (acc[status] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>);

                return (
                  <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(stats).map(([status, count]) => (
                      <div key={status} className="bg-white border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={getReconciliationStatusVariant(status)}>
                            {getReconciliationStatusLabel(status)}
                          </Badge>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">{count}</div>
                        <div className="text-xs text-gray-500">
                          {((count / cabinetReconciliation.rows.length) * 100).toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()}

              <h2 className="text-xl font-semibold mb-4">Reconciliación de Milestones</h2>

              {/* Leyenda Explicativa */}
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Cómo interpretar esta tabla</h3>
                <p className="text-xs text-gray-700 mb-3">
                  Las señales mostradas no indican errores ni bloqueos de pago. Son explicaciones informativas sobre cómo y cuándo el upstream ejecutó los pagos.
                </p>
                
                <div className="mb-3">
                  <h4 className="text-xs font-semibold text-gray-800 mb-2">Señales de secuencia:</h4>
                  <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                    <li><strong>Fuera de secuencia:</strong> pago válido que apareció después de uno mayor</li>
                    <li><strong>Pago adelantado:</strong> pago ejecutado antes de consolidarse la evidencia operativa</li>
                    <li><strong>Pago tardío:</strong> pago ejecutado con retraso</li>
                    <li><strong>Secuencia incompleta:</strong> no todos los milestones fueron pagados</li>
                    <li><strong>Secuencia corregida:</strong> el sistema se completó automáticamente con el tiempo</li>
                  </ul>
                </div>

                <div className="mb-3">
                  <h4 className="text-xs font-semibold text-gray-800 mb-2">Situaciones generales:</h4>
                  <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                    <li><strong>PAID_WITHOUT_ACHIEVEMENT:</strong> Estado válido. El upstream pagó bajo sus propias reglas.</li>
                    <li><strong>UPSTREAM_OVERPAYMENT:</strong> No es un error. Representa pagos legítimos ejecutados por upstream.</li>
                    <li><strong>INSUFFICIENT_TRIPS_CONFIRMED:</strong> Puede deberse a lag de datos o ventanas distintas.</li>
                    <li><strong>ACHIEVED_NOT_PAID:</strong> Milestone logrado, pago pendiente.</li>
                  </ul>
                </div>

                <p className="text-xs text-gray-700 italic border-t border-gray-300 pt-2 mt-2">
                  El sistema CT4 no corrige el pasado. Lo explica con evidencia.
                </p>
              </div>

              {/* Leyenda de Estados */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Leyenda de Estados</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="flex items-start gap-2">
                    <Badge variant="success">OK</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">Logrado y Pagado</p>
                      <p className="text-xs text-gray-600">El milestone fue logrado operativamente y pagado por Yango.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="warning">Logrado, No Pagado</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">ACHIEVED_NOT_PAID</p>
                      <p className="text-xs text-gray-600">El milestone fue logrado operativamente pero aún no ha sido pagado por Yango.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="info">Pagado, No Logrado</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">PAID_WITHOUT_ACHIEVEMENT</p>
                      <p className="text-xs text-gray-600">Yango pagó según sus criterios, sin evidencia suficiente en nuestro sistema. <strong>Estado válido y esperado</strong>.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="default">No Aplicable</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">NOT_APPLICABLE</p>
                      <p className="text-xs text-gray-600">Ni logrado ni pagado.</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Leyenda de Flags Derivados */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-semibold text-amber-900 mb-3">📊 Flags Derivados (Análisis de Secuencias)</h3>
                <p className="text-xs text-amber-800 mb-3 italic">
                  Estos flags se calculan en memoria analizando las secuencias de pagos por driver. Son informativos y no modifican los datos originales.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="flex items-start gap-2">
                    <Badge variant="warning">Fuera de Secuencia</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">OUT_OF_SEQUENCE</p>
                      <p className="text-xs text-gray-600">Un milestone menor fue pagado después de un milestone mayor del mismo driver.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="info">Pago Anticipado</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">EARLY_PAYMENT</p>
                      <p className="text-xs text-gray-600">PAID_WITHOUT_ACHIEVEMENT donde el pago ocurrió antes de la fecha de logro (o sin fecha de logro).</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="warning">Pago Tardío</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">LATE_PAYMENT</p>
                      <p className="text-xs text-gray-600">El pago ocurrió más de 7 días después de la fecha de logro.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="warning">Secuencia Incompleta</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">INCOMPLETE_SEQUENCE</p>
                      <p className="text-xs text-gray-600">Existe un milestone mayor pagado pero faltan milestones intermedios o inferiores pagados.</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Badge variant="success">Secuencia Corregida</Badge>
                    <div className="flex-1">
                      <p className="text-xs font-medium text-gray-700">SEQUENCE_CORRECTED</p>
                      <p className="text-xs text-gray-600">Inicialmente hubo problemas de secuencia, pero ahora todos los milestones esperados aparecen correctamente.</p>
                    </div>
                  </div>
                </div>
              </div>

              {cabinetReconciliation.rows.length === 0 ? (
                <p>Sin resultados</p>
              ) : (() => {
                // Calcular flags derivados para todos los rows
                const rowsWithFlags: RowWithFlags[] = cabinetReconciliation.rows.map(row => ({
                  ...row,
                  derivedFlags: detectDerivedFlags(row, cabinetReconciliation.rows),
                }));

                return (
                  <div className="overflow-x-auto">
                    <table className="min-w-full border border-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Driver ID</th>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Milestone</th>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Estado</th>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Señales</th>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Fecha Pago</th>
                          <th className="px-4 py-2 text-left border-b border-gray-200">Fecha Logrado</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rowsWithFlags.map((row, index) => {
                          const stableKey = row.driver_id && row.milestone_value
                            ? `${row.driver_id}-${row.milestone_value}-${index}`
                            : `row-${index}`;
                          return (
                            <tr key={stableKey} className="border-b border-gray-200 hover:bg-gray-50">
                              <td className="px-4 py-2">{row.driver_id || '—'}</td>
                              <td className="px-4 py-2">
                                <span className="font-medium">M{row.milestone_value || '—'}</span>
                              </td>
                              <td className="px-4 py-2">
                                <Badge variant={getReconciliationStatusVariant(row.reconciliation_status)}>
                                  {getReconciliationStatusLabel(row.reconciliation_status)}
                                </Badge>
                              </td>
                              <td className="px-4 py-2">
                                {row.derivedFlags.length === 0 ? (
                                  <span className="text-gray-400">—</span>
                                ) : (
                                  <div className="flex flex-wrap items-center gap-2">
                                    {row.derivedFlags.map((flag, flagIndex) => (
                                      <Badge
                                        key={flagIndex}
                                        variant={getDerivedFlagVariant(flag)}
                                      >
                                        {getDerivedFlagLabel(flag)}
                                      </Badge>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="px-4 py-2">
                                {row.pay_date ? new Date(row.pay_date).toLocaleDateString('es-ES') : '—'}
                              </td>
                              <td className="px-4 py-2">
                                {row.achieved_date ? new Date(row.achieved_date).toLocaleDateString('es-ES') : '—'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
