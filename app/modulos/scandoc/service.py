import os
import re
import io
import base64
import logging
from typing import List, Dict, Any, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps
import pytesseract
import qrcode

# --- Configuración de Logs ---
logger = logging.getLogger(__name__)

# --- Configuración Tesseract ---
tesseract_paths = [
    "/usr/bin/tesseract", # Linux / PythonAnywhere
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\alets\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
]

tesseract_cmd = None
for path in tesseract_paths:
    if os.path.exists(path):
        tesseract_cmd = path
        break

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    logger.info(f"Tesseract encontrado en: {tesseract_cmd}")
else:
    logger.warning("Tesseract NO encontrado. El OCR fallará.")

def clean_ocr_number(text: str) -> str:
    replacements = {
        'O': '0', 'o': '0', 'Q': '0', 'D': '0', 'C': '0',
        'I': '1', 'l': '1', '|': '1', '!': '1', 'i': '1', 'L': '1', 'j': '1', 'J': '1', ']': '1', '[': '1',
        'Z': '2', 'E': '3', 'A': '4', 'S': '5', '$': '5',
        'G': '6', 'T': '7', 'B': '8', 'g': '9'
    }
    cleaned = text
    for char, digit in replacements.items(): cleaned = cleaned.replace(char, digit)
    return re.sub(r'\D', '', cleaned)

def validate_ruc(ruc: str) -> bool:
    if len(ruc) != 11 or not ruc.isdigit(): return False
    factors = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(ruc[i]) * factors[i] for i in range(10))
    residuo = suma % 11
    complemento = 11 - residuo
    digito = 0 if complemento == 10 else (1 if complemento == 11 else complemento)
    return digito == int(ruc[10])

def preprocess_image(pil_image):
    open_cv_image = np.array(pil_image) 
    img_gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY) if len(open_cv_image.shape) == 3 else open_cv_image
    
    # Median Blur suave
    img_blur = cv2.medianBlur(img_gray, 3)

    # Adaptive Threshold
    img_thresh = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return Image.fromarray(img_thresh), img_thresh

def extract_data_from_text(text: str) -> Dict[str, str]:
    data = {}
    text_clean = re.sub(r'  +', ' ', text)
    lines = [l.strip() for l in text_clean.split('\n') if l.strip()]

    # 1. EXPEDIENTE SIGAD
    exp_sigad_match = re.search(r'(\d{3}-[\w\d]+-\d{4}-\d+-\d)', text)
    if exp_sigad_match: data["exp_sigad"] = exp_sigad_match.group(1)

    # 2. RESOLUCIÓN COACTIVA
    res_pattern = r'(?i)(?:RESOLUCI[ÓO]N|RES\.?)\s*(?:COACTIVA)?\s*(?:N[º°])?[\s\\|i:\.\'‘’]*([\dOIZSBl|!i]{10,16})'
    res_match = re.search(res_pattern, text)
    if res_match:
        raw = clean_ocr_number(res_match.group(1))
        if len(raw) >= 10: data["res_coactiva"] = raw
    
    if "res_coactiva" not in data:
        possibles = re.findall(r'\b(133\d{10})\b', clean_ocr_number(text))
        if possibles: data["res_coactiva"] = possibles[0]

    # 3. EXPEDIENTE RC
    exp_rc_pattern = r'(?i)EXPEDIENTE\s*(?:NUMERO|N[º°])?[\s\\|i:\.\'‘’]*([\dOIZSBl|!i]{10,16})'
    exp_rc_match = re.search(exp_rc_pattern, text)
    if exp_rc_match:
        data["expediente_rc"] = clean_ocr_number(exp_rc_match.group(1))

    # 4. RUCs
    ruc_pattern = r'\b([\dOIZSBl|!i]{11})\b'
    all_ruc_matches = list(re.finditer(ruc_pattern, text))
    
    for match in all_ruc_matches:
        raw_ruc = match.group(1)
        ruc = clean_ocr_number(raw_ruc)
        if validate_ruc(ruc):
            start_pos = max(0, match.start() - 100)
            context_area = text.upper()[start_pos:match.start()]
            
            if any(w in context_area for w in ["USUARIO", "TERCERO", "EJECUTORA"]):
                data["ruc_tercero"] = ruc
            elif not data.get("ruc_contribuyente"):
                data["ruc_contribuyente"] = ruc
            elif ruc != data.get("ruc_contribuyente") and not data.get("ruc_tercero"):
                data["ruc_tercero"] = ruc

    # 5. NOMBRE CONTRIBUYENTE
    for i, line in enumerate(lines):
        line_up = line.upper()
        if any(w in line_up for w in ["DEUDOR", "CONTRIBUYENTE", "CONTRIB:"]):
             match = re.search(r'[:\.]\s*(.*)', line)
             val = ""
             if match: val = match.group(1).strip()
             elif i + 1 < len(lines): val = lines[i+1].strip()
            
             if val:
                 val_clean = re.sub(r'(?i)^(?:DEUDOR|TRIBUTARIO|CONTRIBUYENTE|CONTRIB)[:\s\\|!\"\'\.\-=]*', '', val).strip()
                 val_clean = re.sub(r'^[^\w\(\)]+', '', val_clean).strip()
                 if len(val_clean) > 4: data["nombre_contribuyente"] = val_clean
             break

    # 6. NOMBRE TERCERO
    usuario_match = re.search(r'(?i)USUARIO:\s*(?:RUC)?\s*(\d{11})?\s*(.*)', text)
    if usuario_match:
        if usuario_match.group(1): data["ruc_tercero"] = usuario_match.group(1)
        name_raw = usuario_match.group(2).strip()
        name_clean = re.split(r'(?i)PROC:|ASUNTO:', name_raw)[0].strip()
        name_clean = re.sub(r'^[^\w]+', '', name_clean).strip()
        if len(name_clean) > 4: data["nombre_tercero"] = name_clean

    # 7. MONTO
    monto_paren = re.search(r'\(\s*([\dOIZSB]{1,10}[.,]\d{2})\s*\)', text)
    if monto_paren: 
        raw = clean_ocr_number(monto_paren.group(1))
        if len(raw) >= 3:
            val = float(int(raw[:-2]) + int(raw[-2:])/100.0)
            data["monto"] = f"S/. {val:,.2f}"
    
    monto_soles = re.search(r'(?:S/|Soles|suma de)\.?\s*.*?([\d\.,]{1,15}[.,]\d{2})', text, re.I)
    if monto_soles and "monto" not in data:
        raw = clean_ocr_number(monto_soles.group(1))
        if len(raw) >= 3:
            val = float(int(raw[:-2]) + int(raw[-2:])/100.0)
            data["monto"] = f"S/. {val:,.2f}"

    # 8. FECHAS
    meses_map = {
        'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04', 'MAY': '05', 'JUN': '06',
        'JUL': '07', 'AGO': '08', 'SET': '09', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12',
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
        'julio': '07', 'agosto': '08', 'septiembre': '09', 'setiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    sello_matches = re.findall(r'([\dOIZSBl|!i\]\[]{1,4})\s+([A-Z]{3,10})[.,\s‘]*\s*(20\d{2})', text.upper())
    if sello_matches:
        for m_day, m_mes, m_anio in sello_matches:
            dia = clean_ocr_number(m_day).zfill(2)
            mes = meses_map.get(m_mes) or meses_map.get(m_mes[:3])
            if mes:
                data["fecha_recepcion"] = f"STAMP:{dia}/{mes}/{m_anio}"
                break

    potential_matches = re.finditer(r'\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b', text)
    for m in potential_matches:
        start = max(0, m.start() - 30)
        pre = text[start:m.start()].upper()
        if any(w in pre for w in ["FECHA", "HORA", "PRINT"]): continue
        
        f_num = f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"
        if "fecha_recepcion" not in data:
            data["fecha_recepcion"] = f"NUMERIC:{f_num}"
        elif "fecha_rc" not in data and f_num not in data["fecha_recepcion"]:
            data["fecha_rc"] = f_num

    meses_pattern = r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)'
    date_text_match = re.search(rf'(?:\w+[,\s]+)?(\d{{1,2}})\s*[‘\w]{{1,3}}\s+{meses_pattern}\s*[‘\w]{{1,4}}\s+(20\d{{2}})', text, re.IGNORECASE)
    if date_text_match:
        d, m_txt, y = date_text_match.groups()
        if m_txt.lower() in meses_map:
            val_text = f"{d.zfill(2)}/{meses_map[m_txt.lower()]}/{y}"
            data["fecha_rc"] = val_text
            if "fecha_recepcion" not in data or "NUMERIC:" in data["fecha_recepcion"]:
                data["fecha_recepcion"] = val_text

    bancos = ["NACION", "CREDITO", "BCP", "INTERBANK", "BBVA", "CONTINENTAL", "SCOTIABANK", "BANBIF"]
    for banco in bancos:
        if banco in text.upper():
            data["banco_cheque"] = banco
            break

    return data

async def process_ocr_batch(images_b64: List[str]) -> Dict[str, Any]:
    merged_fields = {
        "exp_sigad": "", "fecha_recepcion": "", "ruc_contribuyente": "", "nombre_contribuyente": "",
        "res_coactiva": "", "fecha_rc": "", "expediente_rc": "", "monto": "",
        "ruc_tercero": "", "nombre_tercero": "", "cheque_boleta": "", "banco_cheque": "",
        "observaciones": ""
    }
    processed_images = []
    all_raw_text = []
    all_results = []
    
    for idx, img_b64 in enumerate(images_b64):
        try:
            if "," in img_b64:
                header, encoded = img_b64.split(",", 1)
            else:
                encoded = img_b64
            image_bytes = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(image_bytes))
            image = ImageOps.exif_transpose(image)

            processed_pil, processed_cv = preprocess_image(image)
            img_proc_b64 = base64.b64encode(cv2.imencode('.jpg', processed_cv)[1]).decode()
            processed_images.append(img_proc_b64)
            
            # OCR Loop with Rotations
            rotations = [0, 180, 270, 90]
            best_img_data = {}
            max_img_score = -1
            current_raw = f"[Página {idx+1} | No se detectó texto]"

            for angle in rotations:
                img_to_process = processed_pil if angle == 0 else processed_pil.rotate(angle, expand=True)
                text = pytesseract.image_to_string(img_to_process, config='--oem 3 --psm 6')
                data = extract_data_from_text(text)
                
                score = 0
                if "exp_sigad" in data: score += 5
                if "ruc_contribuyente" in data: score += 4
                if "res_coactiva" in data: score += 4
                if "fecha_recepcion" in data: score += 5 
                score += len(data)

                if score > max_img_score:
                    max_img_score = score
                    best_img_data = data
                    current_raw = f"[Página {idx+1} | Rotación {angle}°]\n" + text
                
                if score >= 15: break
            
            all_raw_text.append(current_raw)
            all_results.append(best_img_data)
        except Exception as e:
            logger.error(f"Error procesando imagen {idx}: {e}")
            continue

    # 3. MERGE FINAL
    for res in all_results:
        for k, v in res.items():
            if not v: continue
            
            if k == "fecha_recepcion":
                if not merged_fields[k]:
                    merged_fields[k] = v
                elif "STAMP:" in v and "STAMP:" not in merged_fields[k]:
                    merged_fields[k] = v
                continue

            if not merged_fields[k]:
                merged_fields[k] = v
            elif k in ["monto", "exp_sigad", "res_coactiva"]:
                if len(v) >= len(merged_fields[k]):
                    merged_fields[k] = v
            elif len(v) > len(merged_fields[k]):
                merged_fields[k] = v
    
    # Limpiar prefijos
    for k in ["fecha_recepcion", "fecha_rc"]:
        if merged_fields[k]:
            merged_fields[k] = merged_fields[k].replace("STAMP:", "").replace("NUMERIC:", "")

    return {
        "fields": merged_fields,
        "raw_text": "\n\n".join(all_raw_text),
        "processed_images": processed_images
    }

def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()
