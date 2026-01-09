/**
 * Yango Cabinet Claims - Claims Exigibles
 * 
 * Objetivo: "¿Qué claims exigibles tenemos para cobrar a Yango?"
 */

'use client';

import { useEffect, useState } from 'react';
import {
  getYangoCabinetClaimsToCollect,
  getYangoCabinetClaimDrilldown,
  ApiError,
} from '@/lib/api';
import type {
  YangoCabinetClaimsResponse,
  YangoCabinetClaimRow,
  YangoCabinetClaimDrilldownResponse,
} from '@/lib/types';
import DataTable from '@/components/DataTable';
import Filters from '@/components/Filters';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';
import PaymentsLegend from '@/components/payments/PaymentsLegend';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function YangoCabinetClaimsPage() {
  const [claims, setClaims] = useState<YangoCabinetClaimRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    date_from: '',
    date_to: '',
    milestone_value: '',
    search: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(50);
  const [total, setTotal] = useState(0);
  
  // Drilldown modal state
  const [selectedClaim, setSelectedClaim] = useState<YangoCabinetClaimRow | null>(null);
  const [drilldownData, setDrilldownData] = useState<YangoCabinetClaimDrilldownResponse | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [drilldownError, setDrilldownError] = useState<string | null>(null);
  const [showDrilldownModal, setShowDrilldownModal] = useState(false);
  const [needsLeadDate, setNeedsLeadDate] = useState(false);
  const [leadDateForDrilldown, setLeadDateForDrilldown] = useState('');

  useEffect(() => {
    async function loadClaims() {
      try {
        setLoading(true);
        setError(null);

        const data = await getYangoCabinetClaimsToCollect({
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
          milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
          search: filters.search || undefined,
          limit,
          offset,
        });

        setClaims(data.rows);
        setTotal(data.total);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setError('Parámetros inválidos');
          } else if (err.status === 500) {
            setError('Error al cargar claims');
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

    loadClaims();
  }, [filters, offset, limit]);

  const handleRowClick = async (row: YangoCabinetClaimRow) => {
    if (!row.driver_id || !row.milestone_value) {
      return;
    }

    setSelectedClaim(row);
    setShowDrilldownModal(true);
    setDrilldownLoading(true);
    setDrilldownError(null);
    setNeedsLeadDate(false);
    setLeadDateForDrilldown('');

    try {
      const data = await getYangoCabinetClaimDrilldown(
        row.driver_id,
        row.milestone_value,
        row.lead_date || undefined
      );
      setDrilldownData(data);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          // Ambigüedad: necesita lead_date
          setNeedsLeadDate(true);
          setDrilldownError(err.detail || 'Ambigüedad: múltiples claims encontrados. Proporcione fecha lead.');
        } else if (err.status === 404) {
          setDrilldownError('Claim no encontrado');
        } else {
          setDrilldownError(`Error ${err.status}: ${err.detail || err.message}`);
        }
      } else {
        setDrilldownError('Error desconocido');
      }
    } finally {
      setDrilldownLoading(false);
    }
  };

  const handleRetryDrilldown = async () => {
    if (!selectedClaim?.driver_id || !selectedClaim?.milestone_value || !leadDateForDrilldown) {
      return;
    }

    setDrilldownLoading(true);
    setDrilldownError(null);

    try {
      const data = await getYangoCabinetClaimDrilldown(
        selectedClaim.driver_id,
        selectedClaim.milestone_value,
        leadDateForDrilldown
      );
      setDrilldownData(data);
      setNeedsLeadDate(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setDrilldownError(`Error ${err.status}: ${err.detail || err.message}`);
      } else {
        setDrilldownError('Error desconocido');
      }
    } finally {
      setDrilldownLoading(false);
    }
  };

  const handleExportCSV = () => {
    const searchParams = new URLSearchParams();
    if (filters.date_from) searchParams.set('date_from', filters.date_from);
    if (filters.date_to) searchParams.set('date_to', filters.date_to);
    if (filters.milestone_value) searchParams.set('milestone_value', filters.milestone_value);
    if (filters.search) searchParams.set('search', filters.search);

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/api/v1/yango/cabinet/claims/export${query ? `?${query}` : ''}`;
    window.open(url, '_blank');
  };

  const filterFields = [
    {
      name: 'date_from',
      label: 'Fecha Desde',
      type: 'date' as const,
    },
    {
      name: 'date_to',
      label: 'Fecha Hasta',
      type: 'date' as const,
    },
    {
      name: 'milestone_value',
      label: 'Milestone',
      type: 'select' as const,
      options: [
        { value: '', label: 'Todos' },
        { value: '1', label: '1' },
        { value: '5', label: '5' },
        { value: '25', label: '25' },
      ],
    },
    {
      name: 'search',
      label: 'Buscar (Driver ID/Nombre)',
      type: 'text' as const,
      placeholder: 'Ej: DRIVER123 o Juan Pérez',
    },
  ];

  const columns = [
    {
      key: 'driver_id',
      header: 'Driver ID',
      render: (row: YangoCabinetClaimRow) => row.driver_id || '—',
    },
    {
      key: 'driver_name',
      header: 'Nombre Conductor',
      render: (row: YangoCabinetClaimRow) => row.driver_name || '—',
    },
    {
      key: 'milestone_value',
      header: 'Milestone',
      render: (row: YangoCabinetClaimRow) => row.milestone_value || '—',
    },
    {
      key: 'expected_amount',
      header: 'Monto Exigible',
      render: (row: YangoCabinetClaimRow) =>
        row.expected_amount ? `S/ ${Number(row.expected_amount).toFixed(2)}` : '—',
    },
    {
      key: 'lead_date',
      header: 'Fecha Lead',
      render: (row: YangoCabinetClaimRow) =>
        row.lead_date ? new Date(row.lead_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'yango_due_date',
      header: 'Fecha Vencimiento',
      render: (row: YangoCabinetClaimRow) =>
        row.yango_due_date ? new Date(row.yango_due_date).toLocaleDateString('es-ES') : '—',
    },
    {
      key: 'days_overdue_yango',
      header: 'Días Vencidos',
      render: (row: YangoCabinetClaimRow) => (
        <span className={row.days_overdue_yango && row.days_overdue_yango > 0 ? 'text-red-600 font-semibold' : ''}>
          {row.days_overdue_yango ?? '—'}
        </span>
      ),
    },
    {
      key: 'yango_payment_status',
      header: 'Estado Pago',
      render: (row: YangoCabinetClaimRow) =>
        row.yango_payment_status ? (
          <Badge
            variant={
              row.yango_payment_status === 'PAID' ? 'success' :
              row.yango_payment_status === 'PAID_MISAPPLIED' ? 'warning' : 'error'
            }
          >
            {row.yango_payment_status}
          </Badge>
        ) : (
          '—'
        ),
    },
    {
      key: 'payment_key',
      header: 'Payment Key',
      render: (row: YangoCabinetClaimRow) => row.payment_key || '—',
    },
  ];

  return (
    <div className="px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Yango Cabinet - Claims Exigibles</h1>
          <PaymentsLegend />
        </div>
        <button
          onClick={handleExportCSV}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
        >
          Exportar CSV
        </button>
      </div>

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
          setFilters({ date_from: '', date_to: '', milestone_value: '', search: '' });
          setOffset(0);
        }}
      />

      <div className="mb-4">
        <p className="text-sm text-gray-600">
          Total: <span className="font-semibold">{total}</span> claims
        </p>
      </div>

      <DataTable
        data={claims}
        columns={columns}
        loading={loading}
        emptyMessage="No hay claims que coincidan con los filtros"
        onRowClick={handleRowClick}
      />

      {!loading && claims.length > 0 && (
        <Pagination
          total={total}
          limit={limit}
          offset={offset}
          onPageChange={(newOffset) => setOffset(newOffset)}
        />
      )}

      {/* Drilldown Modal */}
      {showDrilldownModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold">Drilldown del Claim</h2>
                <button
                  onClick={() => {
                    setShowDrilldownModal(false);
                    setSelectedClaim(null);
                    setDrilldownData(null);
                    setNeedsLeadDate(false);
                    setLeadDateForDrilldown('');
                  }}
                  className="text-gray-500 hover:text-gray-700 text-2xl"
                >
                  ×
                </button>
              </div>
              {selectedClaim && (
                <p className="text-sm text-gray-600 mt-2">
                  Driver ID: {selectedClaim.driver_id} | Milestone: {selectedClaim.milestone_value}
                </p>
              )}
            </div>

            <div className="p-6">
              {drilldownLoading && (
                <div className="text-center py-8">
                  <p className="text-gray-500">Cargando drilldown...</p>
                </div>
              )}

              {drilldownError && !needsLeadDate && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <p className="text-red-800">{drilldownError}</p>
                </div>
              )}

              {needsLeadDate && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <p className="text-yellow-800 mb-3">{drilldownError}</p>
                  <div className="flex gap-4 items-end">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Fecha Lead
                      </label>
                      <input
                        type="date"
                        value={leadDateForDrilldown}
                        onChange={(e) => setLeadDateForDrilldown(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>
                    <button
                      onClick={handleRetryDrilldown}
                      disabled={!leadDateForDrilldown}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Reintentar
                    </button>
                  </div>
                </div>
              )}

              {drilldownData && !drilldownLoading && (
                <div className="space-y-6">
                  {/* Claim Info */}
                  {drilldownData.claim && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Información del Claim</h3>
                      <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm text-gray-600">Driver ID:</span>
                          <p className="font-medium">{drilldownData.claim.driver_id || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Driver Name:</span>
                          <p className="font-medium">{drilldownData.claim.driver_name || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Milestone:</span>
                          <p className="font-medium">{drilldownData.claim.milestone_value || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Monto Esperado:</span>
                          <p className="font-medium">
                            {drilldownData.claim.expected_amount ? `S/ ${Number(drilldownData.claim.expected_amount).toFixed(2)}` : '—'}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Estado Pago:</span>
                          <p className="font-medium">
                            {drilldownData.claim.yango_payment_status ? (
                              <Badge
                                variant={
                                  drilldownData.claim.yango_payment_status === 'PAID' ? 'success' :
                                  drilldownData.claim.yango_payment_status === 'PAID_MISAPPLIED' ? 'warning' : 'error'
                                }
                              >
                                {drilldownData.claim.yango_payment_status}
                              </Badge>
                            ) : (
                              '—'
                            )}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Días Vencidos:</span>
                          <p className="font-medium">{drilldownData.claim.days_overdue_yango ?? '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Lead Cabinet Info */}
                  {drilldownData.lead_cabinet && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Lead Cabinet</h3>
                      <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm text-gray-600">Source PK:</span>
                          <p className="font-medium">{drilldownData.lead_cabinet.source_pk || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Match Rule:</span>
                          <p className="font-medium">{drilldownData.lead_cabinet.match_rule || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Match Score:</span>
                          <p className="font-medium">{drilldownData.lead_cabinet.match_score ?? '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Confidence:</span>
                          <p className="font-medium">{drilldownData.lead_cabinet.confidence_level || '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Payment Exact */}
                  {drilldownData.payment_exact && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Pago Exacto</h3>
                      <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm text-gray-600">Payment Key:</span>
                          <p className="font-medium">{drilldownData.payment_exact.payment_key || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Fecha Pago:</span>
                          <p className="font-medium">
                            {drilldownData.payment_exact.pay_date
                              ? new Date(drilldownData.payment_exact.pay_date).toLocaleDateString('es-ES')
                              : '—'}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Milestone:</span>
                          <p className="font-medium">{drilldownData.payment_exact.milestone_value ?? '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Identity Status:</span>
                          <p className="font-medium">{drilldownData.payment_exact.identity_status || '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Payments Other Milestones */}
                  {drilldownData.payments_other_milestones && drilldownData.payments_other_milestones.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Pagos en Otros Milestones</h3>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="space-y-3">
                          {drilldownData.payments_other_milestones.map((payment, idx) => (
                            <div key={idx} className="border-b border-gray-200 pb-3 last:border-0 last:pb-0">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <span className="text-sm text-gray-600">Payment Key:</span>
                                  <p className="font-medium">{payment.payment_key || '—'}</p>
                                </div>
                                <div>
                                  <span className="text-sm text-gray-600">Milestone:</span>
                                  <p className="font-medium">{payment.milestone_value ?? '—'}</p>
                                </div>
                                <div>
                                  <span className="text-sm text-gray-600">Fecha:</span>
                                  <p className="font-medium">
                                    {payment.pay_date
                                      ? new Date(payment.pay_date).toLocaleDateString('es-ES')
                                      : '—'}
                                  </p>
                                </div>
                                <div>
                                  <span className="text-sm text-gray-600">Identity Status:</span>
                                  <p className="font-medium">{payment.identity_status || '—'}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Reconciliation */}
                  {drilldownData.reconciliation && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Reconciliación</h3>
                      <div className="bg-gray-50 rounded-lg p-4 grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-sm text-gray-600">Estado:</span>
                          <p className="font-medium">{drilldownData.reconciliation.reconciliation_status || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Match Method:</span>
                          <p className="font-medium">{drilldownData.reconciliation.match_method || '—'}</p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Expected Amount:</span>
                          <p className="font-medium">
                            {drilldownData.reconciliation.expected_amount
                              ? `S/ ${Number(drilldownData.reconciliation.expected_amount).toFixed(2)}`
                              : '—'}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-600">Paid Payment Key:</span>
                          <p className="font-medium">{drilldownData.reconciliation.paid_payment_key || '—'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Misapplied Explanation */}
                  {drilldownData.misapplied_explanation && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Explicación PAID_MISAPPLIED</h3>
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <p className="text-yellow-800 whitespace-pre-wrap">{drilldownData.misapplied_explanation}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}










