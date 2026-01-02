/**
 * Claims - PENDING
 * Basado en FRONTEND_UI_BLUEPRINT_v1.md
 * 
 * Esta página está marcada como PENDING en el blueprint.
 * Requiere endpoint: GET /api/v1/payments/claims (o similar)
 */

export default function ClaimsPage() {
  return (
    <div className="px-4 py-6">
      <h1 className="text-3xl font-bold mb-6">Claims</h1>
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 text-yellow-800">Página PENDING</h2>
        <p className="text-yellow-700 mb-4">
          Esta página requiere un endpoint que aún no está disponible.
        </p>
        <div className="bg-white rounded p-4">
          <h3 className="font-semibold mb-2">Qué falta:</h3>
          <ul className="list-disc list-inside text-sm space-y-1">
            <li>Endpoint: GET /api/v1/payments/claims (o similar)</li>
            <li>Vista SQL sugerida: Necesita vista SQL para claims</li>
          </ul>
        </div>
        <div className="bg-white rounded p-4 mt-4">
          <h3 className="font-semibold mb-2">Qué se mostraría cuando exista:</h3>
          <ul className="list-disc list-inside text-sm space-y-1 text-gray-700">
            <li>Tabla de claims con columnas: claim_id, driver_id, amount, status, created_at</li>
            <li>Filtros por status, fecha, driver_id</li>
            <li>Drilldown a detalle de claim</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
