"""
Schemas Pydantic para consultar Source Registry.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class SourceRegistryRow(BaseModel):
    """Fila del Source Registry.
    
    Representa un objeto (tabla/vista/matview) en el registry canónico.
    """
    id: int
    schema_name: str
    object_name: str
    object_type: str  # 'table', 'view', 'matview'
    layer: Optional[str] = None  # 'RAW', 'DERIVED', 'MV', 'CANON'
    role: Optional[str] = None  # 'PRIMARY', 'SECONDARY'
    criticality: Optional[str] = None  # 'critical', 'important', 'normal'
    should_monitor: Optional[bool] = None
    is_expected: Optional[bool] = None
    is_critical: Optional[bool] = None
    health_enabled: Optional[bool] = None
    description: Optional[str] = None
    usage_context: Optional[str] = None  # 'endpoint', 'script', 'both'
    refresh_schedule: Optional[str] = None
    depends_on: Optional[List[Dict[str, str]]] = None  # array de {schema, name}
    discovered_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceRegistryResponse(BaseModel):
    """Response para Source Registry con paginación."""
    items: List[SourceRegistryRow]
    total: int
    limit: int
    offset: int


