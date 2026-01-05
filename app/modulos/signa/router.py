from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import random
import asyncio

router = APIRouter(prefix="/signa", tags=["signa"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/signa/templates",
    "app/modulos/inicio/templates"
])

@router.get("/")
async def signa_home(request: Request):
    return templates.TemplateResponse("signa/index.html", {"request": request})

@router.post("/verify")
async def verify_signature_process(
    folder_path: str = Form(...)
):
    # Mock processing
    # Simulate scanning a directory for PDFs and checking signatures
    
    # Fake delay handled in frontend via UI, here fast response to start stream or just return result
    # We will return a simulated list of files
    
    count = random.randint(5, 15)
    documents = []
    
    estados = ["Firma Válida", "Sin Firma", "Firma Revocada", "Error de Lectura"]
    firmantes = ["JUAN PEREZ", "MARIA GOMEZ", "SYSTEM", "N/A"]
    
    for i in range(count):
        status = random.choice(estados)
        documents.append({
            "id": i + 1,
            "filename": f"RES_COACTIVA_02300500{random.randint(1000,9999)}.pdf",
            "expediente": f"023-005-00{random.randint(100000,999999)}",
            "ruc": f"20{random.randint(100000000,600000000)}",
            "firmante": random.choice(firmantes) if status != "Sin Firma" else "---",
            "status": status,
            "valid": status == "Firma Válida"
        })
        
    return JSONResponse({
        "status": "success",
        "data": documents,
        "summary": {
            "total": count,
            "valid": len([d for d in documents if d['valid']]),
            "error": len([d for d in documents if not d['valid']])
        }
    })
