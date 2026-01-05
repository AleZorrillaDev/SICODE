from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import asyncio

router = APIRouter(prefix="/scadbot", tags=["scadbot"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/scadbot/templates",
    "app/modulos/inicio/templates"
])

@router.get("/")
async def scadbot_home(request: Request):
    return templates.TemplateResponse("scadbot/index.html", {"request": request})

@router.post("/verify")
async def verify_folders(
    month: str = Form(...),
    year: str = Form(...)
):
    # Mock simulation of long running process
    # In reality this would check folders
    import random
    
    results = []
    
    # Simulating some checks
    pedidos_mock = range(242448, 242460)
    
    for p in pedidos_mock:
        status = random.choice(["ok", "missing_folder", "missing_txt"])
        results.append({
            "pedido": str(p),
            "status": status,
            "message": f"Pedido {p}: " + ("Carpeta y TXT correctos" if status == "ok" else "Falta carpeta o archivo")
        })
        
    return JSONResponse({
        "status": "success", 
        "data": results,
        "summary": {
            "total": len(pedidos_mock),
            "ok": len([r for r in results if r['status'] == 'ok']),
            "errors": len([r for r in results if r['status'] != 'ok'])
        }
    })
