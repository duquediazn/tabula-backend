from sqlmodel import Column, SQLModel, Field, String

class User(SQLModel, table=True):
    __tablename__ = "usuario"  

    id: int = Field(default=None, primary_key=True, nullable=False)
    nombre: str = Field(nullable=False)
    email: str = Field(unique=True, nullable=False, index=True)
    passwd: str = Field(nullable=False)
    rol: str = Field(nullable=False)
    activo: bool = Field(default=True, nullable=False)