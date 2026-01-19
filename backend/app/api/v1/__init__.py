"""
API v1 router aggregation.

Combines all v1 endpoint routers into a single router for the main application.
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

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(identity.router, prefix="/identity", tags=["identity"])
router.include_router(identity_audit.router, prefix="/identity", tags=["identity-audit"])
router.include_router(ops.router, prefix="/ops", tags=["ops"])
router.include_router(attribution.router, prefix="/attribution", tags=["attribution"])
router.include_router(payments_router, prefix="/payments", tags=["payments"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(liquidation.router, prefix="/liquidation", tags=["liquidation"])
router.include_router(yango_payments.router, prefix="/yango", tags=["yango"])
router.include_router(cabinet_leads.router, prefix="/cabinet-leads", tags=["cabinet-leads"])
router.include_router(scouts.router, prefix="/scouts", tags=["scouts"])
router.include_router(ops_payments.router, prefix="/payments", tags=["ops-payments"])

