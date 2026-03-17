/**
 * Person Detail - Página servidor para ruta dinámica [person_key]
 * Exporta generateStaticParams requerido por output: 'export'.
 */

import PersonDetailClient from './PersonDetailClient';

export function generateStaticParams(): { person_key: string }[] {
  // Con output: 'export' se requiere al menos un param; el resto se sirve por client-side.
  return [{ person_key: '_' }];
}

export default function PersonDetailPage() {
  return <PersonDetailClient />;
}
