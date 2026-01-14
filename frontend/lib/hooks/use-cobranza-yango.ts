/**
 * Custom hooks for Cobranza Yango with React Query caching
 */

import { useQuery } from '@tanstack/react-query';
import {
  getCabinetFinancial14d,
  getFunnelGapMetrics,
  getCobranzaYangoScoutAttributionMetrics,
  getCobranzaYangoWeeklyKpis,
  getIdentityGaps,
  getIdentityGapAlerts,
} from '@/lib/api';
import { queryKeys } from '@/lib/query-client';

interface CabinetFinancialFilters {
  only_with_debt?: boolean;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
  week_start?: string;
  limit?: number;
  offset?: number;
}

interface ScoutMetricsFilters {
  only_with_debt?: boolean;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
}

interface WeeklyKpisFilters {
  only_with_debt?: boolean;
  reached_milestone?: 'm1' | 'm5' | 'm25';
  scout_id?: number;
  limit_weeks?: number;
}

/**
 * Hook for cabinet financial data with caching
 */
export function useCabinetFinancial(filters: CabinetFinancialFilters) {
  return useQuery({
    queryKey: queryKeys.cabinetFinancial(filters),
    queryFn: () => getCabinetFinancial14d({
      only_with_debt: filters.only_with_debt,
      reached_milestone: filters.reached_milestone,
      scout_id: filters.scout_id,
      week_start: filters.week_start,
      limit: filters.limit || 100,
      offset: filters.offset || 0,
      include_summary: true,
      use_materialized: true,
    }),
    staleTime: 2 * 60 * 1000, // 2 minutes for main data
  });
}

/**
 * Hook for funnel gap metrics with caching
 */
export function useFunnelGap() {
  return useQuery({
    queryKey: queryKeys.funnelGap,
    queryFn: () => getFunnelGapMetrics(),
    staleTime: 5 * 60 * 1000, // 5 minutes - this data doesn't change often
  });
}

/**
 * Hook for scout attribution metrics with caching
 */
export function useScoutAttributionMetrics(filters: ScoutMetricsFilters) {
  return useQuery({
    queryKey: queryKeys.scoutAttributionMetrics(filters),
    queryFn: () => getCobranzaYangoScoutAttributionMetrics({
      only_with_debt: filters.only_with_debt,
      reached_milestone: filters.reached_milestone,
      scout_id: filters.scout_id,
      use_materialized: true,
    }),
    staleTime: 3 * 60 * 1000, // 3 minutes
  });
}

/**
 * Hook for weekly KPIs with caching
 */
export function useWeeklyKpis(filters: WeeklyKpisFilters) {
  return useQuery({
    queryKey: queryKeys.weeklyKpis(filters),
    queryFn: () => getCobranzaYangoWeeklyKpis({
      only_with_debt: filters.only_with_debt,
      reached_milestone: filters.reached_milestone,
      scout_id: filters.scout_id,
      limit_weeks: filters.limit_weeks || 52,
      use_materialized: true,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for identity gaps with caching
 */
export function useIdentityGaps(page: number = 1, pageSize: number = 100) {
  return useQuery({
    queryKey: queryKeys.identityGaps(page, pageSize),
    queryFn: () => getIdentityGaps({ page, page_size: pageSize }),
    staleTime: 60 * 1000, // 1 minute - this data can change
  });
}

/**
 * Hook for identity gap alerts with caching
 */
export function useIdentityGapAlerts() {
  return useQuery({
    queryKey: queryKeys.identityGapAlerts,
    queryFn: () => getIdentityGapAlerts(),
    staleTime: 60 * 1000, // 1 minute
  });
}
