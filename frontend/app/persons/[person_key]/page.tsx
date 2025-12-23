'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { getPerson, PersonDetail } from '@/lib/api'
import { formatDate, formatConfidenceLevel, getConfidenceColor } from '@/lib/utils'

export default function PersonDetailPage() {
  const params = useParams()
  const personKey = params.person_key as string
  const [personDetail, setPersonDetail] = useState<PersonDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPerson() {
      try {
        const data = await getPerson(personKey)
        setPersonDetail(data)
      } catch (error) {
        console.error('Error cargando persona:', error)
      } finally {
        setLoading(false)
      }
    }
    loadPerson()
  }, [personKey])

  if (loading) {
    return <div className="text-center py-12">Cargando...</div>
  }

  if (!personDetail) {
    return <div className="text-center py-12">Persona no encontrada</div>
  }

  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Detalle de Persona</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Información Canónica</h2>
          {personDetail.has_driver_conversion && (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
              ✓ Convertido a Driver
            </span>
          )}
        </div>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Person Key</dt>
            <dd className="mt-1 text-sm font-mono">{personDetail.person.person_key}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Nivel de Confianza</dt>
            <dd className="mt-1">
              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getConfidenceColor(personDetail.person.confidence_level)}`}>
                {formatConfidenceLevel(personDetail.person.confidence_level)}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Nombre Completo</dt>
            <dd className="mt-1 text-sm">{personDetail.person.primary_full_name || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Teléfono</dt>
            <dd className="mt-1 text-sm">{personDetail.person.primary_phone || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Documento</dt>
            <dd className="mt-1 text-sm">{personDetail.person.primary_document || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Licencia</dt>
            <dd className="mt-1 text-sm">{personDetail.person.primary_license || '-'}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Creado</dt>
            <dd className="mt-1 text-sm">{formatDate(personDetail.person.created_at)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Actualizado</dt>
            <dd className="mt-1 text-sm">{formatDate(personDetail.person.updated_at)}</dd>
          </div>
        </dl>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Vínculos ({personDetail.links.length})</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fuente</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">PK</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Regla</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confianza</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha Snapshot</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evidencia</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {personDetail.links.map((link) => (
                <tr key={link.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{link.source_table}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{link.source_pk}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{link.match_rule}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{link.match_score}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getConfidenceColor(link.confidence_level)}`}>
                      {formatConfidenceLevel(link.confidence_level)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(link.snapshot_date)}</td>
                  <td className="px-6 py-4 text-sm">
                    {link.evidence && (
                      <details>
                        <summary className="cursor-pointer text-blue-600 hover:text-blue-800">Ver</summary>
                        <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                          {JSON.stringify(link.evidence, null, 2)}
                        </pre>
                      </details>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}



