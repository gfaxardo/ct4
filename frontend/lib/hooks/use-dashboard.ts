/**
 * Custom hooks for Dashboard with React Query caching
 */

import { useQuery } from '@tanstack/react-query';
import {
  getIdentityStats,
  getGlobalMetrics,
  getPersonsBySource,
  getDriversWithoutLeadsAnalysis,
  getOrphansMetrics,
} from '@/lib/api';
import { queryKeys } from '@/lib/query-client';

/**
 * Hook for identity stats with caching
 */
export function useIdentityStats() {
  return useQuery({
    queryKey: queryKeys.identityStats,
    queryFn: () => getIdentityStats(),
    staleTime: 5 * 60 * 1000, // 5 minutes - this data doesn't change often
  });
}

/**
 * Hook for global metrics with caching
 */
export function useGlobalMetrics(mode: 'summary' | 'weekly' | 'breakdowns') {
  return useQuery({
    queryKey: [...queryKeys.dashboardMetrics, mode],
    queryFn: () => getGlobalMetrics({ mode }), // Fix: pass as object
    staleTime: 3 * 60 * 1000, // 3 minutes
  });
}

/**
 * Hook for persons by source with caching
 */
export function usePersonsBySource() {
  return useQuery({
    queryKey: ['dashboard', 'personsBySource'],
    queryFn: () => getPersonsBySource(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for drivers without leads analysis with caching
 */
export function useDriversWithoutLeads() {
  return useQuery({
    queryKey: ['dashboard', 'driversWithoutLeads'],
    queryFn: () => getDriversWithoutLeadsAnalysis(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for orphans metrics with caching
 */
export function useOrphansMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'orphansMetrics'],
    queryFn: () => getOrphansMetrics(),
    staleTime: 2 * 60 * 1000, // 2 minutes - can change more frequently
  });
}
