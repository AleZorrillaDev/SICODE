from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List

# --- CONFIGURACIÓN DEL ROUTER (Es como el controlador principal del módulo) ---
# Usamos APIRouter para organizar nuestras rutas.
# 'prefix="/autodoc"' significa que todas las URLs de este archivo empezarán con /autodoc
# 'tags' sirve para agrupar endpoints en la documentación automática (Swagger UI)
router = APIRouter(prefix="/autodoc", tags=["AutoDoc"])

# --- CONFIGURACIÓN DE PLANTILLAS (JINJA2) ---
# Aquí le decimos a FastAPI dónde buscar los archivos .html.
# MUY IMPORTANTE: Incluimos carpetas compartidas ('inicio/templates' y 'app/templates')
# porque nuestro index.html usa {% extends "base.html" %}, y ese archivo base vive ahí.
templates = Jinja2Templates(directory=[
    "app/modulos/autodoc/templates",
    "app/modulos/inicio/templates",
    "app/templates"
])

# --- MODELOS DE DATOS (Pydantic) ---
# Definimos la estructura exacta que esperamos recibir del Frontend.
# Esto es una "buena práctica" para validar datos automáticamente.
# Si el JS nos manda algo mal, FastAPI rechazará la petición antes de que rompa nuestro código.
class GenerateRequest(BaseModel):
    filename: str               # Nombre del archivo plantilla (ej: Esquela.docx)
    data: Dict[str, Any]        # Diccionario con los datos del formulario (nombre, fecha, etc.)

# --- RUTAS / ENDPOINTS ---

# 1. RUTA PRINCIPAL (GET /)
# Esta función devuelve la vista HTML (la página web).
# Usamos 'response_class=HTMLResponse' para ser explícitos.
@router.get("/", response_class=HTMLResponse)
async def autodoc_home(request: Request):
    # Renderizamos 'index.html' pasándole el objeto 'request'.
    return templates.TemplateResponse("autodoc/index.html", {"request": request})

# 2. API: OBTENER PLANTILLAS DISPONIBLES
# Devuelve una lista JSON con los documentos que podemos generar.
# En el futuro, esto podría leer archivos reales de una carpeta del servidor.
@router.get("/api/templates")
async def get_templates():
    # Simulamos una base de datos o sistema de archivos
    return [
        {"name": "Esquela_Cobranza_Coactiva.docx", "type": "esquela"},
        {"name": "Carta_Inductiva_Omisos.docx", "type": "carta"},
        {"name": "Resolucion_Multa.docx", "type": "resolucion"},
        {"name": "Solicitud_Devolucion.docx", "type": "solicitud"}
    ]

# 3. API: OBTENER ESQUEMA DE CAMPOS LÓGICOS
# Dependiendo de la plantilla elegida, necesitamos distintos campos en el formulario.
# Aquí definimos qué inputs mostrar al usuario (Text, Date, Select, etc.).
@router.get("/api/templates/{filename}/schema")
async def get_template_schema(filename: str):
    # Campos comunes que van en casi todos los documentos
    common_fields = [
            {"key": "numero_esquela", "label": "Número Documento", "type": "text"},
            {"key": "fecha", "label": "Fecha Emisión", "type": "date"},
            {"key": "ciudad", "label": "Ciudad", "type": "text"},
            {"key": "nombre", "label": "Nombre Contribuyente", "type": "text"}, # Autocompletable con RUC
            {"key": "ruc", "label": "RUC", "type": "text"},
            {"key": "domicilio", "label": "Domicilio Fiscal", "type": "textarea"},
            {"key": "firmante_nombre", "label": "Firmante", "type": "select"}
    ]
    
    # Lógica condicional simple: Si es una Esquela, pedimos monto de deuda.
    # Esto hace que el formulario sea dinámico e inteligente.
    if "Esquela" in filename:
        common_fields.append({"key": "monto_deuda", "label": "Monto Deuda", "type": "text"})
    
    return {"fields": common_fields}

# 4. API: CONSULTA RUC (SIMULADA)
# Recibe un número de RUC y devuelve datos falsos (Mock) para probar.
# En producción, aquí conectaríamos con la API de SUNAT o Padrones.
@router.get("/api/ruc/{ruc}")
async def lookup_ruc(ruc: str):
    # Diccionario 'Fake' para pruebas rápidas
    mock_db = {
        '20600000001': {'nombre': 'MINERA YANACOCHA S.R.L.', 'domicilio': 'AV. VICTOR ANDRES BELAUNDE 147', 'ciudad': 'LIMA'},
        '20100000001': {'nombre': 'ALICORP S.A.A.', 'domicilio': 'AV. ARGENTINA 4793', 'ciudad': 'CALLAO'}
    }
    company = mock_db.get(ruc)
    
    if company:
        return {"success": True, **company} # ** desempaqueta el diccionario
        
    return {"success": False, "message": "RUC no encontrado"}

# 5. API: GENERAR DOCUMENTO (PDF)
# Recibe los datos validados por Pydantic (GenerateRequest)
@router.post("/api/generate")
async def generate_document(req: GenerateRequest):
    # Aquí iría la magia de Python-docx o pdfkit.
    # Por ahora devolvemos un error 501 (Not Implemented) para indicar que falta construirlo.
    # Es buena práctica manejar códigos HTTP correctos.
    return JSONResponse(
        status_code=501, 
        content={"status": "error", "message": "Backend generation not implemented yet (Mock)"}
    )
