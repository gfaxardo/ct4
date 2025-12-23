'use client'

interface WeeklyFiltersProps {
  viewMode: 'summary' | 'weekly'
  onViewModeChange: (mode: 'summary' | 'weekly') => void
  availableWeeks?: string[]
  selectedWeek: string
  selectedSource: string
  onWeekChange: (week: string) => void
  onSourceChange: (source: string) => void
  onApplyFilters: () => void
  loading?: boolean
  weeklyLabel?: string
}

export default function WeeklyFilters({
  viewMode,
  onViewModeChange,
  availableWeeks,
  selectedWeek,
  selectedSource,
  onWeekChange,
  onSourceChange,
  onApplyFilters,
  loading,
  weeklyLabel = 'Semanal (evento)'
}: WeeklyFiltersProps) {
  return (
    <div className="mb-6 p-4 bg-gray-50 rounded-lg">
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium mb-1">Vista</label>
          <div className="flex gap-2">
            <button
              onClick={() => onViewModeChange('summary')}
              className={`px-4 py-2 rounded-md text-sm ${
                viewMode === 'summary'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Resumen
            </button>
            <button
              onClick={() => onViewModeChange('weekly')}
              className={`px-4 py-2 rounded-md text-sm ${
                viewMode === 'weekly'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {weeklyLabel}
            </button>
          </div>
        </div>
        {viewMode === 'weekly' && (
          <>
            <div>
              <label className="block text-sm font-medium mb-1">Semana del evento</label>
              <select
                value={selectedWeek}
                onChange={(e) => onWeekChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">Todas</option>
                {availableWeeks?.map((week) => (
                  <option key={week} value={week}>
                    {week}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fuente</label>
              <select
                value={selectedSource}
                onChange={(e) => onSourceChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="all">Todas</option>
                <option value="module_ct_cabinet_leads">Cabinet</option>
                <option value="module_ct_scouting_daily">Scouting</option>
              </select>
            </div>
            <button
              onClick={onApplyFilters}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              {loading ? 'Cargando...' : 'Aplicar Filtros'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}



