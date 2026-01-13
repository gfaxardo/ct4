"""
Data contract definitions for mapping source tables to canonical fields.

Provides a centralized mapping from various source table schemas
to a unified canonical format for identity matching.
"""
import hashlib
from datetime import date, datetime
from typing import Any, Dict, Optional


class DataContract:
    """
    Maps source table rows to canonical field format.
    
    Defines field mappings for each supported source table,
    enabling consistent data transformation across the pipeline.
    """
    MAPPINGS = {
        "module_ct_cabinet_leads": {
            "source_pk": lambda row: row.get("external_id") or str(row.get("id", "")),
            "snapshot_date": lambda row: _extract_date(row.get("lead_created_at")),
            "park_id": lambda row: None,
            "phone_raw": lambda row: row.get("park_phone"),
            "license_raw": lambda row: None,
            "name_raw": lambda row: _concat_name(
                row.get("first_name"),
                row.get("middle_name"),
                row.get("last_name")
            ),
            "plate_raw": lambda row: row.get("asset_plate_number"),
            "brand_raw": lambda row: None,
            "model_raw": lambda row: row.get("asset_model"),
            "created_at_raw": lambda row: row.get("lead_created_at"),
        },
        "module_ct_scouting_daily": {
            "source_pk": lambda row: _generate_scouting_pk(
                row.get("scout_id"),
                row.get("driver_phone"),
                row.get("driver_license"),
                row.get("registration_date")
            ),
            "snapshot_date": lambda row: _extract_date(row.get("registration_date")),
            "park_id": lambda row: None,
            "phone_raw": lambda row: row.get("driver_phone"),
            "license_raw": lambda row: row.get("driver_license"),
            "name_raw": lambda row: row.get("driver_name"),
            "plate_raw": lambda row: None,
            "brand_raw": lambda row: None,
            "model_raw": lambda row: None,
            "created_at_raw": lambda row: row.get("created_at"),
            "scout_id": lambda row: row.get("scout_id"),
            "acquisition_method": lambda row: row.get("acquisition_method"),
        },
        "drivers": {
            "source_pk": lambda row, **kwargs: str(row.get("driver_id", "")),
            "snapshot_date": lambda row, **kwargs: kwargs.get("run_date") or _extract_date(row.get("created_at")),
            "park_id": lambda row, **kwargs: row.get("park_id"),
            "phone_raw": lambda row, **kwargs: row.get("phone"),
            "license_raw": lambda row, **kwargs: row.get("license_normalized_number") or row.get("license_number"),
            "name_raw": lambda row, **kwargs: row.get("full_name") or _concat_name(
                row.get("first_name"),
                row.get("middle_name"),
                row.get("last_name")
            ),
            "plate_raw": lambda row, **kwargs: row.get("car_normalized_number") or row.get("car_number"),
            "brand_raw": lambda row, **kwargs: row.get("car_brand"),
            "model_raw": lambda row, **kwargs: row.get("car_model"),
            "created_at_raw": lambda row, **kwargs: row.get("created_at"),
            "hire_date": lambda row, **kwargs: _extract_date(row.get("hire_date")),
        }
    }

    @classmethod
    def map_row(cls, table_name: str, row: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if table_name not in cls.MAPPINGS:
            raise ValueError(f"Tabla no soportada: {table_name}")
        
        mapping = cls.MAPPINGS[table_name]
        result = {}
        
        for field, mapper in mapping.items():
            try:
                if callable(mapper):
                    result[field] = mapper(row, **kwargs)
                else:
                    result[field] = mapper
            except Exception:
                result[field] = None
        
        return result

    @classmethod
    def get_missing_keys(cls, table_name: str, row: Dict[str, Any], required_fields: list) -> list:
        mapped = cls.map_row(table_name, row)
        missing = []
        
        for field in required_fields:
            if field not in mapped or mapped[field] is None:
                missing.append(field)
        
        return missing


def _extract_date(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        from app.services.normalization import parse_date
        return parse_date(value)
    return None


def _concat_name(first: Optional[str], middle: Optional[str], last: Optional[str]) -> Optional[str]:
    parts = [p for p in [first, middle, last] if p]
    return " ".join(parts) if parts else None


def _generate_scouting_pk(scout_id: Any, phone: Optional[str], license: Optional[str], date: Any) -> str:
    from app.services.normalization import normalize_phone, normalize_license, parse_date
    
    phone_norm = normalize_phone(phone) or ""
    license_norm = normalize_license(license) or ""
    date_str = str(parse_date(date) or date) if date else ""
    
    key_str = f"{scout_id}|{phone_norm}|{license_norm}|{date_str}"
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()

