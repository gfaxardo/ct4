'use client'

import { useEffect, useState } from 'react'
import { listPersons, IdentityRegistry } from '@/lib/api'
import { formatDate, formatConfidenceLevel, getConfidenceColor } from '@/lib/utils'
import Link from 'next/link'

export default function PersonsPage() {
  const [persons, setPersons] = useState<IdentityRegistry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [confidenceFilter, setConfidenceFilter] = useState<string>('')

  useEffect(() => {
    loadPersons()
  }, [search, confidenceFilter])

  async function loadPersons() {
    setLoading(true)
    try {
      const params: any = { limit: 100 }
      if (search) {
        if (search.match(/^\d/)) {
          params.phone = search
        } else {
          params.name = search
        }
      }
      if (confidenceFilter) {
        params.confidence_level = confidenceFilter
      }
      const data = await listPersons(params)
      setPersons(data)
    } catch (error) {
      console.error('Error cargando personas:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Personas</h1>

      <div className="bg-white rounded-lg shadow mb-6 p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Buscar por teléfono o nombre..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-4 py-2 border rounded-md"
          />
          <select
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="">Todos los niveles</option>
            <option value="HIGH">Alto</option>
            <option value="MEDIUM">Medio</option>
            <option value="LOW">Bajo</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12">Cargando...</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Person Key</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Teléfono</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confianza</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Creado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {persons.map((person) => (
                <tr key={person.person_key} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                    {person.person_key.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{person.primary_full_name || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{person.primary_phone || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getConfidenceColor(person.confidence_level)}`}>
                      {formatConfidenceLevel(person.confidence_level)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(person.created_at)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Link href={`/persons/${person.person_key}`} className="text-blue-600 hover:text-blue-800">
                      Ver detalle →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {persons.length === 0 && (
            <div className="text-center py-12 text-gray-500">No se encontraron personas</div>
          )}
        </div>
      )}
    </div>
  )
}










