/**
 * MilestoneCell - Componente para mostrar información de un milestone (M1/M5/M25)
 */

import Badge from '@/components/Badge';

interface MilestoneCellProps {
  achieved_flag: boolean | null;
  achieved_date: string | null;
  expected_amount_yango: number | null;
  yango_payment_status: string | null;
  window_status: string | null;
  overdue_days: number | null;
}

export default function MilestoneCell({
  achieved_flag,
  achieved_date,
  expected_amount_yango,
  yango_payment_status,
  window_status,
  overdue_days,
}: MilestoneCellProps) {
  // Determinar variant del badge de payment status
  const getPaymentStatusVariant = (status: string | null): 'default' | 'success' | 'warning' | 'error' | 'info' => {
    if (!status) return 'default';
    if (status === 'PAID') return 'success';
    if (status === 'PAID_MISAPPLIED') return 'warning';
    if (status === 'UNPAID' || status === 'PENDING') return 'error';
    return 'default';
  };

  // Determinar variant del badge de window status
  const getWindowStatusVariant = (status: string | null): 'default' | 'success' | 'warning' | 'error' | 'info' => {
    if (!status) return 'default';
    if (status === 'in_window') return 'info';
    if (status === 'expired') return 'error';
    return 'default';
  };

  return (
    <div className="p-2 border border-gray-200 rounded-lg bg-gray-50 min-w-[200px]">
      {/* Achieved flag + date */}
      <div className="mb-2">
        {achieved_flag ? (
          <div className="flex items-center gap-1 text-sm">
            <span>✅</span>
            <span className="font-medium">Alcanzado</span>
            {achieved_date && (
              <span className="text-xs text-gray-500">
                {new Date(achieved_date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' })}
              </span>
            )}
          </div>
        ) : (
          <div className="text-sm text-gray-400">—</div>
        )}
      </div>

      {/* Payment status badge */}
      {yango_payment_status && (
        <div className="mb-1">
          <Badge variant={getPaymentStatusVariant(yango_payment_status)}>
            {yango_payment_status}
          </Badge>
        </div>
      )}

      {/* Window status badge */}
      {window_status && (
        <div className="mb-1">
          <Badge variant={getWindowStatusVariant(window_status)}>
            {window_status === 'in_window' ? 'En ventana' : window_status === 'expired' ? 'Vencido' : window_status}
          </Badge>
        </div>
      )}

      {/* Overdue days */}
      {overdue_days !== null && overdue_days > 0 && (
        <div className="mb-1 text-sm text-red-600 font-semibold">
          ⚠ {overdue_days}d
        </div>
      )}

      {/* Expected amount */}
      {expected_amount_yango !== null && (
        <div className="text-sm font-medium text-gray-700">
          S/ {Number(expected_amount_yango).toFixed(2)}
        </div>
      )}
    </div>
  );
}
