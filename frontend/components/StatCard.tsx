/**
 * StatCard - Tarjeta de estadísticas con diseño moderno
 */

import { ReactNode } from 'react';

interface StatCardProps {
  title: string;
  value: string | number | ReactNode;
  subtitle?: string;
  className?: string;
  variant?: 'default' | 'warning' | 'success' | 'error' | 'info' | 'brand';
  icon?: ReactNode;
  trend?: {
    value: number;
    label?: string;
  };
}

const variantConfig = {
  default: {
    bg: 'bg-white',
    border: 'border-slate-200/60',
    iconBg: 'bg-slate-100',
    iconText: 'text-slate-600',
    labelText: 'text-slate-500',
    subtitleText: 'text-slate-400',
    accentColor: 'from-slate-400 to-slate-500',
  },
  brand: {
    bg: 'bg-white',
    border: 'border-cyan-200/60',
    iconBg: 'bg-cyan-50',
    iconText: 'text-[#ef0000]',
    labelText: 'text-[#ef0000]',
    subtitleText: 'text-[#ef0000]',
    accentColor: 'from-[#ef0000] to-[#ef0000]',
  },
  success: {
    bg: 'bg-white',
    border: 'border-emerald-200/60',
    iconBg: 'bg-emerald-50',
    iconText: 'text-emerald-600',
    labelText: 'text-emerald-600',
    subtitleText: 'text-emerald-500',
    accentColor: 'from-emerald-400 to-emerald-500',
  },
  warning: {
    bg: 'bg-white',
    border: 'border-amber-200/60',
    iconBg: 'bg-amber-50',
    iconText: 'text-amber-600',
    labelText: 'text-amber-600',
    subtitleText: 'text-amber-500',
    accentColor: 'from-amber-400 to-amber-500',
  },
  error: {
    bg: 'bg-white',
    border: 'border-rose-200/60',
    iconBg: 'bg-rose-50',
    iconText: 'text-rose-600',
    labelText: 'text-rose-600',
    subtitleText: 'text-rose-500',
    accentColor: 'from-rose-400 to-rose-500',
  },
  info: {
    bg: 'bg-white',
    border: 'border-blue-200/60',
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    labelText: 'text-blue-600',
    subtitleText: 'text-blue-500',
    accentColor: 'from-blue-400 to-blue-500',
  },
};

export default function StatCard({ 
  title, 
  value, 
  subtitle, 
  className = '', 
  variant = 'default',
  icon,
  trend,
}: StatCardProps) {
  const config = variantConfig[variant];

  return (
    <div className={`
      relative overflow-hidden
      ${config.bg} ${config.border}
      rounded-xl border shadow-card
      p-5
      transition-all duration-300 ease-out
      hover:shadow-card-hover hover:border-opacity-80
      group
      ${className}
    `}>
      {/* Accent line */}
      <div className={`
        absolute top-0 left-0 right-0 h-1
        bg-gradient-to-r ${config.accentColor}
        opacity-0 group-hover:opacity-100
        transition-opacity duration-300
      `} />
      
      {/* Background decoration */}
      <div className={`
        absolute -right-4 -top-4 w-20 h-20 rounded-full
        bg-gradient-to-br ${config.accentColor}
        opacity-5
      `} />

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <span className={`text-sm font-medium ${config.labelText}`}>
            {title}
          </span>
          {icon && (
            <div className={`
              p-2 rounded-lg ${config.iconBg} ${config.iconText}
            `}>
              {icon}
            </div>
          )}
        </div>

        {/* Value */}
        <div className="text-3xl font-bold text-slate-900 tracking-tight mb-1">
          {value}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          {subtitle && (
            <p className={`text-sm ${config.subtitleText}`}>
              {subtitle}
            </p>
          )}
          {trend && (
            <div className={`
              flex items-center gap-1 text-sm font-medium
              ${trend.value >= 0 ? 'text-emerald-600' : 'text-rose-600'}
            `}>
              {trend.value >= 0 ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                </svg>
              )}
              <span>{Math.abs(trend.value)}%</span>
              {trend.label && <span className="text-slate-400 font-normal">{trend.label}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
