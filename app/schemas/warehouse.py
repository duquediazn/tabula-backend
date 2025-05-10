from typing import List, Optional
from pydantic import BaseModel, Field

class WarehouseBase(BaseModel):
    """Esquema base con los campos comunes de un almacén."""
    descripcion: str = Field(..., max_length=255, description="Descripción del almacén")
    activo: Optional[bool] = Field(default=True, description="Indica si el almacén está activo (True) o inactivo (False)")

class WarehouseCreate(WarehouseBase):
    """Esquema para la creación de almacenes.
    - Incluye `descripcion` (obligatoria).
    - `activo` es opcional y por defecto será `True`."""
    pass

class WarehouseUpdate(BaseModel):
    """Esquema para la actualización parcial de un almacén.
    - Permite modificar la `descripcion` y el estado `activo`.
    - Ningún campo es obligatorio, se actualizan solo los que se envíen."""
    descripcion: Optional[str] = Field(None, max_length=255, description="Nueva descripción del almacén")
    activo: Optional[bool] = Field(None, description="Nuevo estado del almacén (True o False)")

class WarehouseResponse(WarehouseBase):
    """Esquema para responder con los datos de un almacén.
    - `codigo`: ID único del almacén generado por la base de datos."""
    codigo: int = Field(..., description="Código único del almacén")

    class Config:
        from_attributes = True  # Permite convertir modelos SQLModel en respuestas JSON automáticamente

class PaginatedWarehouseResponse(BaseModel):
    data: List[WarehouseResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True  

class BulkEstadoUpdate(BaseModel):
    codigos: List[int]
    activo: bool