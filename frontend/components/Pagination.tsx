/**
 * Pagination - Componente moderno para paginación
 */

'use client';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
  className?: string;
}

export default function Pagination({
  total,
  limit,
  offset,
  onPageChange,
  className = '',
}: PaginationProps) {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const start = offset + 1;
  const end = Math.min(offset + limit, total);

  if (totalPages <= 1) return null;

  return (
    <div className={`
      flex items-center justify-between 
      px-5 py-4 mt-4
      bg-white border border-slate-200/60 rounded-xl shadow-card
      ${className}
    `}>
      {/* Mobile pagination */}
      <div className="flex-1 flex justify-between sm:hidden">
        <button
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={offset === 0}
          className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Anterior
        </button>
        <button
          onClick={() => onPageChange(offset + limit)}
          disabled={offset + limit >= total}
          className="btn btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Siguiente
        </button>
      </div>

      {/* Desktop pagination */}
      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-600">
            Mostrando <span className="font-semibold text-slate-900">{start.toLocaleString()}</span> a{' '}
            <span className="font-semibold text-slate-900">{end.toLocaleString()}</span> de{' '}
            <span className="font-semibold text-slate-900">{total.toLocaleString()}</span> resultados
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="
              inline-flex items-center gap-1 px-3 py-2 
              text-sm font-medium text-slate-700
              bg-white border border-slate-200 rounded-lg
              hover:bg-slate-50 hover:border-slate-300
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-200
            "
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Anterior
          </button>
          
          <span className="
            inline-flex items-center px-4 py-2
            text-sm font-medium text-slate-900
            bg-slate-50 border border-slate-200 rounded-lg
          ">
            {currentPage} / {totalPages}
          </span>
          
          <button
            onClick={() => onPageChange(offset + limit)}
            disabled={offset + limit >= total}
            className="
              inline-flex items-center gap-1 px-3 py-2 
              text-sm font-medium text-slate-700
              bg-white border border-slate-200 rounded-lg
              hover:bg-slate-50 hover:border-slate-300
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-200
            "
          >
            Siguiente
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
