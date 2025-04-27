from sqlmodel import SQLModel, create_engine, Session
import os

# Conectar a la base de datos existente
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:admin123@localhost:5432/tabula_db"
)

engine = create_engine(DATABASE_URL, echo=True)

SQLModel.metadata.clear()


def get_db():
    """Obtiene una sesión de la base de datos."""
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
