"""
Lógica de negocio para endpoints de ops payments.

El controller (api/v1/ops_payments.py) solo registra rutas y delega aquí.
No debe haber lógica de negocio en el controller.
"""

from app.services.ops_payments.driver_matrix import get_driver_matrix, OrderByOption
from app.services.ops_payments.cabinet_financial import (
    get_funnel_gap_metrics,
    get_kpi_red_recovery_metrics,
    get_claims_audit_summary,
)

__all__ = [
    "get_driver_matrix",
    "OrderByOption",
    "get_funnel_gap_metrics",
    "get_kpi_red_recovery_metrics",
    "get_claims_audit_summary",
]
