/**
 * DataTable - Tabla de datos con diseño moderno
 * 
 * REGLA: Solo renderiza datos del backend, NO recalcula nada
 */

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
  compact?: boolean;
  striped?: boolean;
}

function LoadingSkeleton({ columns }: { columns: number }) {
  return (
    <div className="animate-pulse">
      {[...Array(5)].map((_, rowIdx) => (
        <div key={rowIdx} className="flex items-center gap-4 px-5 py-4 border-b border-slate-100">
          {[...Array(columns)].map((_, colIdx) => (
            <div 
              key={colIdx} 
              className="h-4 bg-slate-200 rounded flex-1"
              style={{ maxWidth: colIdx === 0 ? '200px' : '120px' }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function EmptyState({ message, icon }: { message: string; icon?: React.ReactNode }) {
  return (
    <div className="py-16 px-6 text-center">
      <div className="mx-auto w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        {icon || (
          <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        )}
      </div>
      <p className="text-base font-medium text-slate-900 mb-1">Sin datos</p>
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

export default function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No hay datos disponibles',
  emptyIcon,
  onRowClick,
  className = '',
  compact = false,
  striped = false,
}: DataTableProps<T>) {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-slate-200/60 shadow-card overflow-hidden ${className}`}>
        <LoadingSkeleton columns={columns.length} />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={`bg-white rounded-xl border border-slate-200/60 shadow-card overflow-hidden ${className}`}>
        <EmptyState message={emptyMessage} icon={emptyIcon} />
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-slate-200/60 shadow-card overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200/60">
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={`
                    ${compact ? 'px-4 py-3' : 'px-5 py-3.5'}
                    text-xs font-semibold text-slate-500 uppercase tracking-wider
                    ${alignClasses[col.align || 'left']}
                    ${col.className || ''}
                  `}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                onClick={() => onRowClick?.(row)}
                className={`
                  transition-colors duration-150
                  ${onRowClick ? 'cursor-pointer' : ''}
                  ${striped && rowIdx % 2 === 1 ? 'bg-slate-50/30' : ''}
                  hover:bg-slate-50/80
                  group
                `}
              >
                {columns.map((col, colIdx) => (
                  <td
                    key={colIdx}
                    className={`
                      ${compact ? 'px-4 py-3' : 'px-5 py-4'}
                      text-sm text-slate-700
                      ${alignClasses[col.align || 'left']}
                      ${col.className || ''}
                    `}
                  >
                    {col.render
                      ? col.render(row)
                      : typeof col.key === 'string'
                      ? (row[col.key] as React.ReactNode) ?? <span className="text-slate-300">—</span>
                      : (row[col.key as keyof T] as React.ReactNode) ?? <span className="text-slate-300">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
