/**
 * React Query Configuration
 * 
 * Provides caching, deduplication, and background refetching for API calls.
 */

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useState } from 'react';

// Default options for all queries
const defaultQueryOptions = {
  queries: {
    // Data is considered fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
    // Cache data for 30 minutes
    gcTime: 30 * 60 * 1000,
    // Retry failed requests 2 times
    retry: 2,
    // Don't refetch on window focus in development
    refetchOnWindowFocus: process.env.NODE_ENV === 'production',
    // Note: removed placeholderData to allow proper skeleton display
  },
};

export function QueryProvider({ children }: { children: ReactNode }) {
  // Create client inside component to avoid shared state between requests
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: defaultQueryOptions })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

// Export query keys for consistency
export const queryKeys = {
  // Dashboard
  dashboardStats: ['dashboard', 'stats'] as const,
  dashboardMetrics: ['dashboard', 'metrics'] as const,
  scoutSummary: ['dashboard', 'scoutSummary'] as const,
  
  // Cobranza Yango
  cabinetFinancial: (filters: Record<string, unknown>) => ['cabinetFinancial', filters] as const,
  funnelGap: ['funnelGap'] as const,
  scoutAttributionMetrics: (filters: Record<string, unknown>) => ['scoutAttributionMetrics', filters] as const,
  weeklyKpis: (filters: Record<string, unknown>) => ['weeklyKpis', filters] as const,
  identityGaps: (page: number, pageSize: number) => ['identityGaps', page, pageSize] as const,
  identityGapAlerts: ['identityGapAlerts'] as const,
  cabinetLimbo: (filters: Record<string, unknown>) => ['cabinetLimbo', filters] as const,
  cabinetClaimsGap: (filters: Record<string, unknown>) => ['cabinetClaimsGap', filters] as const,
  
  // Identity
  identityStats: ['identity', 'stats'] as const,
  identityPersons: (filters: Record<string, unknown>) => ['identity', 'persons', filters] as const,
  identityUnmatched: (filters: Record<string, unknown>) => ['identity', 'unmatched', filters] as const,
  
  // Payments
  driverMatrix: (filters: Record<string, unknown>) => ['driverMatrix', filters] as const,
  paymentEligibility: (filters: Record<string, unknown>) => ['paymentEligibility', filters] as const,
};
