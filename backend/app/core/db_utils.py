"""
Utilidades para resultados de base de datos.

Centraliza la conversión fila SQLAlchemy/Result -> dict para validación con Pydantic,
evitando repetir el mismo patrón en todos los endpoints y servicios.
"""
from typing import Any


def row_to_dict(row: Any) -> dict[str, Any]:
    """
    Convierte una fila (Row, RowMapping, o objeto con _mapping) a dict.
    Útil antes de model_validate() con schemas Pydantic.
    """
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if hasattr(row, "_asdict"):
        return row._asdict()
    return dict(row)
