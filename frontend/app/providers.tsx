/**
 * Client-side providers wrapper
 */

'use client';

import { QueryProvider } from '@/lib/query-client';
import { AuthProvider } from '@/lib/auth';
import ProtectedLayout from '@/components/ProtectedLayout';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <ProtectedLayout>
          {children}
        </ProtectedLayout>
      </AuthProvider>
    </QueryProvider>
  );
}
