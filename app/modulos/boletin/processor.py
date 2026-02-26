"""
Boletin Processor - Gestión y descarga de PDFs del Diario El Peruano
"""
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from typing import List, Dict, Optional, Generator
import threading
import fitz  # PyMuPDF

class BoletinProcessor:
    """Procesador para obtener y gestionar PDFs del Boletín Oficial"""
    
    BASE_URL = "https://diariooficial.elperuano.pe"
    SEARCH_URL = f"{BASE_URL}/BoletinOficial/Filtro"
    
    def __init__(self):
        # Carpeta local para caché de PDFs
        self.carpeta_cache = os.path.join(os.getcwd(), "app", "modulos", "boletin", "cache")
        if not os.path.exists(self.carpeta_cache):
            os.makedirs(self.carpeta_cache, exist_ok=True)
        
        self.resultados_mes: Dict[str, List[Dict]] = {} # Cache en memoria por mes/año
        
        # Estado de búsqueda masiva
        self.busqueda_activa = False
        self.busqueda_cancelada = False
        self.progreso_busqueda = {"actual": 0, "total": 0, "porcentaje": 0, "archivo": ""}

    def _normalizar_texto(self, texto: str) -> str:
        """Quita tildes y normaliza texto"""
        reemplazos = {
            'á': 'a', 'Á': 'a',
            'é': 'e', 'É': 'e', 
            'í': 'i', 'Í': 'i',
            'ó': 'o', 'Ó': 'o',
            'ú': 'u', 'Ú': 'u',
            'ñ': 'n', 'Ñ': 'n'
        }
        for orig, reemplazo in reemplazos.items():
            texto = texto.replace(orig, reemplazo)
        return texto.lower()

    def buscar_palabra_en_pdfs(self, pdfs: List[Dict], palabra: str) -> Generator[Dict, None, None]:
        """
        Busca una palabra en una lista de PDFs y reporta coincidencias.
        Utiliza lógica idéntica a BpSearch para robustez.
        """
        self.busqueda_activa = True
        self.busqueda_cancelada = False
        self.progreso_busqueda["total"] = len(pdfs)
        self.progreso_busqueda["actual"] = 0
        
        palabra_norm = self._normalizar_texto(palabra)
        # Patrón idéntico a BpSearch para palabras cortadas por guion
        patron = re.compile(
            rf"(?i)(\b{re.escape(palabra_norm)}\b|"
            rf"{re.escape(palabra_norm[:-1])}-\s*\n\s*{re.escape(palabra_norm[-1])}\b)"
        )
        
        for i, pdf in enumerate(pdfs):
            if self.busqueda_cancelada:
                yield {"type": "cancelled", "message": "Búsqueda cancelada"}
                break
                
            self.progreso_busqueda["actual"] = i + 1
            self.progreso_busqueda["archivo"] = pdf["titulo"]
            self.progreso_busqueda["porcentaje"] = int(((i + 1) / len(pdfs)) * 100)
            
            yield {
                "type": "progress",
                "current": i + 1,
                "total": len(pdfs),
                "percent": self.progreso_busqueda["porcentaje"],
                "archivo": pdf["titulo"]
            }
            
            try:
                # Asegurar que el PDF esté local para procesarlo
                ruta_local = self.obtener_ruta_local(pdf["fecha"], pdf["titulo"])
                if not ruta_local:
                    ruta_local = self.descargar_pdf(pdf["url_online"], pdf["fecha"], pdf["titulo"])
                
                doc = fitz.open(ruta_local)
                apariciones = 0
                paginas_encontradas = []
                
                for num_pagina, pagina in enumerate(doc):
                    texto = pagina.get_text("text") or ""
                    # Unir palabras cortadas por guion (como en BpSearch)
                    texto = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', texto)
                    texto_norm = self._normalizar_texto(texto)
                    coincidencias = re.findall(patron, texto_norm)
                    
                    if coincidencias:
                        apariciones += len(coincidencias)
                        paginas_encontradas.append(num_pagina + 1)
                
                doc.close()
                
                if apariciones > 0:
                    yield {
                        "type": "found",
                        "pdf": pdf,
                        "veces": apariciones,
                        "paginas": paginas_encontradas
                    }
                    
            except Exception as e:
                yield {"type": "error", "archivo": pdf["titulo"], "error": str(e)}
        
        self.busqueda_activa = False
        yield {"type": "complete", "message": "Búsqueda terminada", "total": len(pdfs)}

    def obtener_pdfs_mes(self, anio: str, mes: str) -> List[Dict]:
        """Scrapea la lista de PDFs para un año y mes específicos"""
        data = { "ddwANO": anio, "ddwMES": mes, "btnBuscar": "Buscar" }
        try:
            headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" }
            response = requests.post(self.SEARCH_URL, data=data, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            pdf_list = []
            articulos = soup.select("article.normaslegales_articulos")
            for art in articulos:
                a_tag = art.select_one("a[href]")
                parrafos = [p.get_text(strip=True) for p in art.select("p")]
                fecha_str = ""
                for p_text in parrafos:
                    if "Fecha:" in p_text or "/" in p_text:
                        match = re.search(r'(\d{1,2})[/](\d{1,2})[/](\d{4})', p_text)
                        if match: fecha_str = match.group(0)
                
                if a_tag and fecha_str:
                    match = re.search(r'(\d{1,2})[/](\d{1,2})[/](\d{4})', fecha_str)
                    dia = int(match.group(1))
                    mes_str = match.group(2).zfill(2)
                    dia_str = match.group(1).zfill(2)
                    anio_str = match.group(3)
                    
                    fecha_iso = f"{anio_str}-{mes_str}-{dia_str}"
                    # Titulo estandarizado BOYYYYMMDD - DD/MM/YYYY
                    titulo = f"BO{anio_str}{mes_str}{dia_str} - {fecha_str}"
                    
                    link = a_tag["href"]
                    if not link.startswith("http"): link = f"{self.BASE_URL}{link}"
                    
                    pdf_list.append({
                        "titulo": titulo, "url_online": link, "dia": dia, "fecha": fecha_iso,
                        "local": self.esta_descargado(fecha_iso, titulo)
                    })
            return pdf_list
        except Exception as e:
            print(f"Error scraping El Peruano: {e}")
            return []

    def esta_descargado(self, fecha: str, titulo: str) -> bool:
        nombre_limpio = self._limpiar_nombre(f"{fecha}_{titulo}.pdf")
        ruta = os.path.join(self.carpeta_cache, nombre_limpio)
        return os.path.exists(ruta)

    def obtener_ruta_local(self, fecha: str, titulo: str) -> Optional[str]:
        nombre_limpio = self._limpiar_nombre(f"{fecha}_{titulo}.pdf")
        ruta = os.path.join(self.carpeta_cache, nombre_limpio)
        return ruta if os.path.exists(ruta) else None

    def descargar_pdf(self, url: str, fecha: str, titulo: str) -> str:
        nombre_limpio = self._limpiar_nombre(f"{fecha}_{titulo}.pdf")
        ruta_completa = os.path.join(self.carpeta_cache, nombre_limpio)
        if os.path.exists(ruta_completa): return ruta_completa
        try:
            headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" }
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            with open(ruta_completa, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            return ruta_completa
        except Exception as e: raise e

    def _limpiar_nombre(self, nombre: str) -> str:
        nombre = re.sub(r'[\\/*?:"<>|]', "_", nombre)
        return nombre[:200]

    def get_file_bytes(self, path: str) -> bytes:
        with open(path, 'rb') as f: return f.read()
