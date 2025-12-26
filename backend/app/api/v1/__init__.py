from fastapi import APIRouter
from app.api.v1 import identity, ops, attribution, dashboard, liquidation, yango_payments
from .payments import router as payments_router

router = APIRouter()

router.include_router(identity.router, prefix="/identity", tags=["identity"])
router.include_router(ops.router, prefix="/ops", tags=["ops"])
router.include_router(attribution.router, prefix="/attribution", tags=["attribution"])
router.include_router(payments_router, prefix="/payments", tags=["payments"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(liquidation.router, prefix="/liquidation", tags=["liquidation"])
router.include_router(yango_payments.router, prefix="/yango", tags=["yango"])





