from sqlmodel import SQLModel, Field

class Warehouse(SQLModel, table=True):
    __tablename__ = "almacen"

    codigo: int = Field(default=None, primary_key=True)
    descripcion: str = Field(nullable=False, max_length=255)
    activo: bool = Field(default=True, nullable=False)