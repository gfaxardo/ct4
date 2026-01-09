"""
Schemas para upload y procesamiento de cabinet leads CSV
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CabinetLeadsUploadResponse(BaseModel):
    """Response del upload de CSV"""
    status: str = Field(..., description="Estado: 'success' o 'error'")
    message: str = Field(..., description="Mensaje descriptivo")
    stats: dict = Field(..., description="Estadísticas del upload")
    errors: List[str] = Field(default_factory=list, description="Lista de errores encontrados")
    run_id: Optional[int] = Field(None, description="ID de la corrida de ingesta si auto_process=true")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "CSV procesado exitosamente",
                "stats": {
                    "total_inserted": 150,
                    "total_ignored": 10,
                    "total_rows": 160,
                    "skipped_by_date": 5,
                    "errors_count": 0,
                    "auto_process": True,
                    "date_cutoff_used": "2025-12-15"
                },
                "errors": [],
                "run_id": 123
            }
        }



