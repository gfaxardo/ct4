'use client';

import { useEffect, useState, useCallback } from 'react';
import { getCabinetLimbo, exportCabinetLimboCSV, ApiError } from '@/lib/api';
import type { CabinetLimboResponse, CabinetLimboRow } from '@/lib/types';
import Badge from '@/components/Badge';
import DataTable from '@/components/DataTable';
import Pagination from '@/components/Pagination';

interface CabinetLimboSectionProps {
  className?: string;
}

export default function CabinetLimboSection({ className = '' }: CabinetLimboSectionProps) {
  const [data, setData] = useState<CabinetLimboResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    limbo_stage: '',
    week_start: '',
    lead_date_from: '',
    lead_date_to: '',
  });
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(50);
  const [exporting, setExporting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getCabinetLimbo({
        limbo_stage: filters.limbo_stage as any || undefined,
        week_start: filters.week_start || undefined,
        lead_date_from: filters.lead_date_from || undefined,
        lead_date_to: filters.lead_date_to || undefined,
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
      const blob = await exportCabinetLimboCSV({
        limbo_stage: filters.limbo_stage as any || undefined,
        week_start: filters.week_start || undefined,
        lead_date_from: filters.lead_date_from || undefined,
        lead_date_to: filters.lead_date_to || undefined,
        limit: 10000,
      });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cabinet_limbo_${new Date().toISOString().split('T')[0]}.csv`;
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

  const getLimboStageBadgeVariant = (stage: string) => {
    switch (stage) {
      case 'NO_IDENTITY':
        return 'error';
      case 'NO_DRIVER':
        return 'warning';
      case 'NO_TRIPS_14D':
        return 'info';
      case 'TRIPS_NO_CLAIM':
        return 'error';
      case 'OK':
        return 'success';
      default:
        return 'warning';
    }
  };

  const columns = [
    {
      key: 'week_start',
      header: 'Semana',
      render: (row: CabinetLimboRow) => row.week_start ? new Date(row.week_start).toLocaleDateString() : '-',
    },
    {
      key: 'lead_date',
      header: 'Lead Date',
      render: (row: CabinetLimboRow) => row.lead_date ? new Date(row.lead_date).toLocaleDateString() : '-',
    },
    {
      key: 'lead_source_pk',
      header: 'Source PK',
      render: (row: CabinetLimboRow) => (
        <span className="font-mono text-xs">{row.lead_source_pk.substring(0, 20)}...</span>
      ),
    },
    {
      key: 'limbo_stage',
      header: 'Etapa',
      render: (row: CabinetLimboRow) => (
        <Badge variant={getLimboStageBadgeVariant(row.limbo_stage)}>
          {row.limbo_stage}
        </Badge>
      ),
    },
    {
      key: 'person_key',
      header: 'Person Key',
      render: (row: CabinetLimboRow) => row.person_key ? (
        <span className="font-mono text-xs">{row.person_key.substring(0, 8)}...</span>
      ) : '-',
    },
    {
      key: 'driver_id',
      header: 'Driver ID',
      render: (row: CabinetLimboRow) => row.driver_id ? (
        <span className="font-mono text-xs">{row.driver_id.substring(0, 12)}...</span>
      ) : '-',
    },
    {
      key: 'trips_14d',
      header: 'Trips 14d',
      render: (row: CabinetLimboRow) => row.trips_14d || 0,
    },
    {
      key: 'milestones',
      header: 'Milestones',
      render: (row: CabinetLimboRow) => (
        <div className="flex gap-1">
          {row.reached_m1_14d && <span className="text-xs bg-blue-100 px-1 rounded">M1</span>}
          {row.reached_m5_14d && <span className="text-xs bg-green-100 px-1 rounded">M5</span>}
          {row.reached_m25_14d && <span className="text-xs bg-purple-100 px-1 rounded">M25</span>}
          {!row.reached_m1_14d && !row.reached_m5_14d && !row.reached_m25_14d && <span className="text-xs text-gray-400">-</span>}
        </div>
      ),
    },
    {
      key: 'limbo_reason_detail',
      header: 'Razón',
      render: (row: CabinetLimboRow) => (
        <span className="text-xs text-gray-600" title={row.limbo_reason_detail}>
          {row.limbo_reason_detail.substring(0, 50)}...
        </span>
      ),
    },
  ];

  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Leads en Limbo (LEAD-first)</h2>
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

      {/* Resumen por etapa */}
      {data?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
          <div className="bg-red-50 p-3 rounded">
            <div className="text-sm text-gray-600">NO_IDENTITY</div>
            <div className="text-2xl font-bold text-red-600">{data.summary.limbo_no_identity}</div>
          </div>
          <div className="bg-yellow-50 p-3 rounded">
            <div className="text-sm text-gray-600">NO_DRIVER</div>
            <div className="text-2xl font-bold text-yellow-600">{data.summary.limbo_no_driver}</div>
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <div className="text-sm text-gray-600">NO_TRIPS_14D</div>
            <div className="text-2xl font-bold text-blue-600">{data.summary.limbo_no_trips_14d}</div>
          </div>
          <div className="bg-orange-50 p-3 rounded">
            <div className="text-sm text-gray-600">TRIPS_NO_CLAIM</div>
            <div className="text-2xl font-bold text-orange-600">{data.summary.limbo_trips_no_claim}</div>
          </div>
          <div className="bg-green-50 p-3 rounded">
            <div className="text-sm text-gray-600">OK</div>
            <div className="text-2xl font-bold text-green-600">{data.summary.limbo_ok}</div>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm text-gray-600">Total</div>
            <div className="text-2xl font-bold">{data.summary.total_leads}</div>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <select
          value={filters.limbo_stage}
          onChange={(e) => {
            setFilters(prev => ({ ...prev, limbo_stage: e.target.value }));
            setOffset(0);
          }}
          className="border rounded px-3 py-2"
        >
          <option value="">Todas las etapas</option>
          <option value="NO_IDENTITY">NO_IDENTITY</option>
          <option value="NO_DRIVER">NO_DRIVER</option>
          <option value="NO_TRIPS_14D">NO_TRIPS_14D</option>
          <option value="TRIPS_NO_CLAIM">TRIPS_NO_CLAIM</option>
          <option value="OK">OK</option>
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
