/**
 * Filters - Componente genérico para filtros
 */

'use client';

import { useState } from 'react';

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
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
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
  const handleChange = (name: string, value: any) => {
    onChange({ ...values, [name]: value });
  };

  return (
    <div className={`bg-white rounded-lg shadow p-4 mb-6 ${className}`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {fields.map((field) => (
          <div key={field.name}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {field.label}
            </label>
            {field.type === 'text' && (
              <input
                type="text"
                value={values[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            {field.type === 'number' && (
              <input
                type="number"
                value={values[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder={field.placeholder}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            {field.type === 'date' && (
              <input
                type="date"
                value={values[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            {field.type === 'select' && (
              <select
                value={values[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value || undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                {field.options?.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
            {field.type === 'checkbox' && (
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={values[field.name] === true}
                  onChange={(e) => handleChange(field.name, e.target.checked ? true : undefined)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label className="ml-2 text-sm text-gray-700">{field.label}</label>
              </div>
            )}
          </div>
        ))}
      </div>
      {onReset && (
        <div className="mt-4">
          <button
            onClick={onReset}
            className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Limpiar Filtros
          </button>
        </div>
      )}
    </div>
  );
}






