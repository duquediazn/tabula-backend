import datetime
from typing import List
from dateutil.relativedelta import relativedelta
from app.models.product_category import ProductCategory
from app.models.warehouse import Warehouse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, case, func, select
from sqlalchemy.exc import SQLAlchemyError
from app.models.database import get_db
from app.models.movement import Movement
from app.models.movement_line import MovementLine
from app.models.product import Product
from app.models.stock import Stock
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.stock import (
    LoteDisponibleResponse,
    PaginatedStockHistory,
    PaginatedStockResponse,
    PaginatedStockSummary,
    StockByCategory,
    StockByProductInCategory,
    StockByWarehouse,
    StockByWarehousePieChart,
    StockResponse,
    StockSemaphore,
    StockSummary,
    StockHistory,
)

router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/", response_model=PaginatedStockResponse)
def get_all_stock(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Lista todo el stock de todos los almacenes."""
    try:
        statement = (
            select(
                Stock.codigo_almacen,
                Warehouse.descripcion,
                Stock.codigo_producto,
                Product.nombre_corto,
                Product.sku,
                Stock.lote,
                Stock.fecha_cad,
                Stock.cantidad,
            )
            .order_by(Stock.codigo_almacen, Stock.codigo_producto, Stock.lote)
            .limit(limit)
            .offset(offset)
        )
        stock = db.exec(statement).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )
    return PaginatedStockResponse(
        data=stock,
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/almacen/{codigo_almacen}", response_model=PaginatedStockResponse)
def get_stock_by_warehouse(
    codigo_almacen: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Lista el stock de un almacén específico."""
    try:
        statement = (
            select(
                Stock.codigo_almacen,
                Warehouse.descripcion,
                Stock.codigo_producto,
                Product.nombre_corto,
                Product.sku,
                Stock.lote,
                Stock.fecha_cad,
                Stock.cantidad,
            )
            .join(Warehouse, Warehouse.codigo == Stock.codigo_almacen)
            .join(Product, Product.codigo == Stock.codigo_producto)
            .where(Stock.codigo_almacen == codigo_almacen)
            .order_by(Stock.codigo_almacen, Stock.codigo_producto, Stock.lote)
            .limit(limit)
            .offset(offset)
        )
        stock = db.exec(statement).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )
    return PaginatedStockResponse(
        data=[
            StockResponse(
                codigo_almacen=item.codigo_almacen,
                nombre_almacen=item.descripcion,
                codigo_producto=item.codigo_producto,
                nombre_producto=item.nombre_corto,
                sku=item.sku,
                lote=item.lote,
                fecha_cad=item.fecha_cad,
                cantidad=item.cantidad,
            )
            for item in stock
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/almacen/{codigo_almacen}/detalle", response_model=List[StockByWarehousePieChart]
)
def get_stock_by_warehouse_pie_chart(
    codigo_almacen: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cantidad de stock por producto en un almacén específico."""
    try:
        statement = (
            select(
                Stock.codigo_producto,
                Product.nombre_corto,
                func.sum(Stock.cantidad).label("cantidad_total"),
            )
            .join(Product, Product.codigo == Stock.codigo_producto)
            .where(Stock.codigo_almacen == codigo_almacen)
            .group_by(Stock.codigo_producto, Product.nombre_corto)
        )
        stock = db.exec(statement).all()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return [
        StockByWarehousePieChart(
            codigo_producto=row.codigo_producto,
            nombre_producto=row.nombre_corto,
            cantidad_total=row.cantidad_total,
        )
        for row in stock
    ]


@router.get(
    "/producto/caducidad",
    response_model=PaginatedStockResponse,
)
def get_stock_by_product_expiration_date(
    desde: int = Query(0, ge=0),
    hasta: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el stock total de los productos con fecha de caducidad próxima a vencimiento."""
    try:
        fecha_desde = datetime.date.today() + relativedelta(months=desde)
        fecha_hasta = fecha_desde + relativedelta(months=hasta)

        statement = (
            select(
                Stock.codigo_almacen,
                Warehouse.descripcion,
                Stock.codigo_producto,
                Product.nombre_corto,
                Product.sku,
                Stock.lote,
                Stock.fecha_cad,
                Stock.cantidad,
            )
            .join(Warehouse, Warehouse.codigo == Stock.codigo_almacen)
            .join(Product, Product.codigo == Stock.codigo_producto)
            .where(
                Stock.fecha_cad > fecha_desde,
                Stock.fecha_cad <= fecha_hasta,
                Stock.cantidad > 0,
            )
        )
        stock = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockResponse(
        data=[
            StockResponse(
                codigo_almacen=item.codigo_almacen,
                nombre_almacen=item.descripcion,
                codigo_producto=item.codigo_producto,
                nombre_producto=item.nombre_corto,
                sku=item.sku,
                lote=item.lote,
                fecha_cad=item.fecha_cad,
                cantidad=item.cantidad,
            )
            for item in stock
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/producto/{codigo_producto}",
    response_model=PaginatedStockSummary,
)
def get_stock_by_product(
    codigo_producto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el stock total de un producto en todos los almacenes."""
    try:
        statement = (
            select(
                Stock.codigo_producto,
                Stock.codigo_almacen,
                Warehouse.descripcion.label("nombre_almacen"),
                func.sum(Stock.cantidad).label("total_cantidad"),
            )
            .join(Warehouse, Warehouse.codigo == Stock.codigo_almacen)
            .where(Stock.codigo_producto == codigo_producto)
            .group_by(
                Stock.codigo_producto, Stock.codigo_almacen, Warehouse.descripcion
            )
        )
        stock_summary = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockSummary(
        data=[
            StockSummary(
                codigo_producto=item.codigo_producto,
                codigo_almacen=item.codigo_almacen,
                nombre_almacen=item.nombre_almacen,
                total_cantidad=item.total_cantidad,
            )
            for item in stock_summary
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/almacen/{codigo_almacen}/producto/{codigo_producto}",
    response_model=PaginatedStockResponse,
)
def get_stock_by_warehouse_and_product(
    codigo_almacen: int,
    codigo_producto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el stock de un producto en un almacén específico."""
    try:
        statement = (
            select(
                Stock.codigo_almacen,
                Warehouse.descripcion,
                Stock.codigo_producto,
                Product.nombre_corto,
                Product.sku,
                Stock.lote,
                Stock.fecha_cad,
                Stock.cantidad,
            )
            .join(Warehouse, Warehouse.codigo == Stock.codigo_almacen)
            .join(Product, Product.codigo == Stock.codigo_producto)
            .where(
                Stock.codigo_almacen == codigo_almacen,
                Stock.codigo_producto == codigo_producto,
            )
        )
        stock = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockResponse(
        data=[
            StockResponse(
                codigo_almacen=item.codigo_almacen,
                nombre_almacen=item.descripcion,
                codigo_producto=item.codigo_producto,
                nombre_producto=item.nombre_corto,
                sku=item.sku,
                lote=item.lote,
                fecha_cad=item.fecha_cad,
                cantidad=item.cantidad,
            )
            for item in stock
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/historial", response_model=PaginatedStockHistory)
def get_stock_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el historial de movimientos de stock."""
    try:
        statement = (
            select(
                Movement.id_mov,
                Movement.fecha,
                Movement.tipo,
                MovementLine.codigo_almacen,
                MovementLine.codigo_producto,
                Product.sku,
                MovementLine.lote,
                MovementLine.cantidad,
                User.nombre.label("usuario"),
            )
            .join(
                MovementLine, Movement.id_mov == MovementLine.id_mov
            )  # Relacionamos movimientos con líneas
            .join(User, Movement.id_usuario == User.id)  # Relacionamos con el usuario
            .join(
                Product, Product.codigo == MovementLine.codigo_producto
            )  # Relacionamos con el producto
            .order_by(Movement.fecha.desc())  # Ordenamos por fecha más reciente primero
        )
        history = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockHistory(
        data=[
            StockHistory(
                id_movimiento=item.id_mov,
                fecha=item.fecha,
                tipo=item.tipo,
                codigo_almacen=item.codigo_almacen,
                codigo_producto=item.codigo_producto,
                sku_producto=item.sku,
                lote=item.lote,
                cantidad=item.cantidad,
                usuario=item.usuario,
            )
            for item in history
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/producto/{codigo_producto}/historial", response_model=PaginatedStockHistory
)
def get_product_stock_history(
    codigo_producto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el historial de movimientos de stock por producto."""
    try:
        statement = (
            select(
                Movement.id_mov,
                Movement.fecha,
                Movement.tipo,
                MovementLine.codigo_almacen,
                MovementLine.codigo_producto,
                Product.sku,
                MovementLine.lote,
                MovementLine.cantidad,
                User.nombre.label("usuario"),
            )
            .join(MovementLine, Movement.id_mov == MovementLine.id_mov)
            .join(User, Movement.id_usuario == User.id)
            .join(Product, Product.codigo == MovementLine.codigo_producto)
            .where(Product.codigo == codigo_producto)
            .order_by(Movement.fecha.desc(), MovementLine.lote)
        )
        history = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockHistory(
        data=[
            StockHistory(
                id_movimiento=item.id_mov,
                fecha=item.fecha,
                tipo=item.tipo,
                codigo_almacen=item.codigo_almacen,
                codigo_producto=item.codigo_producto,
                sku_producto=item.sku,
                lote=item.lote,
                cantidad=item.cantidad,
                usuario=item.usuario,
            )
            for item in history
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/almacen/{codigo_almacen}/historial", response_model=PaginatedStockHistory)
def get_warehouse_stock_history(
    codigo_almacen: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el historial de movimientos de stock por almacen."""
    try:
        statement = (
            select(
                Movement.id_mov,
                Movement.fecha,
                Movement.tipo,
                MovementLine.codigo_almacen,
                MovementLine.codigo_producto,
                Product.sku,
                MovementLine.lote,
                MovementLine.cantidad,
                User.nombre.label("usuario"),
            )
            .join(MovementLine, Movement.id_mov == MovementLine.id_mov)
            .join(User, Movement.id_usuario == User.id)
            .join(Product, Product.codigo == MovementLine.codigo_producto)
            .where(MovementLine.codigo_almacen == codigo_almacen)
            .order_by(Movement.fecha.desc(), MovementLine.lote)
        )
        history = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockHistory(
        data=[
            StockHistory(
                id_movimiento=item.id_mov,
                fecha=item.fecha,
                tipo=item.tipo,
                codigo_almacen=item.codigo_almacen,
                codigo_producto=item.codigo_producto,
                sku_producto=item.sku,
                lote=item.lote,
                cantidad=item.cantidad,
                usuario=item.usuario,
            )
            for item in history
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/almacen/{codigo_almacen}/producto/{codigo_producto}/historial",
    response_model=PaginatedStockHistory,
)
def get_warehouse_and_product_stock_history(
    codigo_producto: int,
    codigo_almacen: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Consulta el historial de movimientos de stock por almacen y por producto."""
    try:
        statement = (
            select(
                Movement.id_mov,
                Movement.fecha,
                Movement.tipo,
                MovementLine.codigo_almacen,
                MovementLine.codigo_producto,
                Product.sku,
                MovementLine.lote,
                MovementLine.cantidad,
                User.nombre.label("usuario"),
            )
            .join(MovementLine, Movement.id_mov == MovementLine.id_mov)
            .join(User, Movement.id_usuario == User.id)
            .join(Product, Product.codigo == MovementLine.codigo_producto)
            .where(
                Product.codigo == codigo_producto,
                MovementLine.codigo_almacen == codigo_almacen,
            )
            .order_by(Movement.fecha.desc(), MovementLine.lote)
        )
        history = db.exec(statement.limit(limit).offset(offset)).all()
        total_records = db.exec(
            select(func.count()).select_from(statement.subquery())
        ).first()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    return PaginatedStockHistory(
        data=[
            StockHistory(
                id_movimiento=item.id_mov,
                fecha=item.fecha,
                tipo=item.tipo,
                codigo_almacen=item.codigo_almacen,
                codigo_producto=item.codigo_producto,
                sku_producto=item.sku,
                lote=item.lote,
                cantidad=item.cantidad,
                usuario=item.usuario,
            )
            for item in history
        ],
        total=total_records or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/semaforo")
def get_stock_status_semaforo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el estado del stock segmentado por vencimiento (semáforo) — total de unidades."""

    try:
        hoy = datetime.date.today()
        en_1_mes = hoy + relativedelta(months=1)
        en_6_meses = hoy + relativedelta(months=6)

        caduca_ya = (
            db.exec(
                select(func.sum(Stock.cantidad)).where(
                    Stock.fecha_cad != None,
                    Stock.fecha_cad > hoy,
                    Stock.fecha_cad <= en_1_mes,
                )
            ).first()
            or 0
        )

        caduca_proximamente = (
            db.exec(
                select(func.sum(Stock.cantidad)).where(
                    Stock.fecha_cad > en_1_mes,
                    Stock.fecha_cad <= en_6_meses,
                )
            ).first()
            or 0
        )

        no_caduca = (
            db.exec(
                select(func.sum(Stock.cantidad)).where(
                    (Stock.fecha_cad == None) | (Stock.fecha_cad > en_6_meses)
                )
            ).first()
            or 0
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Error de conexión con la base de datos",
        )

    return {
        "caduca_ya": caduca_ya,
        "caduca_proximamente": caduca_proximamente,
        "no_caduca": no_caduca,
    }


@router.get("/almacenes/detalle", response_model=List[StockByWarehouse])
def get_warehouse_detail(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta la cantidad total de stock de todos los productos, agrupado por almacén."""
    try:
        statement = (
            select(
                Stock.codigo_almacen,
                Warehouse.descripcion,
                func.sum(Stock.cantidad).label("total_cantidad"),
            )
            .join(Warehouse, Warehouse.codigo == Stock.codigo_almacen)
            .group_by(Stock.codigo_almacen, Warehouse.codigo)
        )
        data = db.exec(statement).all()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    result = [
        StockByWarehouse(
            codigo_almacen=item.codigo_almacen,
            nombre_almacen=item.descripcion,
            total_cantidad=item.total_cantidad,
        )
        for item in data
    ]

    return result


@router.get("/categorias-producto", response_model=List[StockByCategory])
def get_stock_by_product_category(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve la cantidad total de stock agrupado por categoría de producto.
    """
    try:
        statement = (
            select(
                ProductCategory.id,
                ProductCategory.nombre,
                func.sum(Stock.cantidad).label("cantidad_total"),
            )
            .join(Product, ProductCategory.id == Product.id_categoria)
            .join(Stock, Stock.codigo_producto == Product.codigo)
            .group_by(ProductCategory.id, ProductCategory.nombre)
            .order_by(ProductCategory.nombre)
        )
        resultados = db.exec(statement).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Error al obtener stock por categoría",
        )

    return [
        StockByCategory(
            id_categoria=row.id,
            nombre_categoria=row.nombre,
            cantidad_total=row.cantidad_total,
        )
        for row in resultados
    ]


@router.get(
    "/categoria/{id_categoria}/productos", response_model=List[StockByProductInCategory]
)
def get_stock_by_category_detail(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve la cantidad total de stock por producto dentro de una categoría concreta.
    """
    try:
        statement = (
            select(
                Product.codigo,
                Product.nombre_corto,
                func.sum(Stock.cantidad).label("cantidad_total"),
            )
            .join(Stock, Stock.codigo_producto == Product.codigo)
            .where(Product.id_categoria == id_categoria)
            .group_by(Product.codigo, Product.nombre_corto)
            .order_by(Product.nombre_corto)
        )
        resultados = db.exec(statement).all()
    except SQLAlchemyError:
        raise HTTPException(
            500, detail="Error al obtener stock por producto en la categoría"
        )

    return [
        StockByProductInCategory(
            codigo_producto=row.codigo,
            nombre_producto=row.nombre_corto,
            cantidad_total=row.cantidad_total,
        )
        for row in resultados
    ]


@router.get("/lotes-disponibles", response_model=list[LoteDisponibleResponse])
def get_lotes_disponibles(
    producto: int = Query(..., gt=0),
    almacen: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve los lotes disponibles para un producto en un almacén.
    Solo se incluyen lotes con stock > 0.
    """

    try:
        statement = (
            select(
                Stock.lote, Stock.fecha_cad, func.sum(Stock.cantidad).label("cantidad")
            )
            .where(Stock.codigo_producto == producto)
            .where(Stock.codigo_almacen == almacen)
            .where(Stock.cantidad > 0)
            .group_by(Stock.lote, Stock.fecha_cad)
            .order_by(Stock.fecha_cad)
        )

        results = db.exec(statement).all()

        return [
            LoteDisponibleResponse(
                lote=row.lote or "SIN_LOTE",
                fecha_cad=row.fecha_cad,
                cantidad=row.cantidad,
            )
            for row in results
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los lotes disponibles",
        )
