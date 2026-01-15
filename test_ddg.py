import requests
import urllib.parse
import re
import urllib3

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_duckduckgo_lite(nombre_entidad):
    nombre_clean = nombre_entidad.upper().strip()
    query = f"RUC {nombre_clean} UNIVERSIDAD PERU"
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
    
    print(f"--- SIMULANDO BÚSQUEDA ---")
    print(f"Query: {query}")
    print(f"URL: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://lite.duckduckgo.com/"
    }

    try:
        # verify=False para simular el entorno corporativo
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            print("Contenido descargado exitosamente.")
            
            # Guardar HTML para inspección visual
            with open("ddg_simulation.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print("HTML guardado en 'ddg_simulation.html'")
            
            # Simular la extracción de RUC
            match = re.search(r"(20\d{9})", resp.text)
            if match:
                print(f"✅ RUC DETECTADO: {match.group(1)}")
            else:
                print("⚠️ NO SE DETECTÓ NINGÚN RUC EN EL HTML.")
        else:
            print(f"FALLO: El servidor respondió con error {resp.status_code}")
            
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {e}")

if __name__ == "__main__":
    # Prueba con una entidad real
    test_duckduckgo_lite("FINANCIERA TFC EN LIQUIDACIÓN")
