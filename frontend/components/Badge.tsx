/**
 * Badge - Componente para mostrar estados/etiquetas
 */

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

export default function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-gray-100 text-gray-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
  };

  // Si el variant no existe, usar default
  const variantClass = variants[variant] || variants.default;

  return (
    <span className={`px-2 py-1 text-xs font-semibold rounded ${variantClass} ${className}`}>
      {children}
    </span>
  );
}






