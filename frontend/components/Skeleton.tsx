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
