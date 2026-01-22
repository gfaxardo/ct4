/**
 * Filters - Componente moderno para filtros
 */

'use client';

interface FilterOption {
  value: string;
  label: string;
}

interface FilterField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'select' | 'checkbox';
  options?: FilterOption[];
  placeholder?: string;
}

interface FiltersProps {
  fields: FilterField[];
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  onReset?: () => void;
  className?: string;
}

export default function Filters({
  fields,
  values,
  onChange,
  onReset,
  className = '',
}: FiltersProps) {
  const handleChange = (name: string, value: unknown) => {
    onChange({ ...values, [name]: value });
  };

  return (
    <div className={`card p-5 mb-6 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {fields.map((field) => (
          <div key={field.name}>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">
              {field.label}
            </label>
            {field.type === 'text' && (
              <input
                type="text"
                value={(values[field.name] as string) || ''}
                onChange={(e) => handleChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                className="input"
              />
            )}
            {field.type === 'number' && (
              <input
                type="number"
                value={(values[field.name] as string) || ''}
                onChange={(e) => handleChange(field.name, e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder={field.placeholder}
                className="input"
              />
            )}
            {field.type === 'date' && (
              <input
                type="date"
                value={(values[field.name] as string) || ''}
                onChange={(e) => handleChange(field.name, e.target.value || undefined)}
                className="input"
              />
            )}
            {field.type === 'select' && (
              <select
                value={(values[field.name] as string) || ''}
                onChange={(e) => handleChange(field.name, e.target.value || undefined)}
                className="select"
              >
                {/* Solo agregar opción default si las opciones no incluyen una con value="" */}
                {!field.options?.some(opt => opt.value === '') && (
                  <option value="">Todos</option>
                )}
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
            {field.type === 'checkbox' && (
              <div className="flex items-center gap-2 mt-2">
                <input
                  type="checkbox"
                  checked={values[field.name] === true}
                  onChange={(e) => handleChange(field.name, e.target.checked ? true : undefined)}
                  className="h-4 w-4 rounded border-slate-300 text-[#ef0000] focus:ring-[#ef0000]"
                />
                <label className="text-sm text-slate-700">{field.label}</label>
              </div>
            )}
          </div>
        ))}
      </div>
      {onReset && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <button
            onClick={onReset}
            className="btn btn-secondary text-sm"
          >
            Limpiar Filtros
          </button>
        </div>
      )}
    </div>
  );
}
