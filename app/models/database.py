from sqlmodel import SQLModel, create_engine, Session
from app.utils.getenv import get_required_env

# Conectar a la base de datos existente
DATABASE_URL = get_required_env("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)

SQLModel.metadata.clear()


def get_db():
    """Obtiene una sesión de la base de datos."""
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
