from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date

class MovementLine(SQLModel, table=True):
    __tablename__ = "movimientos_lineas"

    id_mov: int = Field(foreign_key="movimientos.id_mov", primary_key=True)
    id_linea: int = Field(primary_key=True, ge=1)  # Se asegura que sea mayor a 0
    codigo_almacen: int = Field(foreign_key="almacen.codigo", nullable=False)
    codigo_producto: int = Field(foreign_key="producto.codigo", nullable=False)
    lote: str = Field(default="SIN_LOTE", max_length=50)
    fecha_cad: Optional[date] = Field(default=None)
    cantidad: int = Field(nullable=False, ge=1)  # La cantidad siempre debe ser mayor a 0
