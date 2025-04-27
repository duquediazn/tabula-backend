from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.dependencies import require_admin
from app.models import user
from app.models.database import get_db
from app.models.movement_line import MovementLine
from app.models.stock import Stock
from app.models.warehouse import Warehouse
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.warehouse import (
    PaginatedWarehouseResponse,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    BulkEstadoUpdate,
)
from app.utils.validation import is_admin_user

router = APIRouter(prefix="/almacenes", tags=["Almacenes"])


@router.get("/", response_model=PaginatedWarehouseResponse)
def get_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    estado: Optional[bool] = Query(None),
):
    """Lista todos los almacenes. Usuarios y admins pueden verlos."""
    try:
        statement = select(Warehouse)

        if search:
            search_like = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(Warehouse.descripcion).ilike(search_like)
            )

        if estado is not None:
            statement = statement.where(Warehouse.activo == estado)

        paginated = (
            statement.order_by(Warehouse.descripcion).limit(limit).offset(offset)
        )
        warehouses = db.exec(paginated).all()

        total_records = (
            db.exec(select(func.count()).select_from(statement.subquery())).first() or 0
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )
    return {
        "data": warehouses,
        "total": total_records,
        "limit": limit,
        "offset": offset,
    }


@router.put("/estado-multiple", status_code=200)
def cambiar_estado_masivo_almacenes(
    data: BulkEstadoUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        almacenes = db.exec(
            select(Warehouse).where(Warehouse.codigo.in_(data.codigos))
        ).all()

        actualizados = []

        for almacen in almacenes:
            if almacen.activo == data.activo:
                continue

            if data.activo is False:
                stock_total = (
                    db.exec(
                        select(func.sum(Stock.cantidad)).where(
                            Stock.codigo_almacen == almacen.codigo
                        )
                    ).first()
                    or 0
                )

                if stock_total > 0:
                    continue  # El almacén aún tiene productos dentro

            almacen.activo = data.activo
            db.add(almacen)
            actualizados.append(almacen)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Error al actualizar almacenes")

    db.commit()
    return {
        "mensaje": f"{len(actualizados)} almacenes actualizados",
        "omitidos": len(data.codigos) - len(actualizados),
    }


@router.get("/{codigo}", response_model=WarehouseResponse)
def get_warehouse(
    codigo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un almacén específico por su código. Admin puede ver desactivos"""
    try:
        warehouse = db.get(Warehouse, codigo)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado."
        )

    if not is_admin_user(current_user) and not warehouse.activo:
        raise HTTPException(status_code=403, detail="Este almacén está inactivo.")

    return warehouse


@router.post("/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # Solo admins pueden crear
):
    """Crea un nuevo almacén. Solo administradores pueden hacerlo."""
    new_warehouse = Warehouse(**warehouse_data.model_dump())

    try:
        db.add(new_warehouse)
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
    db.refresh(new_warehouse)
    return new_warehouse


@router.put("/{codigo}", response_model=WarehouseResponse)
def update_warehouse(
    codigo: int,
    warehouse_update: WarehouseUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # Solo admins pueden modificar
):
    """Edita la descripción o el estado de un almacén. Solo administradores."""
    try:
        warehouse = db.get(Warehouse, codigo)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado"
        )

    if warehouse_update.activo == False:
        try:
            stock = db.exec(select(Stock).where(Stock.codigo_almacen == codigo)).first()
            if stock:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"El almacén {codigo}, no está vacío y por tanto no se puede inactivar.",
                )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error de conexión con la base de datos",
            )

    # Actualizar solo los campos enviados
    if warehouse_update.descripcion:
        warehouse.descripcion = warehouse_update.descripcion
    if warehouse_update.activo is not None:
        warehouse.activo = warehouse_update.activo

    try:
        db.add(warehouse)
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
            detail="Error interno del servidor al actualizar el almacén.",
        )
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.delete("/{codigo}", response_model=WarehouseResponse)
def deactivate_warehouse(
    codigo: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Elimina un almacén solo si no tiene movimientos asociados.
    Solo los administradores pueden realizar esta acción."""

    try:
        warehouse = db.get(Warehouse, codigo)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado"
        )

    try:
        movement_exists = db.exec(
            select(MovementLine).where(MovementLine.codigo_almacen == codigo)
        ).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if movement_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar este almacén ya que tiene movimientos registrados.",
        )

    try:
        db.delete(warehouse)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en la base de datos.",
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al eliminar el almacén. error: {e}",
        )
    db.commit()

    return warehouse
