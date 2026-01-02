/**
 * RawDataHealthPanel - Panel para mostrar salud de datos RAW
 * 
 * 3 secciones: Status, Freshness, Ingestion Daily
 * Cada sección con filtros, tabla, paginación y estados
 */

'use client';

import { useState, useEffect } from 'react';
import {
  getOpsRawHealthStatus,
  getOpsRawHealthFreshness,
  getOpsRawHealthIngestionDaily,
  ApiError,
} from '@/lib/api';
import type {
  RawDataHealthStatusRow,
  RawDataHealthStatusResponse,
  RawDataFreshnessStatusRow,
  RawDataFreshnessStatusResponse,
  RawDataIngestionDailyRow,
  RawDataIngestionDailyResponse,
} from '@/lib/types';
import DataTable from '@/components/DataTable';
import Pagination from '@/components/Pagination';
import Badge from '@/components/Badge';

const DEFAULT_LIMIT = 50;
const DEFAULT_OFFSET = 0;

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('es-ES');
  } catch {
    return dateStr;
  }
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('es-ES');
  } catch {
    return dateStr;
  }
}

function getHealthStatusBadge(status: string | null) {
  if (!status) return <span>—</span>;
  
  const upperStatus = status.toUpperCase();
  let variant: 'success' | 'warning' | 'error' | 'default' = 'default';
  
  if (upperStatus.includes('GREEN') || upperStatus === 'OK') {
    variant = 'success';
  } else if (upperStatus.includes('YELLOW') || upperStatus.includes('WARN')) {
    variant = 'warning';
  } else if (upperStatus.includes('RED') || upperStatus.includes('ERROR')) {
    variant = 'error';
  }
  
  return <Badge variant={variant}>{status}</Badge>;
}

export default function RawDataHealthPanel() {
  // Status state
  const [statusData, setStatusData] = useState<RawDataHealthStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [statusSource, setStatusSource] = useState('');
  const [statusOffset, setStatusOffset] = useState(DEFAULT_OFFSET);
  const [statusRetryKey, setStatusRetryKey] = useState(0);

  // Freshness state
  const [freshnessData, setFreshnessData] = useState<RawDataFreshnessStatusResponse | null>(null);
  const [freshnessLoading, setFreshnessLoading] = useState(false);
  const [freshnessError, setFreshnessError] = useState<string | null>(null);
  const [freshnessSource, setFreshnessSource] = useState('');
  const [freshnessOffset, setFreshnessOffset] = useState(DEFAULT_OFFSET);
  const [freshnessRetryKey, setFreshnessRetryKey] = useState(0);

  // Ingestion Daily state
  const [ingestionData, setIngestionData] = useState<RawDataIngestionDailyResponse | null>(null);
  const [ingestionLoading, setIngestionLoading] = useState(false);
  const [ingestionError, setIngestionError] = useState<string | null>(null);
  const [ingestionSource, setIngestionSource] = useState('');
  const [ingestionDateFrom, setIngestionDateFrom] = useState('');
  const [ingestionDateTo, setIngestionDateTo] = useState('');
  const [ingestionOffset, setIngestionOffset] = useState(DEFAULT_OFFSET);
  const [ingestionRetryKey, setIngestionRetryKey] = useState(0);

  // Load Status
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setStatusLoading(true);
        setStatusError(null);
        const response = await getOpsRawHealthStatus({
          limit: DEFAULT_LIMIT,
          offset: statusOffset,
          source: statusSource.trim() || undefined,
        });
        if (!cancelled) {
          setStatusData(response);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setStatusError(`Error ${err.status}: ${err.detail || err.message}`);
          } else {
            setStatusError('Error desconocido al cargar datos de status');
          }
        }
      } finally {
        if (!cancelled) {
          setStatusLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [statusSource, statusOffset, statusRetryKey]);

  // Load Freshness
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setFreshnessLoading(true);
        setFreshnessError(null);
        const response = await getOpsRawHealthFreshness({
          limit: DEFAULT_LIMIT,
          offset: freshnessOffset,
          source: freshnessSource.trim() || undefined,
        });
        if (!cancelled) {
          setFreshnessData(response);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setFreshnessError(`Error ${err.status}: ${err.detail || err.message}`);
          } else {
            setFreshnessError('Error desconocido al cargar datos de freshness');
          }
        }
      } finally {
        if (!cancelled) {
          setFreshnessLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [freshnessSource, freshnessOffset, freshnessRetryKey]);

  // Load Ingestion Daily
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setIngestionLoading(true);
        setIngestionError(null);
        const response = await getOpsRawHealthIngestionDaily({
          limit: DEFAULT_LIMIT,
          offset: ingestionOffset,
          source: ingestionSource.trim() || undefined,
          date_from: ingestionDateFrom.trim() || undefined,
          date_to: ingestionDateTo.trim() || undefined,
        });
        if (!cancelled) {
          setIngestionData(response);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setIngestionError(`Error ${err.status}: ${err.detail || err.message}`);
          } else {
            setIngestionError('Error desconocido al cargar datos de ingestion daily');
          }
        }
      } finally {
        if (!cancelled) {
          setIngestionLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [ingestionSource, ingestionDateFrom, ingestionDateTo, ingestionOffset, ingestionRetryKey]);

  // Status columns
  const statusColumns = [
    {
      key: 'source_name' as const,
      header: 'Source',
      render: (row: RawDataHealthStatusRow) => (
        <span className="font-mono text-sm">{row.source_name}</span>
      ),
    },
    {
      key: 'health_status' as const,
      header: 'Health Status',
      render: (row: RawDataHealthStatusRow) => getHealthStatusBadge(row.health_status),
    },
    {
      key: 'max_business_date' as const,
      header: 'Max Business Date',
      render: (row: RawDataHealthStatusRow) => formatDate(row.max_business_date),
    },
    {
      key: 'business_days_lag' as const,
      header: 'Business Days Lag',
      render: (row: RawDataHealthStatusRow) => row.business_days_lag ?? '—',
    },
    {
      key: 'max_ingestion_ts' as const,
      header: 'Max Ingestion TS',
      render: (row: RawDataHealthStatusRow) => formatDateTime(row.max_ingestion_ts),
    },
    {
      key: 'ingestion_lag_interval' as const,
      header: 'Ingestion Lag',
      render: (row: RawDataHealthStatusRow) => row.ingestion_lag_interval ?? '—',
    },
    {
      key: 'rows_business_today' as const,
      header: 'Rows Business Today',
      render: (row: RawDataHealthStatusRow) => row.rows_business_today ?? '—',
    },
    {
      key: 'rows_ingested_today' as const,
      header: 'Rows Ingested Today',
      render: (row: RawDataHealthStatusRow) => row.rows_ingested_today ?? '—',
    },
  ];

  // Freshness columns
  const freshnessColumns = [
    {
      key: 'source_name' as const,
      header: 'Source',
      render: (row: RawDataFreshnessStatusRow) => (
        <span className="font-mono text-sm">{row.source_name}</span>
      ),
    },
    {
      key: 'max_business_date' as const,
      header: 'Max Business Date',
      render: (row: RawDataFreshnessStatusRow) => formatDate(row.max_business_date),
    },
    {
      key: 'business_days_lag' as const,
      header: 'Business Days Lag',
      render: (row: RawDataFreshnessStatusRow) => row.business_days_lag ?? '—',
    },
    {
      key: 'max_ingestion_ts' as const,
      header: 'Max Ingestion TS',
      render: (row: RawDataFreshnessStatusRow) => formatDateTime(row.max_ingestion_ts),
    },
    {
      key: 'ingestion_lag_interval' as const,
      header: 'Ingestion Lag',
      render: (row: RawDataFreshnessStatusRow) => row.ingestion_lag_interval ?? '—',
    },
    {
      key: 'rows_ingested_today' as const,
      header: 'Rows Ingested Today',
      render: (row: RawDataFreshnessStatusRow) => {
        const value = row.rows_ingested_today ?? row.rows_ingested_yesterday ?? null;
        return value ?? '—';
      },
    },
  ];

  // Ingestion Daily columns
  const ingestionColumns = [
    {
      key: 'source_name' as const,
      header: 'Source',
      render: (row: RawDataIngestionDailyRow) => (
        <span className="font-mono text-sm">{row.source_name}</span>
      ),
    },
    {
      key: 'metric_type' as const,
      header: 'Metric Type',
    },
    {
      key: 'metric_date' as const,
      header: 'Metric Date',
      render: (row: RawDataIngestionDailyRow) => formatDate(row.metric_date),
    },
    {
      key: 'rows_count' as const,
      header: 'Rows Count',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Status Section */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Status</h2>
        
        {/* Filters */}
        <div className="mb-4 flex gap-4 items-end">
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source
            </label>
            <input
              type="text"
              value={statusSource}
              onChange={(e) => {
                setStatusSource(e.target.value);
                setStatusOffset(DEFAULT_OFFSET);
              }}
              placeholder="Filtrar por source..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Error */}
        {statusError && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 mb-2">{statusError}</p>
            <button
              onClick={() => {
                setStatusError(null);
                setStatusRetryKey((k) => k + 1);
              }}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Table */}
        <DataTable
          data={statusData?.items || []}
          columns={statusColumns}
          loading={statusLoading}
          emptyMessage="No hay datos de status disponibles"
        />

        {/* Pagination */}
        {statusData && statusData.total > 0 && (
          <Pagination
            total={statusData.total}
            limit={DEFAULT_LIMIT}
            offset={statusOffset}
            onPageChange={(newOffset) => setStatusOffset(newOffset)}
            className="mt-4"
          />
        )}
      </div>

      {/* Freshness Section */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Freshness</h2>
        
        {/* Filters */}
        <div className="mb-4 flex gap-4 items-end">
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source
            </label>
            <input
              type="text"
              value={freshnessSource}
              onChange={(e) => {
                setFreshnessSource(e.target.value);
                setFreshnessOffset(DEFAULT_OFFSET);
              }}
              placeholder="Filtrar por source..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Error */}
        {freshnessError && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 mb-2">{freshnessError}</p>
            <button
              onClick={() => {
                setFreshnessError(null);
                setFreshnessRetryKey((k) => k + 1);
              }}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Table */}
        <DataTable
          data={freshnessData?.items || []}
          columns={freshnessColumns}
          loading={freshnessLoading}
          emptyMessage="No hay datos de freshness disponibles"
        />

        {/* Pagination */}
        {freshnessData && freshnessData.total > 0 && (
          <Pagination
            total={freshnessData.total}
            limit={DEFAULT_LIMIT}
            offset={freshnessOffset}
            onPageChange={(newOffset) => setFreshnessOffset(newOffset)}
            className="mt-4"
          />
        )}
      </div>

      {/* Ingestion Daily Section */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Ingestion Daily</h2>
        
        {/* Filters */}
        <div className="mb-4 flex gap-4 items-end flex-wrap">
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source
            </label>
            <input
              type="text"
              value={ingestionSource}
              onChange={(e) => {
                setIngestionSource(e.target.value);
                setIngestionOffset(DEFAULT_OFFSET);
              }}
              placeholder="Filtrar por source..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date From
            </label>
            <input
              type="date"
              value={ingestionDateFrom}
              onChange={(e) => {
                setIngestionDateFrom(e.target.value);
                setIngestionOffset(DEFAULT_OFFSET);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="flex-1 max-w-xs">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date To
            </label>
            <input
              type="date"
              value={ingestionDateTo}
              onChange={(e) => {
                setIngestionDateTo(e.target.value);
                setIngestionOffset(DEFAULT_OFFSET);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Error */}
        {ingestionError && (
          <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 mb-2">{ingestionError}</p>
            <button
              onClick={() => {
                setIngestionError(null);
                setIngestionRetryKey((k) => k + 1);
              }}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              Reintentar
            </button>
          </div>
        )}

        {/* Table */}
        <DataTable
          data={ingestionData?.items || []}
          columns={ingestionColumns}
          loading={ingestionLoading}
          emptyMessage="No hay datos de ingestion daily disponibles"
        />

        {/* Pagination */}
        {ingestionData && ingestionData.total > 0 && (
          <Pagination
            total={ingestionData.total}
            limit={DEFAULT_LIMIT}
            offset={ingestionOffset}
            onPageChange={(newOffset) => setIngestionOffset(newOffset)}
            className="mt-4"
          />
        )}
      </div>
    </div>
  );
}

