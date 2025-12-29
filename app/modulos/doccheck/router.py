from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/doccheck", tags=["doccheck"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/doccheck/templates",
    "app/modulos/inicio/templates" 
])

@router.get("/")
async def doccheck_home(request: Request):
    return templates.TemplateResponse("doccheck/index.html", {"request": request})
