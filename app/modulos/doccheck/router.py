import os
import shutil
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from app.modulos.doccheck.processor import DocProcessor

router = APIRouter(prefix="/doccheck", tags=["doccheck"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/doccheck/templates",
    "app/modulos/inicio/templates" 
])

# Global instance store (Simple in-memory for demo / single user scenario)
# In production with multiple users, this needs session management or temp files key-value store.
processor_instance = None
TEMP_FILE = "temp_doccheck_upload.xlsx"

@router.get("/")
async def doccheck_home(request: Request):
    return templates.TemplateResponse("doccheck/index.html", {"request": request})

@router.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    global processor_instance
    try:
        # Save uploaded file
        with open(TEMP_FILE, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        processor_instance = DocProcessor(TEMP_FILE)
        return {"status": "success", "count": processor_instance.record_count()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@router.get("/record/{idx}")
async def get_record(idx: int):
    global processor_instance
    if not processor_instance:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    rec = processor_instance.get_record(idx)
    if not rec:
        return JSONResponse(status_code=404, content={"status": "error", "error": "Index out of range"})
        
    return {"status": "success", "data": rec}

@router.get("/find/{value}")
async def find_record(value: str):
    """Buscar registro por N° de Registro y devolver su índice"""
    global processor_instance
    if not processor_instance:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    # Buscar en todos los registros
    for idx in range(processor_instance.record_count()):
        rec = processor_instance.get_record(idx)
        if rec and str(rec.get("N° Registro", "")) == str(value):
            return {"status": "success", "index": idx}
    
    return {"status": "error", "error": "Record not found"}

@router.post("/save/{idx}")
async def save_record(idx: int, request: Request):
    global processor_instance
    if not processor_instance:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    try:
        # Parse form data manually because dynamic fields
        form = await request.form()
        data = {k: v for k, v in form.items()}
        
        processor_instance.save_record(idx, data)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@router.get("/export/{format_type}")
async def export_data(format_type: str, caja: str = ""):
    global processor_instance
    if not processor_instance:
        raise HTTPException(status_code=400, detail="No file loaded")
    
    try:
        if format_type == "excel":
            out_name = "Export.xlsx"
            processor_instance.export_excel(out_name, caja if caja else None)
            headers = {'Content-Disposition': 'attachment; filename="Export.xlsx"'}
            return FileResponse(out_name, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif format_type == "txt":
            out_name = "Export.txt"
            processor_instance.export_txt(out_name, caja if caja else None)
            headers = {'Content-Disposition': 'attachment; filename="Export.txt"'}
            return FileResponse(out_name, headers=headers, media_type="text/plain")
        else:
             raise HTTPException(status_code=400, detail="Invalid format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

