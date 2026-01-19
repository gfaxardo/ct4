/**
 * Layout protegido con sidebar y topbar
 * Solo se muestra si el usuario está autenticado
 */

'use client';

import { useAuth } from '@/lib/auth';
import { usePathname } from 'next/navigation';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const pathname = usePathname();

  // No mostrar layout en login
  if (pathname === '/login') {
    return <>{children}</>;
  }

  // Loading
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-slate-600">Cargando...</p>
        </div>
      </div>
    );
  }

  // No autenticado - el AuthContext se encargará de redirigir
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin w-10 h-10 border-4 border-cyan-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-slate-600">Redirigiendo al login...</p>
        </div>
      </div>
    );
  }

  // Autenticado - mostrar layout completo
  return (
    <>
      <Sidebar />
      <Topbar />
      <main className="ml-64 mt-16 min-h-[calc(100vh-4rem)]">
        <div className="p-6 animate-fade-in">
          {children}
        </div>
      </main>
    </>
  );
}
