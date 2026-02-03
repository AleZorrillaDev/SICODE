
import io
import zipfile
import datetime
import os
from dateutil.parser import parse
from typing import List, Dict, Any

from fastapi import APIRouter, Response, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import pandas as pd
from docxtpl import DocxTemplate

# --- CONFIGURACIÓN ---
try:
    from app.core.config import settings
    TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))
except ImportError:
    TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DEFINICIÓN DE LA APP / ROUTER ---
router = APIRouter(prefix="/autodoc", tags=["AutoDoc"])

# --- HTML FRONTEND CÓDIGO FUENTE (SPA) ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoDoc Masivo | Generador de Documentos</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    
    <style>
        :root {
            /* Palette: Modern Corporate Blue & White */
            --primary: #2563eb;         /* Royal Blue */
            --primary-hover: #1d4ed8;
            --secondary: #64748b;       /* Slate */
            --success: #10b981;         /* Emerald */
            --danger: #ef4444;          /* Red */
            --background: #f8fafc;      /* Very Light Blueish Gray */
            --surface: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;       /* Dark Slate */
            --text-muted: #64748b;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }

        * {
            box-sizing: border-box;
            outline: none;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--background);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* --- Header --- */
        header {
            background-color: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 0 1.5rem;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow-sm);
            z-index: 20;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            background: linear-gradient(135deg, var(--primary), #3b82f6);
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            box-shadow: 0 2px 5px rgba(37, 99, 235, 0.3);
        }

        h1 {
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
            color: var(--text-main);
            letter-spacing: -0.025em;
        }
        
        .header-actions {
            display: flex;
            gap: 12px;
        }

        /* --- Buttons --- */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            font-weight: 500;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }

        .btn-primary {
            background-color: var(--primary);
            color: white;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .btn-primary:hover {
            background-color: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-success {
            background-color: var(--success);
            color: white;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .btn-success:hover {
            background-color: #059669;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background-color: var(--surface);
            color: var(--text-main);
            border-color: var(--border);
        }
        .btn-secondary:hover {
            background-color: #f1f5f9;
            border-color: #cbd5e1;
        }

        .btn-danger-text {
            color: var(--danger);
            background: transparent;
            padding: 4px 8px;
        }
        .btn-danger-text:hover {
            background-color: #fef2f2;
            border-radius: 4px;
        }

        /* --- Toolbar --- */
        .toolbar {
            padding: 1rem 1.5rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
        }

        .stats {
            margin-left: auto;
            font-size: 0.875rem;
            color: var(--text-muted);
            display: flex;
            gap: 1rem;
        }
        .stat-item b {
            color: var(--text-main);
        }

        /* --- Table Area --- */
        .main-content {
            flex: 1;
            overflow: auto;
            position: relative;
            background: #f1f5f9; /* Slightly darker than page bg for contrast with table */
            padding: 1rem;
        }

        .table-wrapper {
            background: var(--surface);
            border-radius: 8px;
            box-shadow: var(--shadow-md);
            border: 1px solid var(--border);
            overflow: auto;
            height: 100%; /* Fill the container */
            position: relative;
        }

        table {
            border-collapse: separate; /* Important for sticky header border */
            border-spacing: 0;
            width: 100%;
            min-width: 2800px; /* Ensure enough scroll space */
        }

        th {
            background-color: #f8fafc;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 12px 10px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
            border-bottom: 1px solid var(--border);
            border-right: 1px solid #f1f5f9;
            white-space: nowrap;
        }

        td {
            padding: 0;
            border-bottom: 1px solid var(--border);
            border-right: 1px solid #f1f5f9;
            background: var(--surface);
            transition: background 0.1s;
        }

        tr:hover td {
            background-color: #f8fafc;
        }

        /* Input styling inside cells to look seamless */
        td input {
            width: 100%;
            height: 100%;
            padding: 10px;
            border: 2px solid transparent;
            font-size: 0.875rem;
            font-family: 'Inter', sans-serif;
            color: var(--text-main);
            background: transparent;
        }
        
        td input:focus {
            background-color: #fff;
            border-color: var(--primary);
            box-shadow: inset 0 0 0 1px var(--primary);
            z-index: 5;
            position: relative;
        }
        
        /* Specific column styles */
        .col-index {
            width: 50px;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.75rem;
            background-color: #f8fafc;
            position: sticky;
            left: 0;
            z-index: 9; /* Lower than header */
            border-right: 2px solid var(--border);
        }
        
        .col-index.header {
            z-index: 11; /* Higher than both */
        }

        .col-vcto input {
            color: var(--text-muted);
            font-style: italic;
            background-color: #f1f5f9;
            pointer-events: none;
        }
        
        .col-action {
            width: 60px;
            text-align: center;
        }

        /* --- Loading Overlay --- */
        .loading-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(4px);
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 100;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #e2e8f0;
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s ease-in-out infinite;
            margin-bottom: 1rem;
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }

        .loading-text {
            font-size: 1.1rem;
            color: var(--text-main);
            font-weight: 500;
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #1e293b;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: var(--shadow-lg);
            display: none;
            animation: slideUp 0.3s ease;
            z-index: 200;
        }
        
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

    </style>
</head>
<body>

    <!-- Loading Screen -->
    <div id="loading" class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">Generando y comprimiendo documentos...</div>
        <div style="color: var(--text-muted); margin-top: 5px;">Esto puede tardar unos segundos</div>
    </div>
    
    <!-- Toast Notification -->
    <div id="toast" class="toast">Notificación</div>

    <header>
        <div class="header-title">
            <div class="logo-icon"><i class="fa-solid fa-file-word"></i></div>
            <div>
                <h1>AutoDoc Masivo</h1>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Sistema de Generación de Documentos sin BD</div>
            </div>
        </div>
        <div class="header-actions">
            <!-- Botón de regreso que lleva al inicio de la app general -->
            <button class="btn btn-secondary" onclick="window.location.href='/'">
                <i class="fa-solid fa-home"></i> Inicio
            </button>
        </div>
    </header>

    <div class="toolbar">
        <button class="btn btn-primary" onclick="addRow()">
            <i class="fa-solid fa-plus"></i> Agregar Fila
        </button>
        <button class="btn btn-secondary" onclick="clearTable()">
            <i class="fa-solid fa-trash"></i> Limpiar Tabla
        </button>
        <button class="btn btn-secondary" onclick="addExampleData()">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Datos de Ejemplo
        </button>
        
        <div style="flex: 1;"></div>
        
        <div class="stats">
            <span class="stat-item">Filas: <b id="rowCount">0</b></span>
        </div>
        
        <button class="btn btn-success" onclick="generarDocumentos()">
            <i class="fa-solid fa-file-zipper"></i> GENERAR DOCUMENTOS
        </button>
    </div>

    <div class="main-content">
        <div class="table-wrapper">
            <table id="dataTable">
                <thead>
                    <tr>
                        <th class="col-index header">#</th>
                        <th style="min-width: 120px;">RUC</th>
                        <th style="min-width: 250px;">RAZON_SOCIAL</th>
                        <th style="min-width: 300px;">DOMICILIO</th>
                        <th>NUM_EXP</th>
                        <th>FECHA_EXP</th>
                        <th style="width: 80px;">DIAS</th>
                        <th title="Calculado Automáticamente">VCTO (Auto)</th>
                        <th>BOLETA</th>
                        <th>NUM_ORDEN</th>
                        <th>FECHA_BOLETA</th>
                        <th>MONTO</th>
                        <th>PERIODO</th>
                        <th>COD_ERR</th>
                        <th>TRIB_ERR</th>
                        <th>COD_COR</th>
                        <th>TRIB_COR</th>
                        <th>REIMPUTACION</th>
                        <th>RI</th>
                        <th>VALOR_VINCULADO</th>
                        <th>EXP_F194</th>
                        <th>ESQUELA</th>
                        <th>OBSV</th>
                        <th style="width: 80px;">CONTEO</th>
                        <th>ESTADO</th>
                        <th class="col-action">Acción</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Rows will be added here -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const COLUMNS = [
            "RUC", "RAZON_SOCIAL", "DOMICILIO", "NUM_EXP", "FECHA_EXP", "DIAS", "VCTO", 
            "BOLETA", "NUM_ORDEN", "FECHA_BOLETA", "MONTO", "PERIODO", "COD_ERR", "TRIB_ERR", 
            "COD_COR", "TRIB_COR", "REIMPUTACION", "RI", "VALOR_VINCULADO", "EXP_F194", 
            "ESQUELA", "OBSV", "CONTEO", "ESTADO"
        ];

        function createInput(key) {
            const input = document.createElement("input");
            input.dataset.key = key;
            input.setAttribute("autocomplete", "off");
            
            // Tipos de input inteligentes
            if (key.includes("FECHA")) input.type = "date";
            else if (["DIAS", "MONTO", "VALOR_VINCULADO", "CONTEO"].includes(key)) input.type = "number";
            else input.type = "text";
            
            if (key === "VCTO") {
                input.placeholder = "Automático";
                input.readOnly = true;
                input.parentElement?.classList.add("col-vcto"); // Esto se aplicará al TD al insertarlo
            }

            // Evento para navegar con flechas (UX improvement)
            input.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    // Lógica para mover foco verticalmente podría ir aquí
                }
            });

            return input;
        }

        function addRow(data = null) {
            const tbody = document.querySelector("#dataTable tbody");
            const tr = document.createElement("tr");
            
            // Index cell
            const tdIndex = document.createElement("td");
            tdIndex.className = "col-index";
            tdIndex.innerText = tbody.children.length + 1;
            tr.appendChild(tdIndex);
            
            COLUMNS.forEach(col => {
                const td = document.createElement("td");
                if (col === "VCTO") td.className = "col-vcto";
                
                const input = createInput(col);
                if (data && data[col]) input.value = data[col];
                
                td.appendChild(input);
                tr.appendChild(td);
            });

            // Action cell
            const tdAction = document.createElement("td");
            tdAction.className = "col-action";
            const btnDel = document.createElement("button");
            btnDel.innerHTML = '<i class="fa-solid fa-times"></i>';
            btnDel.className = "btn-danger-text";
            btnDel.title = "Eliminar fila";
            btnDel.onclick = () => { tr.remove(); updateIndexes(); };
            tdAction.appendChild(btnDel);
            tr.appendChild(tdAction);

            tbody.appendChild(tr);
            updateIndexes();
            
            // Scrool to bottom
            const wrapper = document.querySelector(".table-wrapper");
            wrapper.scrollTop = wrapper.scrollHeight;
        }

        function updateIndexes() {
            const rows = document.querySelectorAll("#dataTable tbody tr");
            rows.forEach((tr, idx) => {
                tr.querySelector(".col-index").innerText = idx + 1;
            });
            document.getElementById("rowCount").innerText = rows.length;
        }

        function clearTable() {
            if(confirm("¿Estás seguro de limpiar toda la tabla?")) {
                document.querySelector("#dataTable tbody").innerHTML = "";
                updateIndexes();
                addRow(); // Add one empty row by default
            }
        }
        
        function addExampleData() {
            const examples = [
                {
                    "RUC": "20600000001", "RAZON_SOCIAL": "EMPRESA EJEMPLO S.A.C.", "DOMICILIO": "AV. SIEMPRE VIVA 123",
                    "FECHA_EXP": "2024-01-15", "DIAS": "10", "ESQUELA": "NO", "REIMPUTACION": "NO"
                },
                {
                    "RUC": "20100000001", "RAZON_SOCIAL": "MINERA YANACOCHA", "DOMICILIO": "CAJAMARCA S/N",
                    "FECHA_EXP": "2024-02-01", "DIAS": "5", "ESQUELA": "SI", "MOTO_DEUDA": "5000"
                }
            ];
            examples.forEach(d => addRow(d));
            showToast("Datos de ejemplo cargados");
        }

        function showToast(msg) {
            const t = document.getElementById("toast");
            t.innerText = msg;
            t.style.display = "block";
            setTimeout(() => t.style.display = "none", 3000);
        }

        async function generarDocumentos() {
            const rows = [];
            const trs = document.querySelectorAll("#dataTable tbody tr");
            
            if (trs.length === 0) {
                alert("Agrega al menos una fila.");
                return;
            }

            trs.forEach(tr => {
                const rowData = {};
                tr.querySelectorAll("input").forEach(input => {
                    const key = input.dataset.key;
                    let val = input.value;
                    rowData[key] = val;
                });
                rows.push(rowData);
            });

            document.getElementById("loading").style.display = "flex";

            try {
                // Endpoint ajustado a la raiz del modulo
                const endpoint = "/autodoc/generar"; 
                
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(rows)
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "Documentos_Masivos_" + new Date().toISOString().slice(0,19).replace(/:/g,"-") + ".zip";
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    showToast("¡Documentos generados correctamente!");
                } else {
                    const err = await response.json();
                    alert("Error servidor: " + (err.detail || "Desconocido"));
                }
            } catch (error) {
                console.error(error);
                alert("Error de conexión o red. Asegúrese que el servidor esté corriendo.");
            } finally {
                document.getElementById("loading").style.display = "none";
            }
        }

        // Inicializar con una fila
        window.onload = () => {
             addRow();
        };
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---

@router.get("/", response_class=HTMLResponse)
async def view_masivo():
    return HTML_PAGE

@router.post("/generar")
async def generar_archivos_masivos(data: List[Dict[str, Any]]):
    if not data:
        return Response(content="No data provided", status_code=400)

    # 1. Convertir a DataFrame
    df = pd.DataFrame(data)

    # 2. Validaciones básicas - Rellenar NaN
    df = df.fillna("")

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        
        # Iterar filas del DataFrame
        for index, row in df.iterrows():
            context = row.to_dict()
            
            # Limpieza de claves vacías para evitar errores en jinja
            # Convertir todo a string excepto lo obvio
            clean_context = {k: str(v) for k, v in context.items()}

            # 3. Lógica de Negocio (Cálculos)
            # VCTO = FECHA_EXP + DIAS
            try:
                if clean_context.get("FECHA_EXP") and clean_context.get("DIAS"):
                    f_exp_str = clean_context["FECHA_EXP"]
                    dias_val = clean_context["DIAS"]
                    
                    if f_exp_str.strip() and dias_val.strip():
                        f_exp = parse(f_exp_str)
                        dias = int(float(dias_val))
                        vcto_date = f_exp + datetime.timedelta(days=dias)
                        clean_context["VCTO"] = vcto_date.strftime("%d/%m/%Y")
                        clean_context["FECHA_EXP"] = f_exp.strftime("%d/%m/%Y")
                    else:
                        clean_context["VCTO"] = ""
                else:
                    clean_context["VCTO"] = ""
            except Exception as e:
                clean_context["VCTO"] = "ERR_CALC"
                print(f"Error cálculo fila {index}: {e}")

            # 4. Selección de Plantilla
            tpl_name = "plantilla_base.docx"
            esquela_val = str(clean_context.get("ESQUELA", "")).upper().strip()
            reimput_val = str(clean_context.get("REIMPUTACION", "")).upper().strip()

            if esquela_val == "SI":
                tpl_name = "plantilla_esquela.docx"
            elif reimput_val == "SI":
                tpl_name = "plantilla_reimputacion.docx"
            
            # Ruta completa plantilla
            tpl_path = os.path.join(TEMPLATES_DIR, tpl_name)
            
            # 5. Renderizar Docx
            if os.path.exists(tpl_path):
                try:
                    doc = DocxTemplate(tpl_path)
                    doc.render(clean_context)
                    
                    file_stream = io.BytesIO()
                    doc.save(file_stream)
                    file_stream.seek(0)
                    
                    ruc = clean_context.get("RUC", "DOC")
                    safe_ruc = "".join([c for c in ruc if c.isalnum()])
                    filename = f"{safe_ruc}_{index+1}.docx"
                    
                    zf.writestr(filename, file_stream.getvalue())
                except Exception as e:
                    zf.writestr(f"ERROR_RENDER_{index+1}.txt", f"Error rendering: {str(e)}")
            else:
                # Si no existe la plantilla, solo loguear el error en el zip
                zf.writestr(f"ERROR_PLANTILLA_{index+1}.txt", f"No se encontró: {tpl_name}")

    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=documentos_masivos.zip"}
    )
