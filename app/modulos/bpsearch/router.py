from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/bpsearch", tags=["bpsearch"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/bpsearch/templates",
    "app/modulos/inicio/templates"
])

@router.get("/")
async def bpsearch_home(request: Request):
    return templates.TemplateResponse("bpsearch/index.html", {"request": request})
