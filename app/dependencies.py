from fastapi import Depends, HTTPException, status
from app.models.user import User
from app.routers.auth import get_current_user

def require_admin(user: User = Depends(get_current_user)) -> User:
    """Verifica si el usuario es administrador. Si no lo es, lanza una excepción."""
    if user.rol.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción."
        )
    return user  # Retorna el usuario si es admin
