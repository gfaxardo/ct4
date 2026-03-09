"""
API v1 — Agregación de routers por dominio.

Todos los endpoints están bajo el prefijo /api/v1 (definido en main.py).
Mapa completo: backend/docs/API_ORGANIZATION.md
Arquitectura: docs/ARCHITECTURE.md
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    attribution,
    cabinet_leads,
    dashboard,
    identity,
    identity_audit,
    liquidation,
    ops,
    ops_payments,
    scouts,
    yango_payments,
)
from app.api.v1.payments import router as payments_router

router = APIRouter()

# --- Auth ---
router.include_router(auth.router, prefix="/auth", tags=["auth"])

# --- Identidad (personas, unmatched, runs, orphans, métricas) ---
router.include_router(identity.router, prefix="/identity", tags=["identity"])
router.include_router(identity_audit.router, prefix="/identity", tags=["identity-audit"])

# --- Operaciones (health, alertas, ingest, MVs, identity-gaps) ---
router.include_router(ops.router, prefix="/ops", tags=["ops"])
# Ops payments también bajo /ops/payments (cabinet-financial-14d, limbo, claims-gap, etc.)
# Se monta en app.api.v1.ops con prefix="/payments"

# --- Atribución (eventos, ledger) ---
router.include_router(attribution.router, prefix="/attribution", tags=["attribution"])

# --- Pagos ---
# Core: elegibilidad, driver-matrix presentación
router.include_router(payments_router, prefix="/payments", tags=["payments"])
# Cobranza Yango + cabinet financial: scout-attribution-metrics, weekly-kpis, cabinet-financial-14d, limbo, claims-gap
router.include_router(ops_payments.router, prefix="/payments", tags=["ops-payments"])

# --- Dashboard (resúmenes scout y Yango) ---
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# --- Liquidación scouts ---
router.include_router(liquidation.router, prefix="/liquidation", tags=["liquidation"])

# --- Yango (reconciliación, cabinet claims, collection-with-scout) ---
router.include_router(yango_payments.router, prefix="/yango", tags=["yango"])

# --- Cabinet leads (upload, auto-processor, diagnósticos) ---
router.include_router(cabinet_leads.router, prefix="/cabinet-leads", tags=["cabinet-leads"])

# --- Scouts (atribución, conflictos, backlog, liquidación base) ---
router.include_router(scouts.router, prefix="/scouts", tags=["scouts"])

