from sqlmodel import SQLModel, Field

class ProductCategory(SQLModel, table=True):
    __tablename__ = "categoria_producto"

    id: int = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, nullable=False, unique=True)
