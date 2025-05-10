from typing import List, Optional
from pydantic import BaseModel, Field
import datetime


class StockBase(BaseModel):
    """Esquema base con los campos comunes de stock."""

    codigo_almacen: int = Field(..., description="Código del almacén asociado")
    nombre_almacen: str = Field(..., description="Nombre el almacén asociado")
    codigo_producto: int = Field(..., description="Código del producto asociado")
    nombre_producto: str = Field(..., description="Nombre del producto asociado")
    sku: str = Field(..., min_length=3, max_length=20, pattern="^[A-Z0-9]+$")
    lote: str = Field(default="SIN_LOTE", description="Lote del producto")
    fecha_cad: Optional[datetime.date] = Field(
        default=None, description="Fecha de caducidad del lote (si aplica)"
    )
    cantidad: int = Field(
        ..., ge=0, description="Cantidad de unidades disponibles en stock"
    )


class StockResponse(StockBase):
    """Esquema para responder con los datos de un stock específico."""

    class Config:
        from_attributes = True


class StockSummary(BaseModel):
    """Resumen de stock para un producto o almacén específico."""

    codigo_producto: int = Field(..., description="Código del producto")
    codigo_almacen: int = Field(..., description="Código del almacén")
    nombre_almacen: str = Field(..., description="Nombre del almacén")
    total_cantidad: int = Field(
        ..., ge=0, description="Total de unidades en stock para el producto"
    )


class StockHistory(BaseModel):
    """Esquema para consultar el historial de movimientos de stock."""

    id_movimiento: int = Field(..., description="ID del movimiento registrado")
    fecha: datetime.datetime = Field(..., description="Fecha y hora del movimiento")
    tipo: str = Field(..., description="Tipo de movimiento: 'entrada' o 'salida'")
    codigo_almacen: int = Field(..., description="Código del almacén involucrado")
    codigo_producto: int = Field(..., description="Código del producto involucrado")
    sku_producto: str = Field(..., min_length=3, max_length=20, pattern="^[A-Z0-9]+$")
    lote: str = Field(
        default="SIN_LOTE",
        max_length=50,
        description="Lote del producto en el movimiento",
    )
    cantidad: int = Field(..., ge=1, description="Cantidad de unidades movidas")
    usuario: str = Field(
        ..., description="Nombre del usuario que realizó el movimiento"
    )

    class Config:
        orm_mode = True


class PaginatedStockResponse(BaseModel):
    """Esquema para paginación de StockResponse"""

    data: List[StockResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True


class PaginatedStockSummary(BaseModel):
    """Esquema para paginación de StockSummary"""

    data: List[StockSummary]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True


class PaginatedStockHistory(BaseModel):
    """Esquema para paginación de StockHistory"""

    data: List[StockHistory]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True


class StockSemaphore(BaseModel):
    """Esquema base para el endpoint semáforo de fechas próximas a caducar."""

    no_caduca: int = Field(
        ..., ge=0, description="Productos sin fecha de caducidad o superior a 6 meses"
    )
    caduca_proximamente: int = Field(
        ..., ge=0, description="Productos que caducan en los próximos 6 meses"
    )
    caduca_ya: int = Field(
        ..., ge=0, description="Productos que caducan en menos de un mes"
    )

    class Config:
        orm_mode = True


class StockByWarehouse(BaseModel):
    """Suma de stock agrupado por almacén, para gráfico."""

    codigo_almacen: int
    nombre_almacen: str
    total_cantidad: int

    class Config:
        orm_mode = True


class StockByWarehousePieChart(BaseModel):
    """Cantidad de stock por producto en un almacén específico, para gráfico."""

    codigo_producto: int
    nombre_producto: str
    cantidad_total: int


class Config:
    orm_mode = True


class StockByCategory(BaseModel):
    id_categoria: int
    nombre_categoria: str
    cantidad_total: int

    class Config:
        orm_mode = True


class StockByProductInCategory(BaseModel):
    codigo_producto: int
    nombre_producto: str
    cantidad_total: int

    class Config:
        orm_mode = True


class LoteDisponibleResponse(BaseModel):
    lote: str
    fecha_cad: Optional[datetime.date]
    cantidad: int
