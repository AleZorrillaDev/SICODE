from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.core.config import settings
import asyncio
from functools import partial
from .service import obtener_datos_sbs
from datetime import datetime

router = APIRouter(prefix="/sbsview", tags=["sbsview"])

templates_dir = settings.get_template_path("app/modulos/sbsview/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir, templates_base])

@router.get("/")
async def sbsview_home(request: Request):
    # Ejecutar el scraping en un thread separado para no bloquear el loop
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, obtener_datos_sbs)
    
    # Fecha formateada: "12 de Enero de 2026 - 10:15 AM"
    now = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    fecha_str = f"{now.day} de {meses[now.month-1]} de {now.year} - {now.strftime('%I:%M %p')}"

    return templates.TemplateResponse(
        "sbsview/sbsview_main.html", 
        {
            "request": request, 
            "data": data,
            "timestamp_str": fecha_str
        }
    )
