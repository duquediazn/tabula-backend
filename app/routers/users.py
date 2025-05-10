from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.database import get_db
from app.models.movement import Movement
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.user import (
    BulkEstadoUpdate,
    PaginatedUserResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.utils.authentication import hash_password
from app.dependencies import require_admin
from app.utils.validation import is_admin_user

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("/", response_model=PaginatedUserResponse)
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: str = Query(None),
    estado: bool = Query(None),
):
    """Lista todos los usuarios (solo accesible para admins)."""
    try:
        statement = select(User)

        # Filtro por estado (activo/inactivo)
        if estado is not None:
            statement = statement.where(User.activo == estado)

        # Filtro por nombre o email (insensible a mayúsculas/minúsculas)
        if search:
            search_like = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(User.nombre).like(search_like)
                | func.lower(User.email).like(search_like)
            )

        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

        users = db.exec(
            statement.order_by(User.nombre).limit(limit).offset(offset)
        ).all()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return {"data": users, "total": total_records, "limit": limit, "offset": offset}


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Solo un admin puede crear usuarios y asignar roles."""

    # Verificar si el email ya existe
    try:
        statement = select(User).where(User.email == user_data.email)
        existing_user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if existing_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    # Validar rol
    if user_data.rol.lower() not in ["usuario", "admin"]:
        raise HTTPException(
            status_code=400, detail="Rol no válido. Debe ser 'usuario' o 'admin'."
        )

    # Crear usuario
    new_user = User(
        nombre=user_data.nombre,
        email=user_data.email,
        passwd=hash_password(user_data.passwd),
        rol=user_data.rol.lower(),
        activo=user_data.activo,
    )

    try:
        db.add(new_user)
    except IntegrityError:
        db.rollback()
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
    db.commit()
    db.refresh(new_user)

    return new_user  # `UserResponse` filtra automáticamente la contraseña


@router.get("/{id}", response_model=UserResponse)
def get_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener datos de un usuario específico.
    - Un **admin** puede ver cualquier usuario.
    - Un **usuario normal** solo puede ver su propio perfil.
    """
    try:
        statement = select(User).where(User.id == id)
        user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    if not is_admin_user(current_user) or user.id != id:
        raise HTTPException(
            status_code=403, detail="No tienes permiso para ver este usuario"
        )

    return user


@router.put("/estado-multiple")
def cambiar_estado_masivo_usuarios(
    data: BulkEstadoUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Permite a un admin activar o desactivar varios usuarios a la vez."""
    try:
        usuarios = db.exec(select(User).where(User.id.in_(data.ids))).all()
        actualizados = []

        for usuario in usuarios:
            if usuario.activo == data.activo:
                continue  # Ya tiene el estado deseado

            # Reglas opcionales:
            # No permitir desactivar al usuario actual
            if data.activo is False and usuario.id == admin.id:
                continue

            usuario.activo = data.activo
            db.add(usuario)
            actualizados.append(usuario)

        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al actualizar usuarios",
        )

    return {
        "mensaje": f"{len(actualizados)} usuarios actualizados",
        "omitidos": len(data.ids) - len(actualizados),
    }


@router.put("/{id}", response_model=UserResponse)
def update_user(
    id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite a un usuario actualizar su perfil o a un admin editar cualquier usuario."""

    # Buscar el usuario en la base de datos
    try:
        statement = select(User).where(User.id == id)
        user = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # Evaluamos si el usuario actual es admin
    is_admin = is_admin_user(current_user)

    # Control de permisos: solo admin o el propio usuario puede editar
    if not is_admin and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar este usuario",
        )

    # Aplicar cambios (el usuario normal NO puede cambiar el rol ni el estado activo)
    if user_update.nombre:
        user.nombre = user_update.nombre

    if user_update.email:
        # Verificar si el nuevo email ya está en uso por otro usuario
        try:
            existing_user = db.exec(
                select(User).where(User.email == user_update.email, User.id != user.id)
            ).first()
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno en la base de datos",
            )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está en uso",
            )
        user.email = user_update.email

    if user_update.rol:
        if not is_admin:  # Evita que un usuario normal cambie el rol
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para cambiar el rol",
            )
        if user_update.rol.lower() not in ["usuario", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol no válido. Debe ser 'usuario' o 'admin'.",
            )
        user.rol = user_update.rol.lower()

    if user_update.activo is not None:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para cambiar el estado activo",
            )
        user.activo = user_update.activo

    if user_update.passwd:
        user.passwd = hash_password(user_update.passwd)

    try:
        db.add(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en la base de datos. Verifica los datos enviados.",
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar el usuario.",
        )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{id}", response_model=UserResponse)
def delete_user(
    id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Permite a un admin eliminar un usuario siempre que no haya realizado ningún movimiento."""
    # Buscar el usuario en la base de datos
    try:
        user = db.exec(select(User).where(User.id == id)).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado"
        )

    # Verificar si el usuario tiene movimientos en la base de datos
    try:
        statement = select(Movement).where(Movement.id_usuario == id)
        has_movements = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if has_movements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el usuario porque tiene movimientos registrados",
        )

    try:
        db.delete(user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el usuario",
        )
    db.commit()
    return user  # Retorna los datos del usuario eliminado
