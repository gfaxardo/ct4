/**
 * Badge - Componente para mostrar estados/etiquetas con diseño moderno
 */

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'purple' | 'brand';
  size?: 'sm' | 'md' | 'lg';
  dot?: boolean;
  className?: string;
}

const variants = {
  default: 'bg-slate-100 text-slate-700 ring-slate-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-700 ring-amber-200',
  error: 'bg-rose-50 text-rose-700 ring-rose-200',
  info: 'bg-cyan-50 text-cyan-700 ring-cyan-200',
  purple: 'bg-violet-50 text-violet-700 ring-violet-200',
  brand: 'bg-gradient-to-r from-cyan-500 to-emerald-500 text-white ring-cyan-300',
};

const sizes = {
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-2.5 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

const dotColors = {
  default: 'bg-slate-400',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  error: 'bg-rose-500',
  info: 'bg-cyan-500',
  purple: 'bg-violet-500',
  brand: 'bg-white',
};

export default function Badge({ 
  children, 
  variant = 'default', 
  size = 'md',
  dot = false,
  className = '' 
}: BadgeProps) {
  const variantClass = variants[variant] || variants.default;
  const sizeClass = sizes[size];
  const dotColor = dotColors[variant] || dotColors.default;

  return (
    <span className={`
      inline-flex items-center gap-1.5
      font-semibold rounded-full
      ring-1 ring-inset
      transition-colors duration-200
      ${variantClass} 
      ${sizeClass}
      ${className}
    `}>
      {dot && (
        <span className={`
          w-1.5 h-1.5 rounded-full ${dotColor}
          ${variant === 'brand' ? '' : 'animate-pulse'}
        `} />
      )}
      {children}
    </span>
  );
}
