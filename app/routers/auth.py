"""
Este archivo maneja la autenticación de usuarios en la API, incluyendo:
- Registro de usuarios (/auth/registro) → Guarda nuevos usuarios en la BD con contraseñas encriptadas.
- Inicio de sesión (/auth/login) → Verifica credenciales y devuelve un token JWT.
- Obtener datos del usuario autenticado (/auth/perfil) → Usa el token JWT para devolver los datos del usuario.
"""

from datetime import timedelta
from fastapi import Request, Response
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.utils.authentication import (
    ACCESS_TOKEN_DURATION,
    REFRESH_TOKEN_DURATION,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

"""
- APIRouter → Crea un grupo de rutas (/auth).
- Depends → Maneja dependencias, como la base de datos y autenticación.
- HTTPException → Se usa para lanzar errores HTTP con mensajes personalizados.
- status → Contiene códigos HTTP (400, 401, etc.).
- OAuth2PasswordBearer → Maneja la autenticación OAuth2 con tokens JWT.
- get_db() → Obtiene la sesión de base de datos.
- UserCreate, UserResponse → Esquemas de validación con Pydantic.
- hash_password, verify_password, create_access_token, decode_access_token → Funciones de autenticación.
"""

# Configuración del Router
router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Configuración del esquema de autenticación OAuth2
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


### REGISTRO DE USUARIO ###
@router.post(
    "/registro", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario con contraseña encriptada."""
    try:
        statement = select(User).where(User.email == user_data.email)
        existing_user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado.",
        )

    # Crear usuario
    new_user = User(
        nombre=user_data.nombre,
        email=user_data.email,
        passwd=hash_password(user_data.passwd),
        rol="usuario",  # Asignar siempre el rol "usuario"
        activo=False,  # Inactivo por defecto
    )

    try:
        db.add(
            new_user
        )  # sqlmodel (SQLAlchemy): agrega una instancia de un objeto al contexto de la sesión (pendiente)

    except IntegrityError:
        db.rollback()  # Deshacer cualquier cambio no commiteado en la transacción
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en la base de datos.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al registrar el usuario.",
        )

    db.commit()  # confirma todas las transacciones realizadas en la sesión actual
    db.refresh(
        new_user
    )  # actualiza los atributos de una instancia con los valores actuales de la base de datos,
    return new_user  # `UserResponse` filtra automáticamente la contraseña


### LOGIN DE USUARIO ###
@router.post("/login")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Autentica al usuario y genera un token JWT."""
    try:
        statement = select(User).where(
            User.email == form_data.username
        )  # OAuth2PasswordRequestForm por defecto espera username y password, nuestro "username" es el email.
        user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos:",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El usuario no existe"
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo. Contacta al administrador para activarlo.",
        )
    if not verify_password(form_data.password, user.passwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.rol},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_DURATION),
    )
    refresh_token = create_access_token(
        {"sub": str(user.id)}, expires_delta=timedelta(days=REFRESH_TOKEN_DURATION)
    )

    response.set_cookie(
        key="refresh_token",  # Nombre de la cookie
        value=refresh_token,  # Valor que vamos a guardar (el JWT de refresco)
        httponly=True,  # Impide que JavaScript acceda a la cookie → más seguro
        secure=True,  # False en desarrollo, True en producción
        samesite="none",  # Para permitir cookies cross-origin
        path="/auth/refresh",  # Opcional, pero buena práctica de seguridad
        max_age=REFRESH_TOKEN_DURATION * 24 * 60 * 60,  # Tiempo de vida en segundos
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


### OBTENER DATOS DEL USUARIO AUTENTICADO ###
def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)):
    """Obtiene el usuario actual a partir del token JWT."""
    payload = decode_access_token(token)

    # Validar que el token contiene el campo "sub"
    user_id = payload["sub"]
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )

    # Verificar si el usuario sigue existiendo en la base de datos
    try:
        statement = select(User).where(User.id == user_id)
        user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado o eliminado",
        )
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo. Contacta al administrador para activarlo.",
        )

    return user


@router.get("/perfil", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    """Retorna los datos del usuario autenticado."""
    return user


### REFRESCAR TOKEN PARA USUARIO AUTENTICADO ###
@router.post("/refresh")
def refresh_token(request: Request, db: Session = Depends(get_db)):
    """Genera un nuevo Access Token a partir del Refresh Token guardado en cookie HttpOnly."""
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token no encontrado en cookies",
        )

    try:
        payload = decode_access_token(refresh_token)
        user_id = payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token inválido"
        )

    try:
        statement = select(User).where(User.id == user_id)
        user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o eliminado",
        )

    new_access_token = create_access_token(
        {"sub": str(user.id), "role": user.rol},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_DURATION),
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


### VERIFICACIÓN CON CONTRASEÑA ###
class PasswordCheckRequest(BaseModel):
    password: str


@router.post("/verify-password")
def verify_user_password(
    data: PasswordCheckRequest, current_user: User = Depends(get_current_user)
):
    """Verifica que la contraseña proporcionada coincide con la del usuario autenticado."""
    if not verify_password(data.password, current_user.passwd):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta"
        )
    return {"message": "Contraseña válida"}


### LOGOUT ###
@router.post("/logout")
def logout(response: Response):
    """Elimina la cookie de refresh_token al cerrar sesión."""
    response.delete_cookie(
        key="refresh_token", path="/auth/refresh", secure=True, samesite="none"
    )
    return {"message": "Sesión cerrada correctamente"}
