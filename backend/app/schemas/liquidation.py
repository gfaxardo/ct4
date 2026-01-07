from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal


class ScoutMarkPaidRequest(BaseModel):
    scout_id: int
    cutoff_date: date
    paid_by: str
    payment_ref: str
    notes: Optional[str] = None


class ScoutPreviewResponse(BaseModel):
    preview_items: int
    preview_amount: Decimal


class ScoutMarkPaidResponse(BaseModel):
    inserted_items: int
    inserted_amount: Decimal
    preview_items: int
    preview_amount: Decimal
    message: str



























