/**
 * PaymentsLegend - Componente global de guía/leyenda para páginas de pagos
 */

'use client';

import { useState } from 'react';
import Badge from '@/components/Badge';

export default function PaymentsLegend() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
      >
        <span>ℹ️</span>
        <span>Guía de Pagos</span>
        <span className={isOpen ? 'transform rotate-180' : ''}>▼</span>
      </button>

      {isOpen && (
        <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
          <h3 className="font-semibold text-gray-900 mb-3">Guía de Pagos</h3>
          
          <div className="space-y-3">
            <div>
              <p className="font-medium text-gray-800 mb-1">¿Qué es esta pantalla?</p>
              <p className="text-gray-700">
                Esta pantalla muestra datos canónicos de vistas ops. <strong>No recalcula reglas</strong>; 
                muestra información consolidada de pagos, claims, reconciliación y cobranza.
              </p>
            </div>

            <div>
              <p className="font-medium text-gray-800 mb-2">Estados de Pago Yango:</p>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="success">PAID</Badge>
                  <span className="text-gray-700">Pagado correctamente</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="warning">UNPAID / PENDING</Badge>
                  <span className="text-gray-700">Pendiente de pago</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="error">PENDING_EXPIRED / expired+unpaid</Badge>
                  <span className="text-gray-700">Vencido y sin pagar</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="warning">PAID_MISAPPLIED</Badge>
                  <span className="text-gray-700">Pagado pero a otro milestone</span>
                </div>
              </div>
            </div>

            <div>
              <p className="font-medium text-gray-800 mb-2">Estados de Ventana:</p>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="info">in_window</Badge>
                  <span className="text-gray-700">Dentro de la ventana de pago</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="error">expired</Badge>
                  <span className="text-gray-700">Fuera de la ventana de pago</span>
                </div>
              </div>
            </div>

            <div>
              <p className="font-medium text-gray-800 mb-1">Overdue (Vencido):</p>
              <p className="text-gray-700">
                Muestra <span className="text-red-600 font-semibold">⚠ Xd</span> cuando hay días vencidos (overdue_days &gt; 0)
              </p>
            </div>

            <div className="pt-2 border-t border-blue-200">
              <p className="text-xs text-gray-600">
                <strong>Nota:</strong> Esta pantalla no recalcula reglas; muestra data canónica de vistas ops.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}





