/**
 * Cobranza Yango con Scout - Claims de cobranza con información de scout
 * 
 * NOTA: Esta ruta ha sido redirigida a /pagos/cobranza-yango (vista principal)
 * Se mantiene este archivo temporalmente para redirección automática.
 */

'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ScoutCobranzaYangoPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirigir automáticamente a la vista principal de Cobranza Yango
    router.replace('/pagos/cobranza-yango');
  }, [router]);

  return (
    <div className="px-4 py-6">
      <div className="text-center py-12">
        <p className="text-gray-600">Redirigiendo a Cobranza Yango...</p>
      </div>
    </div>
  );
}

// Código legacy comentado - mantiene historial pero no se ejecuta
/*
import { useState } from 'react';
import { getYangoCollectionWithScout, ApiError } from '@/lib/api';
import type { YangoCollectionWithScoutResponse } from '@/lib/types';
import Badge from '@/components/Badge';
import Link from 'next/link';

export default function ScoutCobranzaYangoPageLegacy() {
  const [data, setData] = useState<YangoCollectionWithScoutResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    scout_missing_only: false,
    conflicts_only: false,
  });

  // ... resto del código legacy comentado para mantener historial
}
*/

