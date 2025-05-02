from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.models.database import create_db_and_tables
from app.routers import (
    auth,
    movements,
    product_categories,
    products,
    users,
    stock,
    warehouses,
)
from fastapi.middleware.cors import CORSMiddleware  # CORS
from app.routers.websocket import router as websocket_router


# Crear la base de datos y las tablas al iniciar la aplicación
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield  # Aquí se pueden cerrar conexiones u otros recursos


app = FastAPI(lifespan=lifespan)

# Configuración CORS segura para cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://tabula-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(movements.router)
app.include_router(warehouses.router)
app.include_router(stock.router)
app.include_router(product_categories.router)
# Websocket
app.include_router(websocket_router)


@app.get("/")
def read_root():
    return {"message": "API funcionando correctamente"}
