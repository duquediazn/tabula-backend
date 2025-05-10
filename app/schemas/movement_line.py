from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class MovementLineBase(BaseModel):
    """Esquema base con los campos comunes de una línea de movimiento."""

    codigo_almacen: int = Field(
        ..., description="Código del almacén donde se realiza el movimiento"
    )
    codigo_producto: int = Field(..., description="Código del producto que se mueve")
    lote: Optional[str] = Field(
        default="SIN_LOTE", max_length=50, description="Lote del producto (opcional)"
    )
    fecha_cad: Optional[date] = Field(
        None, description="Fecha de caducidad del producto (opcional)"
    )
    cantidad: int = Field(
        ...,
        ge=1,
        description="Cantidad de productos en el movimiento (debe ser mayor a 0)",
    )


class MovementLineCreate(MovementLineBase):
    """Esquema para la creación de una línea de movimiento."""

    pass  # `id_mov` y `id_linea` se generan automáticamente


class MovementLineResponse(MovementLineBase):
    """Esquema de respuesta con datos adicionales."""

    id_mov: int
    id_linea: int

    class Config:
        from_attributes = (
            True  # Para convertir modelos SQLModel en respuestas JSON automáticamente
        )


class PaginatedMovementLineResponse(BaseModel):
    data: List[MovementLineResponse]
    total: int
    limit: int
    offset: int


class MovementLineWithNamesResponse(MovementLineResponse):
    nombre_producto: str
    nombre_almacen: str


class PaginatedMovementLineWithNamesResponse(BaseModel):
    data: List[MovementLineWithNamesResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True
