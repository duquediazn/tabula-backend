from app.schemas.product_category import CategoryResponse
from pydantic import BaseModel, Field
from typing import List, Optional


class ProductBase(BaseModel):
    """
    Esquema base para productos.
    - Define los campos comunes a todos los esquemas.
    - `sku`: Validado con regex para permitir solo letras mayúsculas y números.
    """

    sku: str = Field(
        ..., min_length=3, max_length=20, pattern="^[A-Z0-9]+$"
    )  # Field(...) significa que el campo debe ser proporcionado al crear un objeto
    nombre_corto: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    id_categoria: int = Field(..., gt=0)


class ProductCreate(ProductBase):
    """
    Esquema para la creación de un producto.
    - `activo` no se incluye porque por defecto será `True`.
    """

    pass


class ProductUpdate(BaseModel):
    """
    Esquema para la actualización de un producto.
    - Permite modificar `sku`, `nombre_corto`, `descripcion`, `categoria`, y `activo`.
    """

    sku: Optional[str] = Field(None, min_length=3, max_length=20, pattern="^[A-Z0-9]+$")
    nombre_corto: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    id_categoria: Optional[int] = Field(None, gt=0)
    activo: Optional[bool] = None


class ProductResponse(ProductBase):
    """
    Esquema para respuestas de la API.
    - Incluye `codigo` y `activo`, ya que estos se generan en la base de datos.
    """

    nombre_categoria: str = Field(..., min_length=3, max_length=50)
    codigo: int
    activo: bool

    class Config:
        orm_mode = True  # Permite convertir SQLModel en JSON automáticamente


class PaginatedProductResponse(BaseModel):
    data: List[ProductResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True


class EstadoMultipleRequest(BaseModel):
    codigos: list[int]
    activo: bool
