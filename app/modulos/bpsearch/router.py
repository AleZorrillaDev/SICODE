"""
BPSearch Router - Endpoints para búsqueda en Boletín El Peruano
"""
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import json

# Imports para funcionalidad nativa local
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None

from .processor import BPSearchProcessor

router = APIRouter(prefix="/bpsearch", tags=["bpsearch"])

from app.core.config import settings
templates_dir = settings.get_template_path("app/modulos/bpsearch/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir, templates_base])

# Instancia global del procesador (para demo - en producción usar sesiones)
processor_instance: Optional[BPSearchProcessor] = None
search_generator = None


class SearchRequest(BaseModel):
    carpeta: str
    palabra: str
    incluir_subcarpetas: bool = False
    ignorar_historial: bool = False


class FolderRequest(BaseModel):
    carpeta: str



@router.get("/select-folder-dialog")
def select_folder_dialog():
    """Abre un diálogo nativo del sistema para seleccionar carpeta (solo funciona en local)"""
    if tk is None:
         return {"status": "error", "message": "Tkinter no está instalado en el servidor"}

    try:
        # Create a hidden root window
        root = tk.Tk()
        root.withdraw() # Hide the main window
        root.attributes('-topmost', True) # Make dialog appear on top
        
        # Open directory selector
        carpeta = filedialog.askdirectory(title="Seleccionar Carpeta para BPSearch")
        
        root.destroy() # Cleanup
        
        if carpeta:
            # Update global state
            global processor_instance
            if processor_instance is None:
                processor_instance = BPSearchProcessor()
            
            if processor_instance.set_carpeta(carpeta):
                pdfs = processor_instance.obtener_pdfs(incluir_subcarpetas=False)
                pdfs_sub = processor_instance.obtener_pdfs(incluir_subcarpetas=True)
                
                return {
                    "status": "success", 
                    "carpeta": carpeta, 
                    "pdfs_carpeta": len(pdfs), 
                    "pdfs_total": len(pdfs_sub)
                }
            else:
                 return {"status": "error", "message": "La carpeta seleccionada no es válida"}
        else:
            return {"status": "cancelled", "message": "No se seleccionó ninguna carpeta"}
            
    except Exception as e:
        return {"status": "error", "message": f"Error abriendo diálogo nativo: {str(e)}"}


@router.get("/")
async def bpsearch_home(request: Request):
    return templates.TemplateResponse("bpsearch/index.html", {"request": request})


@router.post("/set-folder")
async def set_folder(data: FolderRequest):
    """Establece la carpeta de búsqueda"""
    global processor_instance
    
    if processor_instance is None:
        processor_instance = BPSearchProcessor()
    
    if processor_instance.set_carpeta(data.carpeta):
        # Contar PDFs disponibles
        pdfs = processor_instance.obtener_pdfs(incluir_subcarpetas=False)
        pdfs_sub = processor_instance.obtener_pdfs(incluir_subcarpetas=True)
        
        return {
            "status": "success",
            "carpeta": data.carpeta,
            "pdfs_carpeta": len(pdfs),
            "pdfs_total": len(pdfs_sub)
        }
    else:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Carpeta no válida"}
        )


@router.post("/search")
async def start_search(data: SearchRequest):
    """Inicia una búsqueda SSE (Server-Sent Events)"""
    global processor_instance, search_generator
    
    if processor_instance is None:
        processor_instance = BPSearchProcessor()
    
    if not processor_instance.set_carpeta(data.carpeta):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Carpeta no válida"}
        )
    
    # Crear el generador de búsqueda
    search_generator = processor_instance.buscar_palabra(
        palabra=data.palabra,
        incluir_subcarpetas=data.incluir_subcarpetas,
        ignorar_historial=data.ignorar_historial
    )
    
    return {"status": "started", "message": "Búsqueda iniciada"}


@router.get("/search-stream")
def search_stream():
    """Stream de eventos SSE para la búsqueda"""
    global search_generator
    
    def event_generator():
        if search_generator is None:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No hay búsqueda activa'})}\n\n"
            return
        
        try:
            for evento in search_generator:
                yield f"data: {json.dumps(evento)}\n\n"
                # No necesitamos sleep aquí si es síncrono en threadpool
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Nginx
        }
    )


@router.post("/pause")
async def pause_search():
    """Pausa la búsqueda"""
    global processor_instance
    
    if processor_instance:
        processor_instance.pausar()
        return {"status": "paused"}
    return {"status": "error", "message": "No hay búsqueda activa"}


@router.post("/resume")
async def resume_search():
    """Reanuda la búsqueda"""
    global processor_instance
    
    if processor_instance:
        processor_instance.continuar()
        return {"status": "resumed"}
    return {"status": "error", "message": "No hay búsqueda activa"}


@router.post("/cancel")
async def cancel_search():
    """Cancela la búsqueda"""
    global processor_instance
    
    if processor_instance:
        processor_instance.cancelar()
        return {"status": "cancelled"}
    return {"status": "error", "message": "No hay búsqueda activa"}


@router.get("/status")
async def get_status():
    """Obtiene el estado actual de la búsqueda"""
    global processor_instance
    
    if processor_instance:
        return processor_instance.get_estado()
    return {"estado": "idle", "progreso": 0, "total": 0}


@router.get("/results")
async def get_results():
    """Obtiene los resultados de la búsqueda"""
    global processor_instance
    
    if processor_instance and processor_instance.resultados:
        return {
            "status": "success",
            "count": len(processor_instance.resultados),
            "results": processor_instance.resultados
        }
    return {"status": "empty", "count": 0, "results": []}


@router.get("/export/txt")
async def export_txt(palabra: str = "busqueda"):
    """Exporta resultados a TXT"""
    global processor_instance
    
    if not processor_instance or not processor_instance.resultados:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No hay resultados para exportar"}
        )
    
    contenido = processor_instance.exportar_txt(palabra)
    
    return StreamingResponse(
        iter([contenido.encode('utf-8')]),
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=resultados_{palabra}.txt"
        }
    )


@router.get("/export/excel")
async def export_excel(palabra: str = "busqueda"):
    """Exporta resultados a Excel"""
    global processor_instance
    
    if not processor_instance or not processor_instance.resultados:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No hay resultados para exportar"}
        )
    
    contenido = processor_instance.exportar_excel(palabra)
    
    return StreamingResponse(
        iter([contenido]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=resultados_{palabra}.xlsx"
        }
    )


@router.get("/export/pdf")
async def export_pdf(palabra: str = "busqueda"):
    """Exporta resultados a PDF"""
    global processor_instance
    
    if not processor_instance or not processor_instance.resultados:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "No hay resultados para exportar"}
        )
    
    contenido = processor_instance.exportar_pdf(palabra)
    
    if not contenido:
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": "Error generando PDF (¿fpdf instalado?)"}
        )
    
    return StreamingResponse(
        iter([contenido]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=resultados_{palabra}.pdf"
        }
    )


@router.post("/clear-history")
async def clear_history(data: dict):
    """Borra el historial de una palabra"""
    global processor_instance
    
    if not processor_instance:
        return {"status": "error", "message": "Primero seleccione una carpeta"}
    
    palabra = data.get("palabra", "")
    if processor_instance.borrar_historial(palabra):
        return {"status": "success", "message": f"Historial de '{palabra}' eliminado"}
    return {"status": "info", "message": "No existe historial para esta palabra"}


@router.get("/list-folders")
async def list_folders(path: str = ""):
    """Lista carpetas disponibles (solo para navegación)"""
    try:
        if not path:
            # Listar unidades en Windows o raíz en Linux
            if os.name == 'nt':
                import string
                drives = []
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append({"name": drive, "path": drive})
                return {"folders": drives}
            else:
                path = "/"
        
        if not os.path.isdir(path):
            return {"folders": [], "error": "Ruta no válida"}
        
        folders = []
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    folders.append({
                        "name": item,
                        "path": full_path
                    })
        except PermissionError:
            return {"folders": [], "error": "Sin permisos"}
        
        folders.sort(key=lambda x: x["name"].lower())
        return {"folders": folders, "current": path}
        
    except Exception as e:
        return {"folders": [], "error": str(e)}
