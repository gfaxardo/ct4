from fastapi import APIRouter
from app.api.v1 import identity, ops, attribution

router = APIRouter()

router.include_router(identity.router, prefix="/identity", tags=["identity"])
router.include_router(ops.router, prefix="/ops", tags=["ops"])
router.include_router(attribution.router, prefix="/attribution", tags=["attribution"])





