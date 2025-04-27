from typing import Optional
from app.models.product_category import ProductCategory
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.dependencies import require_admin
from app.models.database import get_db
from app.models.product import Product
from app.models.stock import Stock
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.product import (
    EstadoMultipleRequest,
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.utils.validation import is_admin_user

router = APIRouter(prefix="/productos", tags=["Productos"])


@router.get("/", response_model=PaginatedProductResponse)
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    id_categoria: Optional[int] = Query(None),
    estado: Optional[bool] = Query(None),
):
    """Lista todos los productos.
    - Un **admin** ve todos los productos (activos e inactivos).
    - Un **usuario normal** solo ve los productos activos.
    """
    try:
        statement = select(Product, ProductCategory.nombre).join(
            ProductCategory, Product.id_categoria == ProductCategory.id
        )

        if search:
            # Filtra por nombre o sku (mayúsculas o minúsculas)
            search_like = f"%{search.lower()}%"
            statement = statement.where(
                func.lower(Product.nombre_corto).ilike(search_like)
                | func.lower(Product.sku).ilike(search_like)
            )

        # Filtra por categoría
        if id_categoria:
            statement = statement.where(Product.id_categoria == int(id_categoria))

        # Filtro por estado (activo/inactivo), solo para admin
        if is_admin_user(current_user) and estado is not None:
            statement = statement.where(Product.activo == estado)
        elif not is_admin_user(current_user):
            # Para usuarios normales, siempre filtra por productos activos
            statement = statement.where(Product.activo == True)

        # Consulta paginada y ordenada
        products_raw = db.exec(
            statement.order_by(Product.nombre_corto).limit(limit).offset(offset)
        ).all()

        # Conteo total SIN paginar
        total_records = (
            db.exec(select(func.count()).select_from(statement.subquery())).first() or 0
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    # Formatear respuesta
    products = [
        {**product.__dict__, "nombre_categoria": nombre_categoria}
        for product, nombre_categoria in products_raw
    ]

    return {
        "data": products,
        "total": total_records,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{id}", response_model=ProductResponse)
def get_product(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene un producto específico por su ID.
    - Usuarios normales solo pueden ver productos activos.
    - Admins pueden ver cualquier producto.
    """
    try:
        statement = (
            select(Product, ProductCategory.nombre)
            .join(ProductCategory, Product.id_categoria == ProductCategory.id)
            .where(Product.codigo == id)
        )
        result = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if not result:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product, nombre_categoria = result

    if not is_admin_user(current_user) and not product.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este producto",
        )

    return {
        **product.model_dump(),
        "nombre_categoria": nombre_categoria,
    }


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # Verifica si el usuario es admin
):
    """Crea un nuevo producto (solo admin)."""

    # Verificar si el SKU ya existe
    try:
        statement = select(Product).where(Product.sku == product_data.sku)
        existing_product = db.exec(statement).first()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El SKU ya está registrado."
        )

    categoria = db.get(ProductCategory, product_data.id_categoria)
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La categoría especificada no existe.",
        )

    # Crear producto
    new_product = Product(
        sku=product_data.sku,
        nombre_corto=product_data.nombre_corto,
        descripcion=product_data.descripcion,
        id_categoria=product_data.id_categoria,
    )

    try:
        db.add(new_product)
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
            detail="Error interno al actualizar el producto.",
        )
    db.commit()
    db.refresh(new_product)

    return {**new_product.model_dump(), "nombre_categoria": categoria.nombre}


@router.put("/estado-multiple", status_code=200)
def cambiar_estado_masivo_productos(
    data: EstadoMultipleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        productos = db.exec(
            select(Product).where(Product.codigo.in_(data.codigos))
        ).all()

        actualizados = []

        for producto in productos:
            if producto.activo == data.activo:
                continue

            if data.activo is False:
                stock_total = (
                    db.exec(
                        select(func.sum(Stock.cantidad)).where(
                            Stock.codigo_producto == producto.codigo
                        )
                    ).first()
                    or 0
                )

                if stock_total > 0:
                    continue  # Producto aún tiene stock, no se puede desactivar

            producto.activo = data.activo
            db.add(producto)
            actualizados.append(producto)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Error al actualizar productos")

    db.commit()
    return {
        "mensaje": f"{len(actualizados)} productos actualizados",
        "omitidos": len(data.codigos) - len(actualizados),
    }


@router.put("/{id}", response_model=ProductResponse)
def update_product(
    id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Permite actualizar un producto (cualquier usuario puede hacerlo, pero solo admin cambia `activo`)."""

    try:
        # Buscar el producto en la base de datos
        statement = select(Product).where(Product.codigo == id)
        product = db.exec(statement).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )
        # Validar si el nuevo SKU ya existe en otro producto
        if product_update.sku:
            statement = select(Product).where(
                Product.sku == product_update.sku, Product.codigo != id
            )
            existing_product = db.exec(statement).first()
            if existing_product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El SKU ya está en uso",
                )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    # Aplicar cambios solo si se envían
    if product_update.sku:
        product.sku = product_update.sku
    if product_update.nombre_corto:
        product.nombre_corto = product_update.nombre_corto
    if product_update.descripcion:
        product.descripcion = product_update.descripcion
    if product_update.id_categoria:
        categoria = db.get(ProductCategory, product_update.id_categoria)
        if not categoria:
            raise HTTPException(404, detail="La categoría especificada no existe.")
        product.id_categoria = product_update.id_categoria

    # Solo admin puede cambiar el estado `activo`
    if product_update.activo is not None:
        if not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para cambiar el estado del producto",
            )
        product.activo = product_update.activo

    try:
        # Guardar cambios en la base de datos
        db.add(product)
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
            detail="Error interno al actualizar el producto.",
        )
    db.commit()

    categoria = db.get(ProductCategory, product.id_categoria)

    return {**product.model_dump(), "nombre_categoria": categoria.nombre}


@router.delete("/{id}", response_model=ProductResponse)
def delete_product(
    id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    """Permite a un admin eliminar un producto."""

    try:
        statement = select(Product).where(Product.codigo == id)
        product = db.exec(statement).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado"
            )
        categoria = db.get(ProductCategory, product.id_categoria)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de conexión con la base de datos",
        )

    try:
        db.delete(product)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Este producto tiene movimientos asociados, no se puede eliminar.",
        )

    return {**product.model_dump(), "nombre_categoria": categoria.nombre}
