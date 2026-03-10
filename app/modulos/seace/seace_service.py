import requests
import pandas as pd
from datetime import datetime
import time
import os

# --- Configuración ---
# Nueva API que devuelve más datos (Exportar)
BASE_URL = "https://eap.oece.gob.pe/perfilprov-bus/1.0/ficha/{ruc}/contrataciones/exportar"

def fetch_contracts_for_ruc(ruc):
    """Obtiene todos los contratos de un RUC usando la API de exportación."""
    all_contracts = []
    page_number = 1
    total_pages = 1
    
    print(f"[*] Procesando RUC: {ruc}")
    
    while page_number <= total_pages:
        url = BASE_URL.format(ruc=ruc)
        params = {
            "pageNumber": page_number,
            "pageSize": 500 # El endpoint de exportar suele permitir rangos grandes
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                print(f"[!] Respuesta vacía de SEACE para RUC {ruc}")
                break

            # Extraer info del proveedor (de la primera página o cualquier respuesta válida)
            proveedor_info = data.get("proveedorE02")
            if not proveedor_info:
                proveedor_info = {}
            
            ruc_prov = proveedor_info.get("ruc_proveedor") or ruc
            nom_prov = proveedor_info.get("razon_social_proveedor") or ""

            # Extraer contratos de la data de exportación
            contracts = data.get("contratosE01")
            if contracts is None:
                contracts = []
            
            # Enriquecer contratos con datos del proveedor
            for c in contracts:
                c["_ruc_prov"] = ruc_prov
                c["_nom_prov"] = nom_prov
                
            all_contracts.extend(contracts)
            
            # Verificar si hay más páginas
            search_info = data.get("searchInfo")
            if not search_info:
                break
                
            total_pages = search_info.get("pageTotal", 1)
            
            page_number += 1
            if page_number > total_pages: break
            time.sleep(0.1) # Breve pausa entre páginas
            
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                error_msg = "RUC no encontrado o sin registro en SEACE"
            elif "'NoneType' object has no attribute 'get'" in error_msg:
                error_msg = "Respuesta de SEACE inválida para este RUC"
            elif "timeout" in error_msg.lower():
                error_msg = "Tiempo de espera agotado (SEACE lento)"
            
            print(f"[!] Error procesando RUC {ruc}: {error_msg}")
            raise Exception(error_msg)
            
    return all_contracts

def process_contracts(contracts, start_date=None):
    """Filtra y extrae la información relevante de los contratos según los nuevos campos."""
    processed_data = []
    
    # Rango de fechas: Usar la proporcionada o por defecto 01/12/2025
    if isinstance(start_date, str):
        try:
            START_DATE = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            START_DATE = datetime(2025, 12, 1)
    else:
        START_DATE = start_date or datetime(2025, 12, 1)

    for contract in contracts:
        # Se prioriza la fecha prevista de fin para el filtro de vigencia/reciente
        contract_date_str = contract.get("fecha_prevista_de_fin_de_contrato")
        contract_date = None
        
        if contract_date_str:
            try:
                # Formato en la API de exportación: DD/MM/YYYY
                contract_date = datetime.strptime(contract_date_str, "%d/%m/%Y")
            except Exception:
                try:
                    # Fallback ISO
                    date_part = contract_date_str.split("T")[0]
                    contract_date = datetime.strptime(date_part, "%Y-%m-%d")
                except:
                    pass

        # Aplicar Filtro: Fecha >= 01/12/2025
        if contract_date and contract_date >= START_DATE:
            # Formatear Monto a Moneda (Ej: S/. 1,038,992.03)
            monto_raw = contract.get("monto_del_contrato_original")
            monto_f = ""
            if monto_raw is not None:
                try:
                    monto_f = f"S/. {float(monto_raw):,.2f}"
                except:
                    monto_f = str(monto_raw)

            item = {
                "RUC": contract.get("_ruc_prov", ""),
                "PROVEEDOR": contract.get("_nom_prov", ""),
                "DESCRIPCION": contract.get("descripcion", ""),
                "ENTIDAD": contract.get("entidad", ""),
                "FECHA DE FIRMA DE CONTRATO": contract.get("fecha_de_firma_de_contrato", ""),
                "FECHA PREVISTA DE FIN DE CONTRATO": contract.get("fecha_prevista_de_fin_de_contrato", ""),
                "MONTO": monto_f,
                "OBJETO": contract.get("objeto", ""),
                "ESTADO": contract.get("estado", ""),
                "MIEMBROS CONSORCIO": _limpiar_miembros(contract.get("miembros_consorcio", ""))
            }
            processed_data.append(item)
            
    return processed_data

def _limpiar_miembros(valor: str) -> str:
    """Quita el último campo del valor MIEMBROS CONSORCIO (separado por '|')."""
    if not valor:
        return valor
    partes = [p for p in str(valor).split("|") if p.strip()]
    if len(partes) <= 1:
        return valor
    return "|".join(partes[:-1])


def generate_excel_bytes(data, failed_rucs=None):
    """Genera el DataFrame a partir de los datos con las columnas solicitadas.
    Devuelve el DataFrame principal y el de fallidos.
    """
    # Columnas solicitadas por el usuario para el Reporte Normal Simple
    columns_requested = [
        "RUC", "PROVEEDOR", "DESCRIPCION", "ENTIDAD", 
        "FECHA DE FIRMA DE CONTRATO", "FECHA PREVISTA DE FIN DE CONTRATO", 
        "MONTO", "OBJETO", "ESTADO"
    ]
    
    # Todas las columnas disponibles (incluyendo Miembros por si se usa en Cruce)
    all_columns = columns_requested + ["MIEMBROS CONSORCIO"]
    
    df_datos = pd.DataFrame(data, columns=all_columns) if data else pd.DataFrame(columns=all_columns)
    
    # Para el Reporte Simple, filtramos solo las 9 columnas
    df_simple = df_datos[columns_requested].copy() if not df_datos.empty else pd.DataFrame(columns=columns_requested)

    failed_rucs = failed_rucs or []
    df_fallidos = pd.DataFrame(failed_rucs, columns=["ruc", "reason"]) if failed_rucs else pd.DataFrame(columns=["ruc", "reason"])
    df_fallidos.columns = ["RUC", "Motivo"]

    # Retornamos el completo para el cruce interno y el simple para el archivo
    return df_datos, df_fallidos, df_simple

def process_rucs(ruc_list, start_date=None):
    """Función principal llamada desde el Router. Retorna resultados y estadísticas."""
    all_valid_contracts = []
    success_rucs = []
    failed_rucs = []
    
    for ruc in ruc_list:
        ruc = ruc.strip()
        if not ruc.isdigit() or len(ruc) != 11:
            failed_rucs.append({"ruc": ruc, "reason": "Formato inválido"})
            continue
            
        try:
            raw_contracts = fetch_contracts_for_ruc(ruc)
            if not raw_contracts:
                failed_rucs.append({"ruc": ruc, "reason": "Sin contratos encontrados"})
                continue
                
            valid_contracts = process_contracts(raw_contracts, start_date)
            if not valid_contracts:
                failed_rucs.append({"ruc": ruc, "reason": "Sin contratos en el rango de fecha"})
                continue
                
            all_valid_contracts.extend(valid_contracts)
            success_rucs.append(ruc)
        except Exception as e:
            failed_rucs.append({"ruc": ruc, "reason": str(e)})
        
    return {
        "results": all_valid_contracts,
        "success_rucs": success_rucs,
        "failed_rucs": failed_rucs
    }
