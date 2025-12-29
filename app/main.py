import uvicorn
import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Importar configuración global
from app.core.config import settings
from app.core.database import engine, Base

# Importar routers de los módulos
from app.modulos.inicio.router import router as inicio_router

# Inicializar la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Portal Corporativo Modular construido con FastAPI"
)

# --------------------------------------------------------------------------
# Configuración de Recursos Estáticos
# --------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --------------------------------------------------------------------------
# Configuración de Base de Datos
# --------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------------
# Inclusión de Rutas (Módulos)
# --------------------------------------------------------------------------
# Módulo Inicio (Ruta raíz)
app.include_router(inicio_router, tags=["Inicio"])

# Módulo Auth (Login)
# Módulo Auth (Login)
from app.modulos.auth.router import router as auth_router
app.include_router(auth_router, tags=["Autenticación"])

# Módulo DocCheck
from app.modulos.doccheck.router import router as doccheck_router
app.include_router(doccheck_router)


if __name__ == "__main__":
    # Permite ejecutar el script directamente para desarrollo
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
