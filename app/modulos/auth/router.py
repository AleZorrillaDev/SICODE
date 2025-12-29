from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=["app/modulos/auth/templates"])

@router.get("/login", name="auth.login")
async def login_page(request: Request):
    """
    Muestra la página de inicio de sesión.
    """
    return templates.TemplateResponse("auth/login.html", {
        "request": request
    })

@router.post("/login", name="auth.login_post")
async def login_submit(request: Request):
    """
    Procesa el inicio de sesión (Placeholder).
    """
    # Aquí iría la lógica real de autenticación
    # Por ahora renderizamos la misma página
    return templates.TemplateResponse("auth/login.html", {
        "request": request
    })
