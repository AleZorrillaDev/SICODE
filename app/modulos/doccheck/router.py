import os
import shutil
import uuid
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Response, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from app.modulos.doccheck.processor import DocProcessor
from app.modulos.auth.dependencies import login_required

router = APIRouter(
    prefix="/doccheck", 
    tags=["doccheck"],
    dependencies=[Depends(login_required)]
)

from app.core.config import settings
templates_dir = settings.get_template_path("app/modulos/doccheck/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir, templates_base])

# In-memory session store: { "session_id": DocProcessorInstance }
sessions = {}

@router.get("/")
async def doccheck_home(request: Request):
    response = templates.TemplateResponse("doccheck/index.html", {"request": request})
    
    # Check if user already has a session
    items_session = request.cookies.get("doccheck_session_id")
    if not items_session or items_session not in sessions:
        new_id = str(uuid.uuid4())
        response.set_cookie(key="doccheck_session_id", value=new_id)
        # Initialize empty session (or None until upload)
        sessions[new_id] = None 
    
    # Note: Logic to clear session on reload specific request:
    # If we want to force clear on reload, we can reset it here:
    if items_session and items_session in sessions:
         sessions[items_session] = None # Reset state on reload/home access
         
    return response

@router.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    session_id = request.cookies.get("doccheck_session_id")
    if not session_id:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No session ID"})
    
    try:
        # Create unique filename for this session
        filename = f"temp_doccheck_{session_id}.xlsx"
        
        # Save uploaded file
        with open(filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store processor instance in session
        sessions[session_id] = DocProcessor(filename)
        
        return {"status": "success", "count": sessions[session_id].record_count()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@router.get("/record/{idx}")
async def get_record(idx: int, request: Request):
    session_id = request.cookies.get("doccheck_session_id")
    processor = sessions.get(session_id)
    
    if not processor:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    rec = processor.get_record(idx)
    if not rec:
        return JSONResponse(status_code=404, content={"status": "error", "error": "Index out of range"})
        
    return {"status": "success", "data": rec}

@router.get("/find/{value}")
async def find_record(value: str, request: Request):
    """Buscar registro por N° de Registro y devolver su índice"""
    session_id = request.cookies.get("doccheck_session_id")
    processor = sessions.get(session_id)
    
    if not processor:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    # Buscar en todos los registros
    for idx in range(processor.record_count()):
        rec = processor.get_record(idx)
        if rec and str(rec.get("N° Registro", "")) == str(value):
            return {"status": "success", "index": idx}
    
    return {"status": "error", "error": "Record not found"}

@router.post("/save/{idx}")
async def save_record(idx: int, request: Request):
    session_id = request.cookies.get("doccheck_session_id")
    processor = sessions.get(session_id)
    
    if not processor:
        return JSONResponse(status_code=400, content={"status": "error", "error": "No file loaded"})
    
    try:
        # Parse form data manually because dynamic fields
        form = await request.form()
        data = {k: v for k, v in form.items()}
        
        processor.save_record(idx, data)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})

@router.get("/export/{format_type}")
async def export_data(format_type: str, request: Request, caja: str = ""):
    session_id = request.cookies.get("doccheck_session_id")
    processor = sessions.get(session_id)
    
    if not processor:
        raise HTTPException(status_code=400, detail="No file loaded")
    
    try:
        if format_type == "excel":
            out_name = f"Export_{session_id}.xlsx"
            processor.export_excel(out_name, caja if caja else None)
            headers = {'Content-Disposition': 'attachment; filename="Export.xlsx"'}
            return FileResponse(out_name, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif format_type == "txt":
            out_name = f"Export_{session_id}.txt"
            processor.export_txt(out_name, caja if caja else None)
            headers = {'Content-Disposition': 'attachment; filename="Export.txt"'}
            return FileResponse(out_name, headers=headers, media_type="text/plain")
        else:
             raise HTTPException(status_code=400, detail="Invalid format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
