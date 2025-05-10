from dotenv import (
    load_dotenv,
)  # Para cargar variables de entorno desde un archivo .env.
import os  # Para acceder a variables de entorno.

load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise Exception("Env var {name} is required but not found.")
    return value
