'use client';

import { useEffect, useState, useCallback } from 'react';
import { getCabinetClaimsGap, exportCabinetClaimsGapCSV, ApiError } from '@/lib/api';
import type { CabinetClaimsGapResponse, CabinetClaimsGapRow } from '@/lib/types';
import Badge from '@/components/Badge';
import DataTable from '@/components/DataTable';
import Pagination from '@/components/Pagination';

interface CabinetClaimsGapSectionProps {
  className?: string;
}

export default function CabinetClaimsGapSection({ className = '' }: CabinetClaimsGapSectionProps) {
  const [data, setData] = useState<CabinetClaimsGapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    gap_reason: '',
    week_start: '',
    lead_date_from: '',
    lead_date_to: '',
    milestone_value: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(50);
  const [exporting, setExporting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getCabinetClaimsGap({
        gap_reason: filters.gap_reason || undefined,
        week_start: filters.week_start || undefined,
        lead_date_from: filters.lead_date_from || undefined,
        lead_date_to: filters.lead_date_to || undefined,
        milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
        limit,
        offset,
      });

      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Error ${err.status}: ${err.detail || err.message}`);
      } else {
        setError('Error desconocido');
      }
    } finally {
      setLoading(false);
    }
  }, [filters, limit, offset]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = async () => {
    try {
      setExporting(true);
      const blob = await exportCabinetClaimsGapCSV({
        gap_reason: filters.gap_reason || undefined,
        week_start: filters.week_start || undefined,
        lead_date_from: filters.lead_date_from || undefined,
        lead_date_to: filters.lead_date_to || undefined,
        milestone_value: filters.milestone_value ? parseInt(filters.milestone_value) : undefined,
        limit: 10000,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cabinet_claims_gap_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Error exportando:', err);
      alert('Error al exportar CSV');
    } finally {
      setExporting(false);
    }
  };

  const getGapReasonBadgeVariant = (reason: string) => {
    switch (reason) {
      case 'CLAIM_NOT_GENERATED':
        return 'error';
      case 'OK':
        return 'success';
      case 'NO_IDENTITY':
      case 'NO_DRIVER':
      case 'INSUFFICIENT_TRIPS':
        return 'info';
      default:
        return 'warning';
    }
  };

  const getClaimStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'CLAIM_NOT_GENERATED':
        return 'error';
      case 'OK':
        return 'success';
      case 'INVALID':
        return 'warning';
      default:
        return 'warning';
    }
  };

  const columns = [
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: CabinetClaimsGapRow) => row.lead_date ? new Date(row.lead_date).toLocaleDateString() : '-',
    },
    {
      key: 'week_start',
      header: 'Semana',
      render: (row: CabinetClaimsGapRow) => row.week_start ? new Date(row.week_start).toLocaleDateString() : '-',
    },
    {
      key: 'driver_id',
      header: 'Driver ID',
      render: (row: CabinetClaimsGapRow) => row.driver_id ? (
        <span className="font-mono text-xs">{row.driver_id.substring(0, 12)}...</span>
      ) : '-',
    },
    {
      key: 'milestone_value',
      header: 'Milestone',
      render: (row: CabinetClaimsGapRow) => (
        <span className="font-bold">M{row.milestone_value}</span>
      ),
    },
    {
      key: 'trips_14d',
      header: 'Trips 14d',
      render: (row: CabinetClaimsGapRow) => row.trips_14d || 0,
    },
    {
      key: 'expected_amount',
      header: 'Monto Esperado',
      render: (row: CabinetClaimsGapRow) => `S/ ${parseFloat(String(row.expected_amount || 0)).toFixed(2)}`,
    },
    {
      key: 'claim_status',
      header: 'Estado',
      render: (row: CabinetClaimsGapRow) => (
        <Badge variant={getClaimStatusBadgeVariant(row.claim_status)}>
          {row.claim_status}
        </Badge>
      ),
    },
    {
      key: 'gap_reason',
      header: 'Razón',
      render: (row: CabinetClaimsGapRow) => (
        <Badge variant={getGapReasonBadgeVariant(row.gap_reason)}>
          {row.gap_reason}
        </Badge>
      ),
    },
  ];

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Claims Gap (CLAIM-first)</h2>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {exporting ? 'Exportando...' : 'Exportar CSV'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Resumen */}
      {data?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-red-50 p-3 rounded">
            <div className="text-sm text-gray-600">Gaps Totales</div>
            <div className="text-2xl font-bold text-red-600">{data.summary.total_gaps}</div>
          </div>
          <div className="bg-orange-50 p-3 rounded">
            <div className="text-sm text-gray-600">Claim No Generado</div>
            <div className="text-2xl font-bold text-orange-600">{data.summary.gaps_milestone_achieved_no_claim}</div>
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <div className="text-sm text-gray-600">Monto por Cobrar</div>
            <div className="text-2xl font-bold text-blue-600">
              S/ {parseFloat(String(data.summary?.total_expected_amount || 0)).toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">M1: {data.summary.gaps_m1} | M5: {data.summary.gaps_m5} | M25: {data.summary.gaps_m25}</div>
            <div className="text-xs text-gray-500">Por milestone</div>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
        <select
          value={filters.gap_reason}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, gap_reason: e.target.value }));
            setOffset(0);
          }}
          className="border rounded px-3 py-2"
        >
          <option value="">Todas las razones</option>
          <option value="CLAIM_NOT_GENERATED">Claim No Generado</option>
          <option value="OK">OK (Claim Existe)</option>
          <option value="NO_IDENTITY">Sin Identidad</option>
          <option value="NO_DRIVER">Sin Driver</option>
          <option value="INSUFFICIENT_TRIPS">Viajes Insuficientes</option>
        </select>
        <input
          type="date"
          value={filters.week_start}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, week_start: e.target.value }));
            setOffset(0);
          }}
          placeholder="Semana (week_start)"
          className="border rounded px-3 py-2"
        />
        <input
          type="date"
          value={filters.lead_date_from}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, lead_date_from: e.target.value }));
            setOffset(0);
          }}
          placeholder="Lead date desde"
          className="border rounded px-3 py-2"
        />
        <input
          type="date"
          value={filters.lead_date_to}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, lead_date_to: e.target.value }));
            setOffset(0);
          }}
          placeholder="Lead date hasta"
          className="border rounded px-3 py-2"
        />
        <select
          value={filters.milestone_value}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, milestone_value: e.target.value }));
            setOffset(0);
          }}
          className="border rounded px-3 py-2"
        >
          <option value="">Todos los milestones</option>
          <option value="1">M1</option>
          <option value="5">M5</option>
          <option value="25">M25</option>
        </select>
      </div>

      {/* Tabla */}
      {loading ? (
        <div className="text-center py-8">Cargando...</div>
      ) : data ? (
        <>
          <DataTable columns={columns} data={data.data} />
          <Pagination
            limit={limit}
            offset={offset}
            total={data.meta.total}
            onLimitChange={setLimit}
            onOffsetChange={setOffset}
          />
        </>
      ) : null}
    </div>
  );
}
