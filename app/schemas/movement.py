from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, List
from app.schemas.movement_line import MovementLineCreate, MovementLineResponse


class MovementBase(BaseModel):
    """Esquema base con los campos comunes de un movimiento."""

    tipo: Literal["entrada", "salida"] = Field(
        ..., description="Debe ser 'entrada' o 'salida'"
    )
    id_usuario: int = Field(..., description="ID del usuario que realiza el movimiento")


class MovementCreate(MovementBase):
    """Esquema para la creación de movimientos.
    - Incluye `lineas` para registrar las líneas asociadas."""

    lineas: List[MovementLineCreate] = Field(
        ..., description="Lista de líneas del movimiento"
    )


class MovementResponse(MovementBase):
    """Esquema para responder con los datos de un movimiento."""

    id_mov: int
    fecha: datetime
    nombre_usuario: str
    lineas: List[MovementLineResponse] = Field(
        default=[], description="Líneas asociadas al movimiento"
    )

    class Config:
        from_attributes = True  # Permite convertir modelos SQLModel en respuestas JSON automáticamente


class PaginatedMovementsResponse(BaseModel):
    data: List[MovementResponse]
    total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True


class MovimientoResumen(BaseModel):
    tipo: str 
    cantidad: int 
    
    class Config:
        from_attributes = True

class MovementLastyearGraph(BaseModel):
    id_mov: int
    id_usuario: int
    fecha: datetime
    tipo: str