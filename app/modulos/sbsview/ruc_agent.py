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
    # ESTRATEGIA: Google Search (Directo)
    # Preferencia del Usuario. Volumen bajo de datos.
    
    nombre_clean = nombre_entidad.upper().strip()
    query = f"RUC {nombre_clean}"
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://www.google.com/search?q={encoded_query}"
    
    logger.info(f"🔎 Consultando Google: {query}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        # verify=False indispensable
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if resp.status_code == 200:
            # Buscamos patrones de RUC en todo el HTML devuelto
            match = re.search(r"(20\d{9})", resp.text)
            if match:
                logger.info(f"✅ RUC Encontrado: {match.group(1)}")
                return match.group(1)
        else:
            logger.warning(f"Google status {resp.status_code}")

    except Exception as e:
        logger.error(f"Error Google: {e}")
        return None

    return None

def obtener_ruc_inteligente(nombre_entidad: str) -> str:
    """
    1. Busca en Cache.
    2. Si no esta, Retorna 'PENDING' para que el frontend sepa que debe buscarlo.
       (No buscamos aqui para no bloquear el renderizado inicial).
    """
    return "PENDING" # Marcador para el frontend

def obtener_ruc_inteligente(nombre_entidad: str) -> str:
    """
    1. Busca en Cache.
    2. Si no esta, Retorna 'PENDING' para que el frontend sepa que debe buscarlo.
       (No buscamos aqui para no bloquear el renderizado inicial).
    """
    # Normalizamos clave
    key = nombre_entidad.strip().upper()

    # 1. Cache
    cache = load_cache()
    if key in cache:
        return cache[key]
        
    return "PENDING"

def buscar_y_guardar_ruc(nombre_entidad: str) -> str:
    """
    Funcion llamada asincronamente (streaming) para buscar y guardar.
    """
    # Recargamos cache por si hubo escrituras concurrentes (simple)
    cache = load_cache()
    key = nombre_entidad.strip().upper()
    
    # Si esta en cache, verificamos si es un valor valido o un error previo
    if key in cache:
        val = cache[key]
        # Si el valor es un RUC valido (numerico), lo devolvemos
        if val.isdigit() and len(val) == 11:
            return val
        # Si es PENDING, NO HALLADO o ERROR, dejamos pasar para RE-INTENTAR
        # (Esto arregla que se quede pegado en errores pasados)
    
    # Validar si es un mensaje de error del sistema
    if key.startswith("⚠️") or "ERROR" in key:
        return "ERROR"
    
    # Buscamos en web (ultima ratio)
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
