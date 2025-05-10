from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select
from sqlalchemy.exc import SQLAlchemyError
from app.models.database import get_db
from app.models.movement import Movement
from app.models.movement_line import MovementLine
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.movement import (
    MovementLastyearGraph,
    MovementResponse,
    MovementCreate,
    PaginatedMovementsResponse,
    MovimientoResumen,
)
from app.routers.auth import get_current_user
from app.schemas.movement_line import (
    MovementLineResponse,
    PaginatedMovementLineWithNamesResponse,
)
from app.utils.validation import is_admin_user
from app.routers.websocket import manager
import anyio


router = APIRouter(prefix="/movimientos", tags=["Movimientos"])


@router.get("/", response_model=PaginatedMovementsResponse)
def get_movements(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    usuario_id: Optional[int] = Query(None),
):
    """Lista todos los movimientos. Admin ve todos, usuario solo los suyos, incluyendo líneas."""
    try:
        statement = select(Movement, User.nombre).join(
            User, Movement.id_usuario == User.id
        )

        if search:
            search_like = f"%{search.lower()}%"
            statement = statement.where(func.lower(User.nombre).ilike(search_like))

        if tipo in {"entrada", "salida"}:
            statement = statement.where(Movement.tipo == tipo)

        if fecha_desde:
            statement = statement.where(Movement.fecha >= fecha_desde)

        if fecha_hasta:
            statement = statement.where(Movement.fecha <= fecha_hasta)

        if usuario_id and is_admin_user(current_user):
            statement = statement.where(Movement.id_usuario == usuario_id)

        if not is_admin_user(current_user):
            statement = statement.where(Movement.id_usuario == current_user.id)

        results = db.exec(
            statement.order_by(Movement.fecha.desc()).limit(limit).offset(offset)
        ).all()

        total_records = (
            db.exec(select(func.count()).select_from(statement.subquery())).first() or 0
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    movements_response = []

    for movement, nombre_usuario in results:
        try:
            movement_lines = db.exec(
                select(MovementLine)
                .where(MovementLine.id_mov == movement.id_mov)
                .order_by(MovementLine.id_linea)
            ).all()
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error de conexión con la base de datos",
            )

        movements_response.append(
            MovementResponse(
                id_mov=movement.id_mov,
                fecha=movement.fecha,
                tipo=movement.tipo,
                id_usuario=movement.id_usuario,
                nombre_usuario=nombre_usuario,
                lineas=[
                    MovementLineResponse.model_validate(line) for line in movement_lines
                ],
            )
        )

    return {
        "data": movements_response,
        "total": total_records,
        "limit": limit,
        "offset": offset,
    }


@router.get("/last-year", response_model=List[MovementLastyearGraph])
def get_movements_last_year(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve los movimientos del último año. Filtra por usuario si no es admin."""
    fecha_hasta = datetime.combine(date.today(), time.max)
    fecha_desde = fecha_hasta - relativedelta(years=1)

    try:
        statement = (
            select(Movement)
            .where(Movement.fecha >= fecha_desde)
            .where(Movement.fecha <= fecha_hasta)
        )

        if not is_admin_user(current_user):
            statement = statement.where(Movement.id_usuario == current_user.id)

        statement = statement.order_by(Movement.fecha.desc())
        results = db.exec(statement).all()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return [
        MovementLastyearGraph(
            id_mov=row.id_mov,
            id_usuario=row.id_usuario,
            fecha=row.fecha,
            tipo=row.tipo,
        )
        for row in results
    ]


@router.get("/{id_mov}", response_model=MovementResponse)
def get_movement(
    id_mov: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene los detalles de un movimiento específico con sus líneas.
    - **Usuarios normales** solo pueden ver sus propios movimientos.
    - **Admins** pueden ver cualquier movimiento.
    """
    try:
        statement = select(Movement).where(Movement.id_mov == id_mov)
        movement = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado"
        )

    # Si no es admin y el movimiento no pertenece al usuario autenticado, denegar acceso
    if not is_admin_user(current_user) and movement.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este movimiento",
        )

    # Obtener usuario asociado al movimiento
    try:
        usuario = db.exec(
            select(User.nombre).where(User.id == movement.id_usuario)
        ).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el usuario asociado al movimiento",
        )

    # Obtener líneas del movimiento
    try:
        statement_lines = select(MovementLine).where(
            MovementLine.id_mov == movement.id_mov
        )
        movement_lines = db.exec(statement_lines).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las líneas del movimiento",
        )

    return MovementResponse(
        id_mov=movement.id_mov,
        fecha=movement.fecha,
        tipo=movement.tipo,
        id_usuario=movement.id_usuario,
        nombre_usuario=usuario or "Desconocido",
        lineas=[MovementLineResponse.model_validate(line) for line in movement_lines],
    )


@router.post("/", response_model=MovementResponse, status_code=status.HTTP_201_CREATED)
def create_movement(
    movement_data: MovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registra un movimiento con todas sus líneas en una sola petición.

    - Un **usuario normal** solo puede registrar movimientos a su nombre.
    - Un **admin** puede registrar movimientos para cualquier usuario.
    - Si un producto está inactivo, se interrumpe la operación.
    - Si un almacén está inactivo, se interrumpe la operación.
    """

    # Si no es admin, el usuario solo puede registrar sus propios movimientos
    if not is_admin_user(current_user) and movement_data.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes registrar un movimiento para otro usuario.",
        )

    if not movement_data.lineas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El movimiento debe contener al menos una línea.",
        )

    # Controlamos que no se puedan meter productos con fecha de caducidad vencida.
    for linea in movement_data.lineas:
        if (
            linea.fecha_cad
            and linea.fecha_cad <= date.today()
            and movement_data.tipo == "entrada"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"La línea con producto {linea.codigo_producto}, lote '{linea.lote}', "
                    f"tiene una fecha de caducidad vencida o del día actual: {linea.fecha_cad}."
                ),
            )

    # Control de máximo de líneas por movimiento
    if len(movement_data.lineas) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número máximo de líneas permitidas es 100.",
        )

    # Crear el movimiento
    new_movement = Movement(
        tipo=movement_data.tipo,
        id_usuario=movement_data.id_usuario,
    )

    try:
        db.add(new_movement)
        db.flush()

        almacenes = [linea.codigo_almacen for linea in movement_data.lineas]
        productos = [linea.codigo_producto for linea in movement_data.lineas]

        almacenes_activos = db.exec(
            select(Warehouse.codigo).where(
                Warehouse.codigo.in_(almacenes), Warehouse.activo == True
            )
        ).all()

        diff = set(almacenes) - set(almacenes_activos)
        if diff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los siguientes almacenes: {diff} no existen",
            )

        productos_activos = db.exec(
            select(Product.codigo).where(
                Product.codigo.in_(productos), Product.activo == True
            )
        ).all()

        diff = set(productos) - set(productos_activos)
        if diff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los siguientes productos: {diff} no existen",
            )

        # Agregar las líneas de movimiento si las hay
        for i, line_data in enumerate(movement_data.lineas, 1):

            # Crear la línea de movimiento
            new_line = MovementLine(
                id_mov=new_movement.id_mov,
                id_linea=i,
                codigo_almacen=line_data.codigo_almacen,
                codigo_producto=line_data.codigo_producto,
                lote=line_data.lote or "SIN_LOTE",
                fecha_cad=line_data.fecha_cad,
                cantidad=line_data.cantidad,
            )
            db.add(new_line)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        msg_error = (str(e.orig) if hasattr(e, "orig") else str(e)).split("\n")[0]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de integridad: {msg_error}",
        )
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error en la base de datos.",
        )

    # Obtener usuario asociado al movimiento
    try:
        nombre_usuario = db.exec(
            select(User.nombre).where(User.id == movement_data.id_usuario)
        ).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener el usuario asociado al movimiento",
        )

    # Recuperamos las líneas asociadas
    try:
        movement_lines = db.exec(
            select(MovementLine).where(MovementLine.id_mov == new_movement.id_mov)
        ).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    # Enviar mensaje a todos los clientes WebSocket conectados
    try:
        mensaje = (
            f"Nuevo movimiento registrado: {new_movement.id_mov} ({new_movement.tipo})"
        )

        # Función asíncrona que realizará el broadcast del mensaje
        async def emitir_websocket_mensaje(mensaje: str):
            await manager.broadcast(mensaje)

        """
        Se utiliza AnyIO para emitir un mensaje WebSocket de manera asincrónica desde una ruta sincrónica, 
        garantizando compatibilidad con el event loop de FastAPI."
        """
        anyio.from_thread.run(emitir_websocket_mensaje, mensaje)

    except Exception as e:
        print("Error al emitir WebSocket:", str(e))

    # Devolver el objeto con las líneas
    return MovementResponse(
        id_mov=new_movement.id_mov,
        fecha=new_movement.fecha,
        tipo=new_movement.tipo,
        id_usuario=new_movement.id_usuario,
        nombre_usuario=nombre_usuario or "Desconocido",
        lineas=[MovementLineResponse.model_validate(line) for line in movement_lines],
    )


@router.get("/{id_mov}/lineas", response_model=PaginatedMovementLineWithNamesResponse)
def get_movement_lines(
    id_mov: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Lista todas las líneas de un movimiento con nombres de producto y almacén."""

    try:
        statement = select(Movement).where(Movement.id_mov == id_mov)
        movement = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado",
        )

    if not is_admin_user(current_user) and movement.id_usuario != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este movimiento",
        )

    try:
        statement_lines = (
            select(MovementLine, Product.nombre_corto, Warehouse.descripcion)
            .join(Product, Product.codigo == MovementLine.codigo_producto)
            .join(Warehouse, Warehouse.codigo == MovementLine.codigo_almacen)
            .where(MovementLine.id_mov == id_mov)
            .order_by(MovementLine.id_linea)
        )

        results = db.exec(statement_lines.limit(limit).offset(offset)).all()
        total_records = (
            db.exec(
                select(func.count()).select_from(statement_lines.subquery())
            ).first()
            or 0
        )

        lineas = []
        for linea, nombre_producto, nombre_almacen in results:
            lineas.append(
                {
                    "id_linea": linea.id_linea,
                    "id_mov": linea.id_mov,
                    "codigo_almacen": linea.codigo_almacen,
                    "codigo_producto": linea.codigo_producto,
                    "nombre_producto": nombre_producto,
                    "nombre_almacen": nombre_almacen,
                    "lote": linea.lote,
                    "fecha_cad": linea.fecha_cad,
                    "cantidad": linea.cantidad,
                }
            )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cargar las líneas del movimiento",
        )

    return {
        "data": lineas,
        "total": total_records,
        "limit": limit,
        "offset": offset,
    }


@router.get("/resumen/tipo", response_model=List[MovimientoResumen])
def contar_movimientos_por_tipo(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        statement = select(Movement.tipo, func.count()).join(
            User, Movement.id_usuario == User.id
        )

        if not is_admin_user(current_user):
            statement = statement.where(Movement.id_usuario == current_user.id)

        statement = statement.group_by(Movement.tipo)
        resultados = db.exec(statement).all()

        conteo = {"entrada": 0, "salida": 0}
        for tipo, cantidad in resultados:
            if tipo in conteo:
                conteo[tipo] = cantidad

        return [
            {"tipo": "Entrada", "cantidad": conteo["entrada"]},
            {"tipo": "Salida", "cantidad": conteo["salida"]},
        ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )
