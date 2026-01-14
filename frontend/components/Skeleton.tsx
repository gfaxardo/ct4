/**
 * Skeleton - Componente de carga con animación shimmer
 */

import { ReactNode } from 'react';

interface SkeletonProps {
  className?: string;
  children?: ReactNode;
}

// Skeleton base con animación shimmer
export default function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 bg-[length:200%_100%] rounded ${className}`}
      style={{ animation: 'shimmer 1.5s infinite' }}
    />
  );
}

// Skeleton para StatCards
export function StatCardSkeleton() {
  return (
    <div className="card p-5 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

// Skeleton para filas de tabla
export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-b border-slate-100">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-4 px-4">
          <Skeleton className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
}

// Skeleton para tabla completa
export function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="p-4 border-b border-slate-200">
        <Skeleton className="h-6 w-48" />
      </div>
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            {Array.from({ length: columns }).map((_, i) => (
              <th key={i} className="py-3 px-4 text-left">
                <Skeleton className="h-4 w-20" />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRowSkeleton key={i} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Skeleton para cards de métricas (grid)
export function MetricsGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-${Math.min(count, 4)} gap-4`}>
      {Array.from({ length: count }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  );
}

// Skeleton para sección completa con título
export function SectionSkeleton({ title }: { title?: string }) {
  return (
    <div className="card">
      <div className="card-header">
        {title ? (
          <h3 className="font-semibold text-slate-900">{title}</h3>
        ) : (
          <Skeleton className="h-6 w-40" />
        )}
      </div>
      <div className="card-body space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  );
}

// Skeleton para filtros
export function FiltersSkeleton() {
  return (
    <div className="card p-4 flex flex-wrap gap-4">
      <Skeleton className="h-10 w-32" />
      <Skeleton className="h-10 w-40" />
      <Skeleton className="h-10 w-28" />
      <Skeleton className="h-10 w-24" />
    </div>
  );
}

// Skeleton para gráfico/chart
export function ChartSkeleton() {
  return (
    <div className="card p-6">
      <Skeleton className="h-6 w-40 mb-4" />
      <div className="flex items-end justify-around h-48 gap-2">
        {[40, 70, 55, 90, 65, 80, 45].map((height, i) => (
          <Skeleton key={i} className="w-8" style={{ height: `${height}%` }} />
        ))}
      </div>
    </div>
  );
}

// Loading spinner centrado
export function LoadingSpinner({ size = 'md', text }: { size?: 'sm' | 'md' | 'lg'; text?: string }) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div
        className={`${sizeClasses[size]} border-cyan-500 border-t-transparent rounded-full animate-spin`}
      />
      {text && <p className="text-sm text-slate-500">{text}</p>}
    </div>
  );
}

// Page loading skeleton
export function PageLoadingSkeleton() {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      
      <MetricsGridSkeleton count={4} />
      
      <TableSkeleton rows={5} columns={6} />
    </div>
  );
}

// ============================================================================
// COMPONENTE ESTÁNDAR DE CARGA - Usar en TODAS las páginas
// ============================================================================

interface PageLoadingOverlayProps {
  title?: string;
  subtitle?: string;
}

/**
 * Overlay de carga estándar para usar en todas las páginas.
 * Muestra un spinner con texto descriptivo.
 * 
 * USO:
 * ```tsx
 * if (isLoading) {
 *   return <PageLoadingOverlay title="Dashboard" subtitle="Cargando métricas..." />;
 * }
 * ```
 */
export function PageLoadingOverlay({ 
  title = "Cargando", 
  subtitle = "Obteniendo datos del servidor..." 
}: PageLoadingOverlayProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        {/* Spinner */}
        <div className="relative w-16 h-16 mx-auto mb-6">
          <div className="absolute inset-0 border-4 border-slate-200 rounded-full" />
          <div className="absolute inset-0 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        </div>
        
        {/* Texto */}
        <h2 className="text-xl font-semibold text-slate-700 mb-2">
          {title}
        </h2>
        <p className="text-sm text-slate-500">
          {subtitle}
        </p>
        
        {/* Indicador de progreso visual */}
        <div className="mt-6 w-48 mx-auto h-1 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-cyan-400 to-cyan-600 rounded-full animate-pulse"
            style={{ 
              width: '60%',
              animation: 'loading-progress 1.5s ease-in-out infinite'
            }}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton de página estándar con estadísticas y tabla.
 * Usa animaciones suaves para mejor UX.
 */
export function StandardPageSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-8 bg-slate-200 rounded-lg w-56 mb-2 animate-pulse" />
          <div className="h-4 bg-slate-200 rounded w-80 animate-pulse" />
        </div>
        <div className="h-10 bg-slate-200 rounded-xl w-32 animate-pulse" />
      </div>

      {/* Stats cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div 
            key={i} 
            className="bg-gradient-to-br from-slate-100 to-slate-50 rounded-xl border border-slate-200/60 p-5 h-28"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-slate-200 rounded w-24" />
              <div className="h-8 bg-slate-200 rounded w-20" />
              <div className="h-3 bg-slate-200 rounded w-16" />
            </div>
          </div>
        ))}
      </div>

      {/* Filters skeleton */}
      <div className="bg-white rounded-xl border border-slate-200/60 p-4">
        <div className="grid grid-cols-5 gap-4 animate-pulse">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i}>
              <div className="h-3 bg-slate-200 rounded w-16 mb-2" />
              <div className="h-10 bg-slate-100 rounded-lg" />
            </div>
          ))}
        </div>
      </div>

      {/* Table skeleton */}
      <div className="bg-white rounded-xl border border-slate-200/60 overflow-hidden">
        <div className="p-4 border-b border-slate-200/60 bg-slate-50/50">
          <div className="flex gap-8 animate-pulse">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-4 bg-slate-200 rounded w-20" />
            ))}
          </div>
        </div>
        <div className="divide-y divide-slate-100">
          {[1, 2, 3, 4, 5].map((i) => (
            <div 
              key={i} 
              className="p-4 flex gap-8 animate-pulse"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="h-4 bg-slate-200 rounded w-32" />
              <div className="h-4 bg-slate-200 rounded w-16" />
              <div className="h-4 bg-slate-200 rounded w-20" />
              <div className="h-4 bg-slate-200 rounded w-24" />
              <div className="h-4 bg-slate-200 rounded w-24" />
              <div className="h-4 bg-slate-200 rounded w-16" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Spinner inline pequeño para usar dentro de botones o elementos pequeños.
 */
export function InlineSpinner({ className = '' }: { className?: string }) {
  return (
    <div className={`w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin ${className}`} />
  );
}
