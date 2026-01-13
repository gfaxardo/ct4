/**
 * CompactMilestoneCell - Componente compacto para mostrar información de milestone en 1 línea
 */

import Badge from '@/components/Badge';
import { useState } from 'react';

interface CompactMilestoneCellProps {
  achieved_flag: boolean | null;
  achieved_date: string | null;
  expected_amount_yango: number | null;
  yango_payment_status: string | null;
  window_status: string | null;
  overdue_days: number | null;
  label?: string;
  compact?: boolean;
}

export default function CompactMilestoneCell({
  achieved_flag,
  achieved_date,
  expected_amount_yango,
  yango_payment_status,
  window_status,
  overdue_days,
  label,
  compact = true,
}: CompactMilestoneCellProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Si achieved_flag es explícitamente false o null Y no hay ningún otro dato, mostrar "—"
  // PERO si achieved_flag es true, SIEMPRE mostrar el checkmark, incluso si los demás campos son null
  if (
    achieved_flag !== true &&
    achieved_date === null &&
    expected_amount_yango === null &&
    yango_payment_status === null &&
    window_status === null &&
    overdue_days === null
  ) {
    return <div className="text-center text-gray-400">—</div>;
  }

  // Determinar variant del badge de payment status
  const getPaymentStatusVariant = (
    status: string | null
  ): 'default' | 'success' | 'warning' | 'error' | 'info' => {
    if (!status) return 'default';
    if (status === 'PAID') return 'success';
    if (status === 'PAID_MISAPPLIED') return 'warning';
    if (status === 'UNPAID' || status === 'PENDING') return 'error';
    return 'default';
  };

  // Construir tooltip content
  const tooltipContent = [];
  if (achieved_flag && achieved_date) {
    const date = new Date(achieved_date).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
    tooltipContent.push(`Alcanzado ${date}`);
  }
  if (yango_payment_status) {
    tooltipContent.push(`Payment status: ${yango_payment_status}`);
  }
  if (window_status) {
    if (window_status === 'expired' && overdue_days !== null && overdue_days > 0) {
      tooltipContent.push(`Vencido (${overdue_days}d)`);
    } else if (window_status === 'in_window') {
      tooltipContent.push('En ventana de pago');
    }
  }
  if (expected_amount_yango !== null) {
    tooltipContent.push(`Expected: S/ ${Number(expected_amount_yango).toFixed(2)}`);
  }

  const tooltipText = tooltipContent.length > 0 ? tooltipContent.join('\n') : null;

  return (
    <div
      className="flex items-center gap-1 py-1 px-2 whitespace-nowrap relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Icono de alcanzado - BASADO SOLO EN achieved_flag */}
      <div className="flex-shrink-0">
        {achieved_flag === true ? (
          <span className="text-green-600 text-xs font-bold" title="✅ Alcanzado">✅</span>
        ) : (
          <span className="text-gray-400 text-xs">—</span>
        )}
      </div>

      {/* Badge de pago */}
      {yango_payment_status && (
        <Badge variant={getPaymentStatusVariant(yango_payment_status)} className="text-xs py-0 px-1">
          {yango_payment_status}
        </Badge>
      )}

      {/* Badge de vencido */}
      {window_status === 'expired' && overdue_days !== null && overdue_days > 0 && (
        <Badge variant="error" className="text-xs py-0 px-1">
          Venc. {overdue_days}d
        </Badge>
      )}

      {/* Monto a la derecha */}
      {expected_amount_yango !== null && (
        <div className="ml-auto text-xs font-medium text-gray-700">
          S/ {Number(expected_amount_yango).toFixed(2)}
        </div>
      )}

      {/* Tooltip */}
      {showTooltip && tooltipText && (
        <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg whitespace-pre-line max-w-xs">
          {tooltipText}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
            <div className="border-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>
      )}
    </div>
  );
}
