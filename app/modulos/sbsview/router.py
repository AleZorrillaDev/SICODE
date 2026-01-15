from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from .service import obtener_datos_sbs
import datetime

router = APIRouter(
    prefix="/sbsview",
    tags=["sbsview"]
)

from app.core.config import settings

# Usamos la config centralizada para rutas (robusto para .exe)
SBSVIEW_TEMPLATES = settings.get_template_path("app/modulos/sbsview/templates")
INICIO_TEMPLATES = settings.get_template_path("app/modulos/inicio/templates")

templates = Jinja2Templates(directory=[SBSVIEW_TEMPLATES, INICIO_TEMPLATES])

@router.get("/")
async def sbs_monitor(request: Request):
    """
    Vista principal del Monitor SBS.
    """
    # Obtenemos los datos frescos del servicio
    data = obtener_datos_sbs()
    
    # Fecha/Hora para mostrar "Vigente al..."
    timestamp_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return templates.TemplateResponse(
        "sbsview/sbsview_main.html", 
        {
            "request": request, 
            "data": data,
            "timestamp_str": timestamp_str
        }
    )

from fastapi.responses import StreamingResponse
from .ruc_agent import buscar_y_guardar_ruc
import time
import json

@router.get("/stream_ruc_updates")
async def stream_ruc_updates(names: str):
    """
    SSE Endpoint. Recibe lista de nombres separados por comas.
    Busca RUCs 1 a 1 y emite eventos.
    """
    lista_nombres = names.split(",")
    total = len(lista_nombres)
    
    async def event_generator():
        for i, nombre_raw in enumerate(lista_nombres):
            nombre = nombre_raw.strip()
            if not nombre: continue
            
            # Buscamos RUC (Esto tarda 1-2s aprox)
            nuevo_ruc = buscar_y_guardar_ruc(nombre)
            
            # Preparamos data JSON
            data = json.dumps({
                "nombre": nombre,
                "ruc": nuevo_ruc,
                "progress": int(((i + 1) / total) * 100)
            })
            
            yield f"data: {data}\n\n"
            # Pequeña pausa para no saturar si fuera muy rapido
            # (con requests HTTP ya hay lag natural)
            
        yield "event: close\ndata: close\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/reset_cache")
async def reset_cache():
    """
    Elimina el archivo de cache para forzar recarga.
    """
    from .ruc_agent import CACHE_FILE
    import os
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            return {"status": "ok", "msg": "Cache eliminada"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}
    return {"status": "ok", "msg": "No existía cache"}
