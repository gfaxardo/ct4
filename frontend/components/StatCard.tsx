/**
 * StatCard - Componente para mostrar estadísticas
 */

import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number | ReactNode;
  subtitle?: string;
  className?: string;
  variant?: 'default' | 'warning' | 'success' | 'error' | 'info';
}

export default function StatCard({ title, value, subtitle, className = '', variant = 'default' }: StatCardProps) {
  const variantStyles = {
    default: 'bg-white border-gray-200',
    warning: 'bg-yellow-50 border-yellow-200',
    success: 'bg-green-50 border-green-200',
    error: 'bg-red-50 border-red-200',
    info: 'bg-blue-50 border-blue-200',
  };

  const variantTextStyles = {
    default: 'text-gray-500',
    warning: 'text-yellow-700',
    success: 'text-green-700',
    error: 'text-red-700',
    info: 'text-blue-700',
  };

  return (
    <div className={`rounded-lg shadow border p-6 ${variantStyles[variant]} ${className}`}>
      <h2 className={`text-sm font-medium mb-2 ${variantTextStyles[variant]}`}>{title}</h2>
      <div className="text-3xl font-bold text-gray-900">{value}</div>
      {subtitle && <p className={`text-sm mt-1 ${variant === 'default' ? 'text-gray-400' : variantTextStyles[variant]}`}>{subtitle}</p>}
    </div>
  );
}



