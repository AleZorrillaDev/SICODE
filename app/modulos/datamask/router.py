from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
from PIL import Image
import io
import base64

router = APIRouter(prefix="/datamask", tags=["datamask"])

templates = Jinja2Templates(directory=[
    "app/templates", 
    "app/modulos/datamask/templates",
    "app/modulos/inicio/templates"

])

@router.get("/")
async def datamask_home(request: Request):
    return templates.TemplateResponse("datamask/index.html", {"request": request})

@router.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    annotations: str = Form(...)  # JSON string of annotations
):
    import json
    try:
        data = json.loads(annotations)
        # data is structure: { "0": [ann1, ann2], "1": ... } where keys are page indices
        
        # Read PDF from upload
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_idx_str, anns in data.items():
            page_idx = int(page_idx_str)
            if page_idx >= len(doc):
                continue
                
            page = doc[page_idx]
            # Get page dimensions to calculate properties if needed
            # We assume coordinates passed are already somewhat compatible or we might need scaling
            # But let's assume JS sends coordinates relative to PDF points 
            # OR JS sends canvas-relative and we need the scale factor.
            # For simplicity, let's assume JS sends normalized 0-1 coordinates or PDF coordinates.
            # *Decided*: JS will send relative coords (0-1) to avoid scale issues.
            
            page_w = page.rect.width
            page_h = page.rect.height
            
            shape = page.new_shape()
            
            for ann in anns:
                kind = ann.get("type")
                color_hex = ann.get("color", "#000000")
                # Convert hex to rgb tuple 0-1
                r = int(color_hex[1:3], 16) / 255.0
                g = int(color_hex[3:5], 16) / 255.0
                b = int(color_hex[5:7], 16) / 255.0
                color = (r, g, b)
                
                if kind in ("highlight", "redact"):
                    # ann["rect"] is [x, y, w, h] normalized (0-1)
                    rx, ry, rw, rh = ann["rect"]
                    rect = fitz.Rect(rx * page_w, ry * page_h, (rx + rw) * page_w, (ry + rh) * page_h)
                    
                    if kind == "highlight":
                        shape.draw_rect(rect)
                        shape.finish(fill=color, fill_opacity=0.3)
                    elif kind == "redact":
                        page.add_redact_annot(rect, fill=color)

                elif kind == "strike":
                    p1 = ann["p1"] # {x, y} normalized
                    p2 = ann["p2"]
                    start = fitz.Point(p1["x"] * page_w, p1["y"] * page_h)
                    stop = fitz.Point(p2["x"] * page_w, p2["y"] * page_h)
                    shape.draw_line(start, stop)
                    shape.finish(color=color, width=2)
                    
                elif kind == "ink":
                    points = ann.get("points", [])
                    if len(points) > 1:
                        # Normalize points
                        fitz_points = [fitz.Point(p["x"] * page_w, p["y"] * page_h) for p in points]
                        shape.draw_polyline(fitz_points)
                        shape.finish(color=color, width=3)
                        
                elif kind == "text":
                    tx = ann["x"] * page_w
                    ty = ann["y"] * page_h
                    text = ann.get("text", "")
                    
                    # Insert simple text
                    rect = fitz.Rect(tx, ty, tx + 300, ty + 50)
                    page.insert_textbox(rect, text, fontsize=16, color=color)

            shape.commit()
            try:
                page.apply_redactions()
            except:
                pass

        # Save to buffer
        out_buffer = io.BytesIO()
        doc.save(out_buffer)
        doc.close()
        out_buffer.seek(0)
        
        # Return as downloadable file
        headers = {'Content-Disposition': 'attachment; filename="modified.pdf"'}
        return JSONResponse(
            content={"status": "success", "file": base64.b64encode(out_buffer.getvalue()).decode('utf-8')},
            media_type="application/json"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# Placeholder for logic - we will implement the actual PDF processing in following steps
# once we confirm libraries are available or if we do it client-side.
