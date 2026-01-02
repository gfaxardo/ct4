/**
 * StatCard - Componente para mostrar estadísticas
 */

import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number | ReactNode;
  subtitle?: string;
  className?: string;
}

export default function StatCard({ title, value, subtitle, className = '' }: StatCardProps) {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      <h2 className="text-sm font-medium text-gray-500 mb-2">{title}</h2>
      <div className="text-3xl font-bold">{value}</div>
      {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}



