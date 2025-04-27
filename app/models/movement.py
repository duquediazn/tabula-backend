from sqlmodel import SQLModel, Field
from datetime import datetime


class Movement(SQLModel, table=True):
    __tablename__ = "movimientos"

    id_mov: int = Field(default=None, primary_key=True, nullable=False)
    fecha: datetime = Field(default_factory=lambda: datetime.now())
    tipo: str = Field(
        nullable=False
    )  # Tipo como `str`, la restricción la ponemos en el esquema
    id_usuario: int = Field(foreign_key="usuario.id", nullable=False)
