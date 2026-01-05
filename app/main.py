import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base

# Import routers de los módulos
from app.modulos.inicio.router import router as inicio_router
from app.modulos.auth.router import router as auth_router
from app.modulos.doccheck.router import router as doccheck_router
from app.modulos.bpsearch.router import router as bpsearch_router
from app.modulos.datamask.router import router as datamask_router
from app.modulos.scadbot.router import router as scadbot_router
from app.modulos.signa.router import router as signa_router

# Inicializar la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Portal Corporativo Modular construido con FastAPI"
)

# Configuración de Recursos Estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configuración de Base de Datos
Base.metadata.create_all(bind=engine)

# Inclusión de Rutas (Módulos)
app.include_router(inicio_router, tags=["Inicio"])
app.include_router(auth_router, tags=["Autenticación"])
app.include_router(doccheck_router)
app.include_router(bpsearch_router)
app.include_router(datamask_router)
app.include_router(scadbot_router)
app.include_router(signa_router)

if __name__ == "__main__":
    # Permite ejecutar el script directamente para desarrollo
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
