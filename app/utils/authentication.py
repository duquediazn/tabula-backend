# Este script maneja la autenticación en nuestra API usando JWT (JSON Web Tokens) y el hash de contraseñas con bcrypt.
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from datetime import (
    datetime,
    timedelta,
    timezone,
)  # Para manejar fechas y la expiración de los tokens.
from app.utils.getenv import get_required_env
from fastapi import HTTPException, status
from passlib.context import (
    CryptContext,
)  # Para cifrar y verificar contraseñas con bcrypt.
import jwt  # Para crear y decodificar tokens JWT.
import os  # Para acceder a variables de entorno.

# Clave secreta para firmar JWT
SECRET_KEY = get_required_env("SECRET_KEY")

# Algoritmo de encriptación JWT
ALGORITHM = "HS256"

# Tiempo de expiración del token (minutos)
ACCESS_TOKEN_DURATION = int(os.getenv("ACCESS_TOKEN_DURATION", 30))  # 30 min
REFRESH_TOKEN_DURATION = int(os.getenv("REFRESH_TOKEN_DURATION", 7))  # 7 días
"""
Contexto para cifrado de contraseñas
- CryptContext con bcrypt se usa para cifrar contraseñas de forma segura.
- bcrypt es el estándar recomendado para almacenar contraseñas porque genera hashes únicos y es resistente a ataques.
"""
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera un hash seguro para la contraseña."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña ingresada coincide con la almacenada."""
    return pwd_context.verify(plain_password, hashed_password)


"""
Bcrypt usa "salting", por lo que cada vez que se genera un hash es diferente.
Pero aún así, verify_password() puede verificar si coinciden.
"""


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Crea un token de acceso JWT con tiempo de expiración."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


"""
data → Contiene los datos del usuario (por ejemplo, su email o ID).
Se copia data y se añade la fecha de expiración (exp).
Se firma el token con SECRET_KEY y HS256.
Devuelve un token JWT seguro que el usuario enviará en cada solicitud.

"""


def decode_access_token(token: str):
    """Decodifica un token JWT y retorna los datos o lanza una excepción si es inválido."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )
