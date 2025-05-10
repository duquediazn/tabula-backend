from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Esquema base para usuarios.
    - Define los campos comunes a todos los esquemas de usuario.
    - `EmailStr` valida que el correo tenga formato correcto.
    """

    nombre: str = Field(
        ..., min_length=3, max_length=100, description="Nombre del usuario"
    )
    email: EmailStr = Field(
        ..., max_length=100, description="Correo electrónico válido"
    )


class UserCreate(UserBase):
    """
    Esquema para registrar usuarios.
    - `passwd`: Se exige un mínimo de 8 caracteres.
    - `rol`: Por defecto, 'usuario'. Solo permite valores válidos.
    - `activo`: False por defecto, el usuario debe ser activado por un administrador.
    """

    passwd: str = Field(
        ...,
        min_length=8,
        max_length=255,
        description="Contraseña segura (mínimo 8 caracteres)",
    )
    rol: Optional[str] = Field(
        default="usuario",
        pattern="^(usuario|admin)$",
        description="Rol del usuario (usuario/admin)",
    )
    activo: Optional[bool] = Field(
        default=False, description="Estado activo/inactivo del usuario"
    )


class UserUpdate(BaseModel):
    """
    Esquema para actualizar usuarios.
    - Permite modificar `nombre`, `email`, `rol`, `activo` y `password`.
    - Evita valores vacíos en los campos opcionales.
    """

    nombre: Optional[str] = Field(
        None, min_length=3, max_length=100, description="Nuevo nombre del usuario"
    )
    email: Optional[EmailStr] = Field(
        None, max_length=100, description="Nuevo email del usuario"
    )
    rol: Optional[str] = Field(
        None, pattern="^(usuario|admin)$", description="Nuevo rol (usuario/admin)"
    )
    activo: Optional[bool] = None

    passwd: Optional[str] = Field(
        None, min_length=6, description="Nueva contraseña (opcional)"
    )


class UserResponse(UserBase):
    """
    Esquema para respuestas de usuario.
    - Incluye `id`, `rol` y `activo` porque son datos importantes en la API.
    - No incluye `passwd` por seguridad.
    """

    id: int
    rol: str
    activo: bool

    class Config:
        orm_mode = True  # Permite convertir modelos SQLModel en JSON


class PaginatedUserResponse(BaseModel):
    data: List[UserResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True


class BulkEstadoUpdate(BaseModel):
    ids: List[int]
    activo: bool
