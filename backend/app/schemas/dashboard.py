from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from decimal import Decimal


# Scout Summary Schemas
class ScoutTotals(BaseModel):
    payable_amount: Decimal
    payable_items: int
    payable_drivers: int
    payable_scouts: int
    blocked_amount: Decimal
    blocked_items: int


class ScoutByWeek(BaseModel):
    week_start_monday: date
    iso_year_week: str
    payable_amount: Decimal
    payable_items: int
    blocked_amount: Decimal
    blocked_items: int


class TopScout(BaseModel):
    acquisition_scout_id: Optional[int]
    acquisition_scout_name: Optional[str]
    amount: Decimal
    items: int
    drivers: int


class ScoutSummaryResponse(BaseModel):
    totals: ScoutTotals
    by_week: List[ScoutByWeek]
    top_scouts: List[TopScout]


# Scout Open Items Schema
class ScoutOpenItem(BaseModel):
    payment_item_key: str
    person_key: str
    lead_origin: Optional[str]
    scout_id: Optional[int]
    acquisition_scout_id: Optional[int]
    acquisition_scout_name: Optional[str]
    attribution_confidence: Optional[str]
    attribution_rule: Optional[str]
    milestone_type: Optional[str]
    milestone_value: Optional[int]
    payable_date: Optional[date]
    achieved_date: Optional[date]
    amount: Decimal
    currency: Optional[str]
    driver_id: Optional[str]


class ScoutOpenItemsResponse(BaseModel):
    items: List[ScoutOpenItem]
    total: int
    limit: int
    offset: int


# Yango Summary Schemas
class YangoTotals(BaseModel):
    receivable_amount: Decimal
    receivable_items: int
    receivable_drivers: int


class YangoByWeek(BaseModel):
    week_start_monday: date
    iso_year_week: str
    amount: Decimal
    items: int
    drivers: int


class YangoSummaryResponse(BaseModel):
    totals: YangoTotals
    by_week: List[YangoByWeek]


# Yango Receivable Items Schema
class YangoReceivableItem(BaseModel):
    pay_week_start_monday: date
    pay_iso_year_week: str
    payable_date: date
    achieved_date: Optional[date]
    lead_date: Optional[date]
    lead_origin: Optional[str]
    payer: str
    milestone_type: Optional[str]
    milestone_value: Optional[int]
    window_days: Optional[int]
    trips_in_window: Optional[int]
    person_key: str
    driver_id: Optional[str]
    amount: Decimal
    currency: Optional[str]
    created_at_export: Optional[date]


class YangoReceivableItemsResponse(BaseModel):
    items: List[YangoReceivableItem]
    total: int
    limit: int
    offset: int
























