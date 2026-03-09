/**
 * Hooks para Yango Reconciliation (cabinet) con React Query.
 * Misma optimización que cobranza: refetchOnMount: false para evitar GET duplicados.
 */

import { useQuery } from '@tanstack/react-query';
import {
  getYangoReconciliationSummary,
  getYangoReconciliationItems,
} from '@/lib/api';
import { queryKeys } from '@/lib/query-client';

export interface YangoReconciliationSummaryFilters {
  week_start?: string;
  milestone_value?: number;
  mode?: 'real' | 'assumed';
  limit?: number;
}

export interface YangoReconciliationItemsFilters {
  week_start?: string;
  milestone_value?: number;
  limit?: number;
  offset?: number;
}

export function useYangoReconciliationSummary(filters: YangoReconciliationSummaryFilters) {
  return useQuery({
    queryKey: queryKeys.yangoReconciliationSummary(filters as Record<string, unknown>),
    queryFn: () =>
      getYangoReconciliationSummary({
        week_start: filters.week_start,
        milestone_value: filters.milestone_value,
        mode: filters.mode,
        limit: filters.limit ?? 100,
      }),
    staleTime: 2 * 60 * 1000,
    refetchOnMount: false,
  });
}

export function useYangoReconciliationItems(filters: YangoReconciliationItemsFilters) {
  return useQuery({
    queryKey: queryKeys.yangoReconciliationItems(filters as Record<string, unknown>),
    queryFn: () =>
      getYangoReconciliationItems({
        week_start: filters.week_start,
        milestone_value: filters.milestone_value,
        limit: filters.limit ?? 100,
        offset: filters.offset ?? 0,
      }),
    staleTime: 2 * 60 * 1000,
    refetchOnMount: false,
  });
}
