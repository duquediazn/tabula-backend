from app.utils.validation import normalize_category
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional

from app.models.database import get_db
from app.models.product_category import ProductCategory
from app.models.product import Product
from app.schemas.product_category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    PaginatedCategoryResponse,
)
from app.dependencies import require_admin

router = APIRouter(prefix="/categorias", tags=["Categorías de Producto"])


@router.get("/", response_model=PaginatedCategoryResponse)
def list_categories(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    try:
        statement = select(ProductCategory).order_by(ProductCategory.nombre)
        categorias = db.exec(statement.limit(limit).offset(offset)).all()
        total = db.exec(select(func.count()).select_from(ProductCategory)).first()
    except SQLAlchemyError:
        raise HTTPException(500, detail="Error al obtener las categorías")
    return {"data": categorias, "total": total, "limit": limit, "offset": offset}


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    categoria = ProductCategory(nombre=normalize_category(data.nombre))

    try:
        db.add(categoria)
        db.flush() 
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail="Ya existe una categoría con ese nombre")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Error interno al crear la categoría")

    return categoria


@router.put("/{id}", response_model=CategoryResponse)
def update_category(
    id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    categoria = db.get(ProductCategory, id)
    if not categoria:
        raise HTTPException(404, detail="Categoría no encontrada")

    if data.nombre:
        categoria.nombre = normalize_category(data.nombre)

    try:
        db.add(categoria)
        db.flush() 
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, detail="Ya existe otra categoría con ese nombre")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Error al actualizar la categoría")

    return categoria


@router.delete("/{id}", response_model=CategoryResponse)
def delete_category(
    id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    categoria = db.get(ProductCategory, id)
    if not categoria:
        raise HTTPException(404, detail="Categoría no encontrada")

    # Validar que no haya productos asociados
    productos = db.exec(select(Product).where(Product.id_categoria == id)).first()
    if productos:
        raise HTTPException(
            400,
            detail="No se puede eliminar esta categoría porque tiene productos asociados",
        )

    try:
        db.delete(categoria)
        db.flush() 
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Error al eliminar la categoría")

    return categoria
