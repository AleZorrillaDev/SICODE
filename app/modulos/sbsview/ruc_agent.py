import json
import logging
import os
import re
from typing import Optional



logger = logging.getLogger(__name__)

# Definimos la ruta del archivo de cache en la carpeta del usuario o proyecto
CACHE_FILE = os.path.join(os.path.dirname(__file__), "sbs_rucs_cache.json")

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando cache RUC: {e}")

import requests
from bs4 import BeautifulSoup
import urllib.parse

def buscar_ruc_en_web(nombre_entidad: str) -> Optional[str]:
    # ESTRATEGIA: "Francotirador" a DatosPeru.org
    # Es un directorio ligero que no bloquea requests sencillos.
    
    nombre_clean = nombre_entidad.upper().strip()
    # Codificamos URL (espacios -> %20, etc)
    encoded_name = urllib.parse.quote(nombre_clean)
    
    url = f"https://www.datosperu.org/buscador_empresas.php?buscar={encoded_name}"
    logger.info(f"🔎 Consultando DatosPeru: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        # Fingimos ser Googlebot, suele abrir todas las puertas
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            # DatosPeru devuelve una lista. El RUC suele estar en los titulos de los resultados.
            # Buscamos patron 20xxxxxxxxxxx
            match = re.search(r"(20\d{9})", resp.text)
            if match:
                logger.info(f"✅ RUC Encontrado: {match.group(1)}")
                return match.group(1)
            
            # Si no hay match en el texto crudo, es que no hay resultados.
        else:
            logger.warning(f"DatosPeru status {resp.status_code}")

    except Exception as e:
        logger.error(f"Error DatosPeru: {e}")
        return None

    return None

def obtener_ruc_inteligente(nombre_entidad: str) -> str:
    """
    1. Busca en Cache.
    2. Si no esta, Retorna 'PENDING' para que el frontend sepa que debe buscarlo.
       (No buscamos aqui para no bloquear el renderizado inicial).
    """
    cache = load_cache()
    
    # Normalizamos clave
    key = nombre_entidad.strip().upper()
    
    if key in cache:
        return cache[key]
        
    return "PENDING" # Marcador para el frontend

def buscar_y_guardar_ruc(nombre_entidad: str) -> str:
    """
    Funcion llamada asincronamente (streaming) para buscar y guardar.
    """
    # Recargamos cache por si hubo escrituras concurrentes (simple)
    cache = load_cache()
    key = nombre_entidad.strip().upper()
    
    if key in cache and cache[key] != "PENDING":
        return cache[key]
    
    # Buscamos
    ruc = buscar_ruc_en_web(key)
    
    if ruc:
        cache[key] = ruc
        save_cache(cache)
        return ruc
    else:
        # Guardamos que NO lo encontramos para no re-intentar infinitamente
        # y para que el frontend quite el spinner.
        not_found_val = "NO ENCONTRADO"
        cache[key] = not_found_val
        save_cache(cache)
        return not_found_val
