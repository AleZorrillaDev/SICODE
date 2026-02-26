from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.modulos.auth.dependencies import login_required

# Se inicializa el router. 
# El prefijo y tags se pueden definir aquí o en el include_router en main.py
router = APIRouter(dependencies=[Depends(login_required)])

# Configuración de templates locales para este módulo
# Nota: Jinja2 busca en carpetas 'templates'. Al montar el sistema, 
# se puede centralizar, pero aquí seguimos la estructura modular si se prefiere.
# Sin embargo, para simplicidad y herencia, usaremos la configuración global de templates
# si apuntan al mismo directorio base o se añaden rutas. 
# Para este diseño, asumiremos que 'app/templates' es la base, y cada módulo puede tener
# sus templates ahí o usar una configuración de directorios múltiples.
# FASTAPI permite pasar una lista de directorios a Jinja2Templates.

# Opción A: Un solo directorio de templates global 'app/templates' y subcarpetas para módulos.
# Opción B: Múltiples directorios.
# Usaremos Opción B para aislamiento real.

from app.core.config import settings

# Usamos la función de configuración para obtener la ruta absoluta correcta (soporte EXE)
templates_dir = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir])

@router.get("/", name="inicio.index")
async def pagina_inicio(request: Request):
    """
    Renderiza la página de inicio del sistema.
    """
    return templates.TemplateResponse("inicio/index.html", {
        "request": request, 
        "titulo": "Panel Principal"
    })
