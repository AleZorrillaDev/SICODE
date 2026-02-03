from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
from PIL import Image
from typing import List
import io
import base64

router = APIRouter(prefix="/datamask", tags=["datamask"])

from app.core.config import settings
templates_dir = settings.get_template_path("app/modulos/datamask/templates")
templates_base = settings.get_template_path("app/modulos/inicio/templates")
templates = Jinja2Templates(directory=[templates_dir, templates_base])

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
        
        # Metadata Update
        metadata = doc.metadata
        metadata["producer"] = "DataMask Pro v1.0"
        metadata["creator"] = "DataMask Pro (SUNAT Edition)"
        metadata["author"] = "Alex Zorrilla"
        metadata["title"] = "Documento Procesado"
        doc.set_metadata(metadata)
        
        # --- PROCESSING LOGIC ---
        for p_idx_str, ann_list in data.items():
            try:
                p_idx = int(p_idx_str)
                if p_idx < 0 or p_idx >= doc.page_count: continue
                page = doc.load_page(p_idx)
                
                # Get page size to denormalize coords
                # Rect is usually [x0, y0, x1, y1]
                w = page.rect.width
                h = page.rect.height
                
                for ann in ann_list:
                    atype = ann.get("type")
                    color_hex = ann.get("color", "#000000")
                    
                    # Convert hex to RGB (0-1 range for PyMuPDF)
                    r = int(color_hex[1:3], 16) / 255.0
                    g = int(color_hex[3:5], 16) / 255.0
                    b = int(color_hex[5:7], 16) / 255.0
                    rgb = (r, g, b)
                    
                    if atype == 'highlight':
                        # rect: [x, y, w, h] normalized
                        nr = ann["rect"]
                        # Convert to fitz Rect [x0, y0, x1, y1]
                        # Input was x,y,w,h. Fitz wants x0,y0,x1,y1
                        qt = fitz.Rect(nr[0]*w, nr[1]*h, (nr[0]+nr[2])*w, (nr[1]+nr[3])*h)
                        
                        a = page.add_highlight_annot(qt)
                        a.set_colors(stroke=rgb)
                        a.update()
                        
                    elif atype == 'strike':
                        # p1, p2 normalized
                        p1 = ann["p1"]
                        p2 = ann["p2"]
                        # Strike needs a Quad or Rect usually, but add_strike_annot uses a Quad or Rect
                        # We simulate by creating a small rect or just a line logic
                        # PyMuPDF strike annot takes a Rect or Quad. 
                        # Ideally we identify the text under it, but we are drawing raw.
                        # We will use add_line_annot for strike visual if text search is hard, 
                        # OR use add_strike_annot if we had text quad. 
                        # Simpler: Use a Line Annotation which looks like a strike manually drawn
                        # BUT the prompt asked for "Strike". Let's try to use Line for visual consistency with the frontend drawing
                        a = page.add_line_annot(
                            fitz.Point(p1['x']*w, p1['y']*h),
                            fitz.Point(p2['x']*w, p2['y']*h)
                        )
                        a.set_colors(stroke=rgb)
                        a.set_border(width=2)
                        a.update()

                    elif atype == 'redact':
                         nr = ann["rect"]
                         qt = fitz.Rect(nr[0]*w, nr[1]*h, (nr[0]+nr[2])*w, (nr[1]+nr[3])*h)
                         page.add_redact_annot(qt, fill=rgb)
                         # We must apply redactions immediately or at end
                         page.apply_redactions()

                    elif atype == 'ink':
                        # Points list of {x,y} normalized
                        pts = ann.get("points", [])
                        if len(pts) > 1:
                             fpts = [fitz.Point(p['x']*w, p['y']*h) for p in pts]
                             a = page.add_ink_annot([fpts])
                             a.set_colors(stroke=rgb)
                             a.set_border(width=3)
                             a.update()

                    elif atype == 'text':
                         x = ann['x'] * w
                         y = ann['y'] * h
                         text = ann['text']
                         # Insert text
                         page.insert_text((x, y), text, color=rgb, fontsize=16) 
                         # Note: insert_text is permanent, not an annotation layer usually, but good for "filling"
                         # If we want annotation: page.add_text_annot(...)
                         
            except Exception as e:
                print(f"Error processing page {p_idx_str}: {e}")
                continue

        # Save to buffer
        out_buffer = io.BytesIO()
        doc.save(out_buffer, garbage=4, deflate=True)
        doc.close()
        out_buffer.seek(0)
        
        # Return as downloadable file
        return JSONResponse(
            content={"status": "success", "file": base64.b64encode(out_buffer.getvalue()).decode('utf-8')},
            media_type="application/json"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    """
    Endpoint (Multi-file upload) to merge PDFs.
    """
    try:
        merged_doc = fitz.open()
        
        for file in files:
            file_bytes = await file.read()
            # Open each file as a doc
            with fitz.open(stream=file_bytes, filetype="pdf") as src_doc:
                merged_doc.insert_pdf(src_doc)
        
        # Metadata
        metadata = {
            "producer": "DataMask Pro v1.0",
            "creator": "DataMask Pro (SUNAT Edition)",
            "title": "Documento Combinado",
            "author": "Alex Zorrilla"
        }
        merged_doc.set_metadata(metadata)

        out_buffer = io.BytesIO()
        # garbage=4 compresses and cleans
        merged_doc.save(out_buffer, garbage=4, deflate=True)
        merged_doc.close()
        out_buffer.seek(0)

        # Return Base64
        return JSONResponse(
            content={
                "status": "success", 
                "file": base64.b64encode(out_buffer.getvalue()).decode('utf-8'),
                "message": f"Se han unido {len(files)} archivos correctamente."
            },
            media_type="application/json"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# Placeholder for logic - we will implement the actual PDF processing in following steps
# once we confirm libraries are available or if we do it client-side.
