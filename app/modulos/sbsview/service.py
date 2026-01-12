
import requests
from bs4 import BeautifulSoup
import re
import logging

# Configuración de Logging
logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}
HOME = "https://www.sbs.gob.pe/"

# URLs fallback (Plan B si el menú del HOME cambia o falla)
URLS_FALLBACK = {
    # ===== SISTEMA FINANCIERO =====
    "Financieras en liquidación": "https://www.sbs.gob.pe/supervisados-y-registros/entidades-en-liquidacion/empresas-en-liquidacion/sistema-financiero/financieras-en-liquidacion",
    "Cajas de Ahorro y Crédito en liquidación": "https://www.sbs.gob.pe/supervisados-y-registros/entidades-en-liquidacion/empresas-en-liquidacion/sistema-financiero/cajas-de-ahorro-y-credito-en-liquidacion",
    "Cajas de Beneficios y Derramas en liquidación": "https://www.sbs.gob.pe/supervisados-y-registros/entidades-en-liquidacion/empresas-en-liquidacion/sistema-financiero/cajas-de-beneficios-y-derramas-en-liquidacion",

    # ===== SISTEMA COOPAC =====
    "Coopac en disolución y liquidación (Resolución SBS 034-2019)": "https://www.sbs.gob.pe/coopac/coopac-en-disolucion-y-liquidacion",
    "Coopac en disolución": "https://www.sbs.gob.pe/coopac/coopac-en-disolucion",
    "Coopac en liquidación": "https://www.sbs.gob.pe/coopac/coopac-en-liquidacion",
}

SECCIONES = list(URLS_FALLBACK.keys())

# expected counts (sirve para validación)
EXPECTED_MIN_MAX = {
    # ===== SISTEMA FINANCIERO =====
    "Financieras en liquidación": (1, 10),
    "Cajas de Ahorro y Crédito en liquidación": (1, 15),
    "Cajas de Beneficios y Derramas en liquidación": (1, 10),

    # ===== SISTEMA COOPAC =====
    "Coopac en disolución y liquidación (Resolución SBS 034-2019)": (1, 30),
    "Coopac en disolución": (1, 30),
    "Coopac en liquidación": (1, 30),
}

def normalizar(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extraer_desde_menu_home():
    try:
        r = requests.get(HOME, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        resultados = {}

        for sec in SECCIONES:
            # búsqueda flexible (por si cambian mayúsculas/acentos)
            a = soup.find("a", string=lambda t: t and sec.lower() in t.strip().lower())
            if not a:
                resultados[sec] = []
                continue

            li = a.find_parent("li")
            if not li:
                resultados[sec] = []
                continue

            ul = li.find("ul")
            if not ul:
                resultados[sec] = []
                continue

            items = []
            for subli in ul.find_all("li", recursive=False):
                a2 = subli.find("a")
                if not a2:
                    continue
                txt = normalizar(a2.get_text(strip=True))
                if txt:
                    items.append(txt)

            resultados[sec] = items

        return resultados
    except Exception as e:
        logger.error(f"Error extrayendo desde menu home: {e}")
        return {}

def extraer_fallback_por_pagina(sec: str, url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        main = soup.find("main") or soup
        items = []

        for a in main.select("a"):
            txt = normalizar(a.get_text(strip=True))
            # href = (a.get("href") or "").lower()

            # Heurística para capturar solo links útiles (entidades/elementos del listado)
            if not txt:
                continue

            # Para sistema financiero normalmente el href tiene "en-liquidacion"
            # Para coopac no siempre, así que permitimos por texto también
            if "liquidación" not in txt.lower() and "liquidacion" not in txt.lower() and "disolución" not in txt.lower() and "disolucion" not in txt.lower():
                continue

            items.append(txt)

        # quitar duplicados preservando orden
        out = []
        seen = set()
        for x in items:
            if x not in seen:
                out.append(x)
                seen.add(x)

        return out
    except Exception as e:
        logger.error(f"Error extrayendo fallback {sec}: {e}")
        return []

def validar(sec: str, items: list[str]) -> bool:
    mn, mx = EXPECTED_MIN_MAX.get(sec, (1, 999))
    return mn <= len(items) <= mx

def obtener_datos_sbs():
    """
    Función principal llamada desde el router/controlador.
    Devuelve un diccionario estructurado para el dashboard.
    """
    # 1) método principal (home menu)
    data = extraer_desde_menu_home()

    # 2) validar y fallback si algo raro
    results = {}
    
    # Inicializar con lo que haya o lista vacia
    for sec in SECCIONES:
        items = data.get(sec, [])
        if not validar(sec, items):
            logger.info(f"Validación falló o vacío para '{sec}', intentando fallback...")
            # fallback
            fallback_items = extraer_fallback_por_pagina(sec, URLS_FALLBACK[sec])
            if fallback_items:
                items = fallback_items
        
        results[sec] = items

    # Estructurar para el Frontend
    # Grupo 1: Sistema Financiero
    sistema_financiero = {
        "Financieras en Liquidación": results.get("Financieras en liquidación", []),
        "Cajas de Ahorro y Crédito": results.get("Cajas de Ahorro y Crédito en liquidación", []),
        "Cajas de Beneficios y Derramas": results.get("Cajas de Beneficios y Derramas en liquidación", [])
    }

    # Grupo 2: Sistema COOPAC
    sistema_coopac = {
        "Coopac en Disolución y Liquidación (Res. 034-2019)": results.get("Coopac en disolución y liquidación (Resolución SBS 034-2019)", []),
        "Coopac en Disolución": results.get("Coopac en disolución", []),
        "Coopac en Liquidación": results.get("Coopac en liquidación", [])
    }
    
    # Grupo 3: Liquidaciones Concluidas (Simulado/Estructura)
    liquidaciones_concluidas = {
        "Bancos Concluidos": ["Banco Republicano", "Banco Nuevo Mundo", "Banco de la Industria de la Construcción"],
        "Financieras Concluidas": ["Financiera DAFI", "Financiera TFC (Proceso Cerrado)"],
        "Cajas Concluidas": ["CRAC Señor de Luren", "CRAC San Martín"],
        "Edpymes Concluidas": ["Edpyme Nueva Visión", "Edpyme Confianza (Antigua)"]
    }
    
    # Calcular Totales para el Dashboard
    total_financiero = sum(len(items) for items in sistema_financiero.values())
    total_coopac = sum(len(items) for items in sistema_coopac.values())
    total_concluidas = sum(len(items) for items in liquidaciones_concluidas.values())

    return {
        "sistema_financiero": sistema_financiero,
        "sistema_coopac": sistema_coopac,
        "liquidaciones_concluidas": liquidaciones_concluidas,
        "total_financiero": total_financiero,
        "total_coopac": total_coopac,
        "total_concluidas": total_concluidas
    }
