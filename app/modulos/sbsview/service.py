import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin
import urllib3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
HOME = "https://www.sbs.gob.pe/"



# ------------------------------------------------------------
# 🧠 LOGICA DE AGENTE RUC (Deep Scraping)
# ------------------------------------------------------------
MEMORY_CACHE = {}

from .ruc_agent import obtener_ruc_inteligente

def enriquecer_entidad(nombre: str, url_rel: str) -> dict:
    """
    Convierte un nombre y link en un objeto.
    El RUC se obtiene de la Cache local (instantaneo) o se marca PENDING.
    """
    ruc = obtener_ruc_inteligente(nombre)
    
    return {
        "nombre": nombre,
        "ruc": ruc,  # Puede ser "20xxxx" o "PENDING"
        "razon_social": nombre, # Simplificamos, usamos el nombre como razón por defecto
        "link_sbs": urljoin(HOME, url_rel) if url_rel else "#"
    }


def normalizar(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def imprimir_listado(nombre: str, items: list):
    """
    Imprime listado en consola. Soporta tanto lista de strings como de objetos (dicts).
    """
    print(f"\n--- {nombre} ({len(items)}) ---")
    if not items:
        print("  (Sin resultados)")
        return
    for i, it in enumerate(items, start=1):
        if isinstance(it, dict):
            # Si es objeto enriquecido, mostramos info extra
            txt = f"{it['nombre']} [RUC: {it['ruc']}]"
        else:
            txt = str(it)
        print(f"  {i}. {txt}")



def extraer_menu_entidades_disolucion_liquidacion():
    """
    Imprime lo que sale en el menú y retorna la estructura para la Web App.
    """
    resultados = {"Sistema Financiero": {}, "Sistema COOPAC": {}}

    try:
        # Usamos requests simple con verify=False para evitar problemas de certificados corporativos
        r = requests.get(HOME, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # 1) Buscar el link "Entidades en Disolución y/o Liquidación"
        a_root = soup.find("a", string=lambda t: t and "entidades en disolución" in t.lower())
        if not a_root:
            print("[WARN] No encontré 'Entidades en Disolución y/o Liquidación' en el HOME.")
            return resultados

        li_root = a_root.find_parent("li")
        if not li_root:
            print("[WARN] No encontré contenedor <li> de 'Entidades en Disolución y/o Liquidación'.")
            return resultados

        ul_sistemas = li_root.find("ul")
        if not ul_sistemas:
            print("[WARN] No encontré el <ul> con sistemas dentro de 'Entidades en Disolución y/o Liquidación'.")
            return resultados

        # objetivos de 2do nivel
        objetivos_lvl2 = {"sistema financiero", "sistema coopac", "coopac"}

        # 2) Recorrer sistemas (nivel 2)
        for li_lvl2 in ul_sistemas.find_all("li", recursive=False):
            a_lvl2 = li_lvl2.find("a")
            if not a_lvl2:
                continue

            sistema_raw = normalizar(a_lvl2.get_text(strip=True))
            if sistema_raw.lower() not in objetivos_lvl2:
                continue

            # normalizar etiqueta para el diccionario de retorno
            if "financiero" in sistema_raw.lower():
                key_sistema = "Sistema Financiero"
            else:
                key_sistema = "Sistema COOPAC"

            ul_subcats = li_lvl2.find("ul")
            if not ul_subcats:
                continue

            # 3) Recorrer subcategorías (nivel 3)
            for li_lvl3 in ul_subcats.find_all("li", recursive=False):
                a_lvl3 = li_lvl3.find("a")
                if not a_lvl3:
                    continue

                subcat = normalizar(a_lvl3.get_text(strip=True))

                # buscar menú final (nivel 4)
                ul_final = li_lvl3.find("ul")
                items_finales = []

                if ul_final:
                    for li_final in ul_final.find_all("li", recursive=False):
                        a_final = li_final.find("a")
                        if not a_final:
                            continue
                        txt_final = normalizar(a_final.get_text(strip=True))
                        if txt_final:
                            # AQUI LA FUSIÓN: Enriquecemos el objeto
                            obj = enriquecer_entidad(txt_final, a_final.get('href'))
                            items_finales.append(obj)

                if key_sistema in resultados:
                    resultados[key_sistema][subcat] = items_finales

        # PRINTS PARA DEPURACION (Tal cual solicitado)
        print("\n=======================================================================")
        print(" ENTIDADES EN DISOLUCIÓN Y/O LIQUIDACIÓN (MENÚ FINAL + RUC)")
        print("=======================================================================")

        for sistema, subcats in resultados.items():
            if not subcats: continue
            print(f"\n### {sistema.upper()} ###")
            for subcat, items in subcats.items():
                imprimir_listado(subcat, items)

        print("\n=======================================================================")
        print("                                FIN")
        print("=======================================================================\n")

    except Exception as e:
        logger.error(f"Error CONEXION SBS: {e}")
        # RETORNAR ERROR VISIBLE AL USUARIO
        error_item = {
            "nombre": "⚠️ ERROR DE CONEXIÓN A SBS",
            "ruc": "OFFLINE",
            "razon_social": str(e),
            "link_sbs": "#"
        }
        resultados["Sistema Financiero"]["ERROR DE RED"] = [error_item]

    return resultados


# ============================================================
# ✅ 2) LIQUIDACIONES CONCLUIDAS -> SISTEMA FINANCIERO (MENÚ FINAL)
# ============================================================

def extraer_menu_liquidaciones_concluidas_sistema_financiero():
    """
    Imprime y retorna estructura de liquidaciones concluidas.
    """
    resultados = {}

    try:
        # Usamos requests simple con verify=False para evitar problemas de certificados corporativos
        r = requests.get(HOME, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        # 1) Buscar el link "Liquidaciones concluidas"
        a_liq = soup.find("a", string=lambda t: t and "liquidaciones concluidas" in t.lower())
        if not a_liq:
            print("[WARN] No encontré 'Liquidaciones concluidas' en el HOME.")
            return resultados

        # subir al <li> contenedor
        li_liq = a_liq.find_parent("li")
        if not li_liq:
            print("[WARN] No encontré contenedor <li> de 'Liquidaciones concluidas'.")
            return resultados

        # 2) Dentro debe estar el submenu, buscamos "Sistema financiero"
        a_sis_fin = li_liq.find("a", string=lambda t: t and "sistema financiero" in t.lower())
        if not a_sis_fin:
            print("[WARN] No encontré 'Sistema financiero' dentro del menú de Liquidaciones concluidas.")
            return resultados

        li_sis_fin = a_sis_fin.find_parent("li")
        if not li_sis_fin:
            print("[WARN] No encontré contenedor <li> para 'Sistema financiero'.")
            return resultados

        ul_subcats = li_sis_fin.find("ul")
        if not ul_subcats:
            print("[WARN] No encontré el <ul> con subcategorías (Bancos/Financieras/Cajas/Edpymes).")
            return resultados

        # subcategorías objetivo
        objetivos = {"bancos", "financieras", "cajas", "edpymes"}

        # 3) Para cada subcat, sacar el último nivel
        for subli in ul_subcats.find_all("li", recursive=False):
            a_sub = subli.find("a")
            if not a_sub:
                continue

            subcat = normalizar(a_sub.get_text(strip=True))
            # filtro flexible
            is_valid = False
            for o in objetivos:
                if o in subcat.lower():
                    is_valid = True
                    break
            if not is_valid: continue

            # buscar ultimo ul interno
            ul_final = subli.find("ul")
            entidades = []

            if ul_final:
                for li_ent in ul_final.find_all("li", recursive=False):
                    a_ent = li_ent.find("a")
                    if not a_ent:
                        continue
                    txt_ent = normalizar(a_ent.get_text(strip=True))
                    if txt_ent:
                        # FUSIÓN: Enriquecer
                        obj = enriquecer_entidad(txt_ent, a_ent.get('href'))
                        entidades.append(obj)

            resultados[subcat] = entidades

        # PRINTS
        print("\n=============================================================")
        print(" LIQUIDACIONES CONCLUIDAS -> SISTEMA FINANCIERO (MENÚ FINAL + RUC)")
        print("=============================================================")

        for k in resultados.keys():
            imprimir_listado(k, resultados.get(k, []))

        print("\n=============================================================")
        print("                         FIN")
        print("=============================================================\n")

    except Exception as e:
        logger.error(f"Error CONEXION SBS (Concluidas): {e}")
        # RETORNAR ERROR VISIBLE (Simulamos una categoría de error)
        error_item = {
            "nombre": "⚠️ REVISE SU CONEXIÓN DE INTERNET/PROXY",
            "ruc": "ERROR",
            "razon_social": str(e),
            "link_sbs": "#"
        }
        resultados["ERROR DE RED"] = [error_item]
        
    return resultados


# ============================================================
# ✅ PUENTE PARA LA WEB APP (Router)
# ============================================================
def obtener_datos_sbs():
    """
    Función orquestadora que llama a las funciones de abajo y
    devuelve el diccionario que espera el HTML.
    """
    activas = extraer_menu_entidades_disolucion_liquidacion()
    concluidas = extraer_menu_liquidaciones_concluidas_sistema_financiero()
    
    sf = activas.get("Sistema Financiero", {})
    sc = activas.get("Sistema COOPAC", {})
    
    # Calculo de totales para el dashboard
    total_sf = sum(len(v) for v in sf.values())
    total_sc = sum(len(v) for v in sc.values())
    total_conc = sum(len(v) for v in concluidas.values())
    
    return {
        "sistema_financiero": sf,
        "sistema_coopac": sc,
        "liquidaciones_concluidas": concluidas,
        "total_financiero": total_sf,
        "total_coopac": total_sc,
        "total_concluidas": total_conc
    }


# ============================================================
# ✅ MAIN (Para ejecutar manual)
# ============================================================

if __name__ == "__main__":
    extraer_menu_entidades_disolucion_liquidacion()
    extraer_menu_liquidaciones_concluidas_sistema_financiero()
