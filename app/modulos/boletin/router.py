"""
Boletin Router - Endpoints para gestión de PDFs del Boletín Oficial
"""
from fastapi import APIRouter, Request, Query, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import os
import io

from .processor import BoletinProcessor
from app.modulos.auth.dependencies import login_required
from fastapi import Depends

router = APIRouter(
    prefix="/boletin", 
    tags=["boletin"],
    dependencies=[Depends(login_required)]
)

from app.core.config import settings
templates_dir = settings.get_template_path("app/modulos/boletin/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir, templates_base])

# Instancia global del procesador
processor = BoletinProcessor()

from pydantic import BaseModel
from typing import List

class SearchBulkRequest(BaseModel):
    palabra: str
    pdfs: List[dict]

@router.get("/")
async def boletin_home(request: Request):
    """Renderiza la página principal con el calendario"""
    return templates.TemplateResponse("boletin/index.html", {"request": request})

@router.post("/api/search-bulk")
async def search_bulk(data: SearchBulkRequest):
    """Realiza una búsqueda masiva en una lista de PDFs"""
    def event_generator():
        for update in processor.buscar_palabra_en_pdfs(data.pdfs, data.palabra):
            import json
            yield f"data: {json.dumps(update)}\n\n"
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.get("/api/calendar")
async def get_calendar_data(anio: str, mes: str):
    """Obtiene los PDFs disponibles para un mes y año"""
    pdfs = processor.obtener_pdfs_mes(anio, mes)
    return {"status": "success", "data": pdfs}

@router.get("/api/view")
async def view_pdf(
    url: str = Query(...), 
    fecha: str = Query(None), 
    titulo: str = Query(None),
    highlight: str = Query(None)
):
    """
    Muestra un PDF. Si highlight está presente, resalta la palabra en el PDF.
    """
    try:
        local_path = processor.obtener_ruta_local(fecha, titulo) if (fecha and titulo) else None
        if not local_path:
            local_path = processor.descargar_pdf(url, fecha, titulo)
            
        import fitz
        if highlight:
            # Abrir el PDF original
            doc = fitz.open(local_path)
            palabra_norm = processor._normalizar_texto(highlight)
            
            # Resaltar en todas las páginas
            for pagina in doc:
                # Buscar instancias de la palabra (usando lógica relax)
                instancias = pagina.search_for(highlight, quads=True)
                for quad in instancias:
                    annot = pagina.add_highlight_annot(quad)
                    annot.set_colors(stroke=(1, 1, 0)) # Amarillo
                    annot.update()
            
            # Guardar en memoria para no modificar el cache
            out_pdf_bytes = doc.write()
            doc.close()
            
            return Response(
                content=out_pdf_bytes,
                media_type="application/pdf"
            )
        else:
            file_bytes = processor.get_file_bytes(local_path)
            return Response(
                content=file_bytes, 
                media_type="application/pdf"
            )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/api/download")
async def download_pdf(
    url: str = Query(...), 
    fecha: str = Query(None), 
    titulo: str = Query(None)
):
    """Descarga forzada del PDF"""
    try:
        local_path = processor.obtener_ruta_local(fecha, titulo) if (fecha and titulo) else None
        if not local_path:
            local_path = processor.descargar_pdf(url, fecha, titulo)
            
        file_bytes = processor.get_file_bytes(local_path)
        filename = os.path.basename(local_path)
        
        return Response(
            content=file_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
