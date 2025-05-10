import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Stock(SQLModel, table=True):
    """Modelo SQLModel para representar el stock en los almacenes."""

    __tablename__ = "stock"

    codigo_almacen: int = Field(
        foreign_key="almacen.codigo",
        primary_key=True,
        description="Código del almacén asociado",
    )
    codigo_producto: int = Field(
        foreign_key="producto.codigo",
        primary_key=True,
        description="Código del producto asociado",
    )
    lote: str = Field(
        primary_key=True,
        default="SIN_LOTE",
        description="Identificador del lote del producto",
    )
    fecha_cad: Optional[datetime.date] = Field(
        default=None, description="Fecha de caducidad (si aplica)"
    )
    cantidad: int = Field(
        nullable=False, ge=0, description="Cantidad de unidades en stock (mínimo 0)"
    )
