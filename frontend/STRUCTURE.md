# Estructura del frontend (CT4)

## Carpetas principales

```
frontend/
├── app/                    # Rutas Next.js (App Router)
│   ├── (auth)/             # login, layout login
│   ├── pagos/              # Todo lo de pagos: elegibilidad, cobranza, claims, driver-matrix, etc.
│   ├── scouts/             # Atribución, liquidaciones, conflictos, backlog
│   ├── ops/                # Health, alerts, data-health
│   ├── persons/            # Personas, detalle por person_key
│   ├── cabinet-leads/      # Upload y procesamiento de leads
│   ├── dashboard/          # Resumen general
│   ├── runs/               # Auditoría / runs de identidad
│   ├── unmatched/          # Leads sin match
│   ├── liquidaciones/      # Vista liquidaciones
│   ├── layout.tsx
│   ├── page.tsx            # Redirige a dashboard o login
│   └── providers.tsx
│
├── components/
│   ├── ui/                 # Componentes reutilizables sin lógica de dominio
│   │   ├── Badge.tsx
│   │   ├── DataTable.tsx
│   │   ├── Filters.tsx
│   │   ├── Modal.tsx
│   │   ├── Pagination.tsx
│   │   ├── Skeleton.tsx
│   │   ├── StatCard.tsx
│   │   ├── Tabs.tsx
│   │   └── Topbar.tsx
│   ├── layout/             # Shell de la app (sidebar, layout protegido)
│   │   ├── ProtectedLayout.tsx
│   │   └── Sidebar.tsx
│   ├── pagos/              # Componentes de dominio Pagos (cabinet, milestones, leyenda)
│   │   ├── index.ts
│   │   ├── CabinetClaimsGapSection.tsx
│   │   ├── CabinetLimboSection.tsx
│   │   ├── CompactMilestoneCell.tsx
│   │   ├── MilestoneCell.tsx
│   │   └── PaymentsLegend.tsx
│   └── ops/                # Componentes de dominio Ops (health panels)
│       ├── HealthChecksPanel.tsx
│       ├── HealthGlobalStatus.tsx
│       ├── IdentitySystemHealthPanel.tsx
│       ├── MvHealthPanel.tsx
│       └── RawDataHealthPanel.tsx
│
└── lib/
    ├── api/                # Cliente API
    │   ├── client.ts       # fetchApi, ApiError, API_BASE_URL
    │   └── (api.ts en raíz es el barrel con todas las funciones)
    ├── api.ts              # Punto de entrada único: todas las getXxx() y tipos usados por la app
    ├── endpoints.ts        # Constantes de rutas y builders
    ├── types.ts            # Tipos compartidos (re-exporta desde api donde aplica)
    ├── format.ts           # formatDate, formatDateTime, formatCurrency
    ├── auth.tsx            # Contexto de autenticación
    ├── query-client.tsx    # React Query provider
    └── hooks/              # Hooks por dominio
        ├── use-dashboard.ts
        ├── use-cobranza-yango.ts
        └── use-yango-reconciliation.ts
```

## Convenciones

- **Rutas (`app/`)**: Una carpeta por dominio (pagos, scouts, ops, persons…). Cada página en `page.tsx`.
- **Componentes**:
  - UI: `@/components/Nombre` o agrupados en `@/components/ui` (ver `components/ui/index.ts`).
  - Layout: `@/components/ProtectedLayout`, `@/components/Sidebar` o `@/components/layout`.
  - Pagos: `@/components/pagos/Nombre` o `import { X } from '@/components/pagos'`.
  - Ops: `@/components/ops/Nombre`.
- **API**: Siempre usar `@/lib/api` para llamadas; no instanciar fetch a mano.
- **Tipos**: Preferir tipos de `@/lib/types` o los que exporta `@/lib/api`.
- **Formato**: Usar `@/lib/format` para fechas y moneda.

## Navegación (Sidebar)

La navegación está definida en `components/layout/Sidebar.tsx` (`navItems`). Añadir o quitar ítems ahí.
