/**
 * Client-side providers wrapper
 */

'use client';

import { QueryProvider } from '@/lib/query-client';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      {children}
    </QueryProvider>
  );
}
