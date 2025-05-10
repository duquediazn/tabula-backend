from typing import Optional
from sqlmodel import SQLModel, Field


class Product(SQLModel, table=True):
    __tablename__ = "producto"

    codigo: int = Field(default=None, primary_key=True, nullable=False)
    sku: str = Field(unique=True, index=True, nullable=False)
    nombre_corto: str = Field(nullable=False)
    descripcion: Optional[str] = Field(default=None)
    id_categoria: int = Field(foreign_key="categoria_producto.id", nullable=False)
    activo: bool = Field(default=True, nullable=False)
