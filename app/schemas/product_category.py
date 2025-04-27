from pydantic import BaseModel, Field
from typing import List, Optional

class CategoryBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        orm_mode = True

class PaginatedCategoryResponse(BaseModel):
    data: List[CategoryResponse]
    total: int
    limit: int
    offset: int

    class Config:
        orm_mode = True