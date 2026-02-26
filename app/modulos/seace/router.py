from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.modulos.auth.dependencies import login_required
from app.modulos.seace.seace_service import process_rucs, generate_excel_bytes, fetch_contracts_for_ruc
import pandas as pd
import io
import os
import tempfile
from datetime import datetime

router = APIRouter(
    prefix="/seace", 
    tags=["Seace"],
    dependencies=[Depends(login_required)]
)

# Configuración de plantillas
templates_dir = settings.get_template_path("app/modulos/seace/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates_global = settings.get_template_path("app/templates")

templates = Jinja2Templates(directory=[templates_dir, templates_base, templates_global])

@router.get("/", response_class=HTMLResponse)
async def seace_home(request: Request):
    return templates.TemplateResponse("seace/index.html", {"request": request})

@router.post("/process")
async def process_seace_data(
    request: Request,
    rucs: str = Form(None),
    file: UploadFile = File(None),
    start_date: str = Form(None)
):
    rucs_to_process = []
    
    # 1. Obterner RUCs del Textarea
    if rucs:
        rucs_to_process.extend(rucs.replace('\r', '').split('\n'))
        
    # 2. Obtener RUCs del archivo
    if file:
        try:
            content = await file.read()
            if file.filename.endswith('.xlsx') or file.filename.endswith('.xls'):
                df = pd.read_excel(io.BytesIO(content))
                # Asumimos que la columna se llama RUC o es la primera
                possible_cols = [col for col in df.columns if 'RUC' in str(col).upper()]
                if possible_cols:
                    rucs_to_process.extend(df[possible_cols[0]].astype(str).tolist())
                else:
                    rucs_to_process.extend(df.iloc[:, 0].astype(str).tolist())
            else:
                 # Assume TXT
                 text_content = content.decode('utf-8')
                 rucs_to_process.extend(text_content.replace('\r', '').split('\n'))
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Error leyendo archivo: {str(e)}"})

    # Limpiar lista
    rucs_to_process = [r.strip() for r in rucs_to_process if r.strip().isdigit() and len(r.strip()) == 11]
    rucs_to_process = list(set(rucs_to_process)) # Unicos

    if not rucs_to_process:
         return JSONResponse(status_code=400, content={"status": "error", "message": "No se encontraron RUCs válidos."})

    # Procesar
    try:
        processing_result = process_rucs(rucs_to_process, start_date)
        results = processing_result["results"]
        success_rucs = processing_result["success_rucs"]
        failed_rucs = processing_result["failed_rucs"]
        
        # Generar Excel temporal
        df = generate_excel_bytes(results)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"REPORTE_SEACE_{timestamp}.xlsx"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        df.to_excel(filepath, index=False)
        
        return {
            "status": "success",
            "count": len(results),
            "success_count": len(success_rucs),
            "success_rucs": success_rucs,
            "failed_count": len(failed_rucs),
            "failed_rucs": failed_rucs,
            "download_url": f"/seace/download/{filename}"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.get("/download/{filename}")
async def download_report(filename: str):
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, filename=filename, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    return JSONResponse(status_code=404, content={"message": "Archivo no encontrado"})
