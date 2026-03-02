import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from fastapi.exception_handlers import http_exception_handler

# Import routers de los módulos
from app.modulos.inicio.router import router as inicio_router
from app.modulos.auth.router import router as auth_router
from app.modulos.doccheck.router import router as doccheck_router
from app.modulos.bpsearch.router import router as bpsearch_router
from app.modulos.datamask.router import router as datamask_router
from app.modulos.scadbot.router import router as scadbot_router
from app.modulos.signa.router import router as signa_router
from app.modulos.autodoc.router import router as autodoc_router
from app.modulos.scandoc.router import router as scandoc_router
from app.modulos.seace.router import router as seace_router
from app.modulos.piloto.router import router as piloto_router
from app.modulos.boletin.router import router as boletin_router

# Importar modelos para que SQLAlchemy los detecte al crear la BD
from app.modulos.auth import models as auth_models
from app.modulos.doccheck import models as doccheck_models
from app.core.database import SessionLocal
from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Inicializar la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Portal Corporativo Modular construido con FastAPI"
)

# --- Manejador de Excepciones Global ---
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return await http_exception_handler(request, exc)

# --- Middleware de Contexto de Usuario Global ---
@app.middleware("http")
async def add_user_context(request: Request, call_next):
    # 1. Intentar leer cookie
    token = request.cookies.get("access_token")
    request.state.user = None
    
    if token and token.startswith("user:"):
        username = token.split(":")[1]
        
        # 2. Consultar BD (Scope pequeño)
        db = SessionLocal()
        try:
            user = db.query(auth_models.User).filter(auth_models.User.username == username).first()
            if user:
                request.state.user = user
        except Exception:
            pass # Si falla la BD, seguimos sin usuario
        finally:
            db.close()
            
    response = await call_next(request)
    return response

# Configuración de Recursos Estáticos
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

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
app.include_router(autodoc_router)
app.include_router(scandoc_router)
app.include_router(seace_router)
app.include_router(piloto_router)
app.include_router(boletin_router)

if __name__ == "__main__":
    # Permite ejecutar el script directamente para desarrollo
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
