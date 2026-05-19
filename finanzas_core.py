import pandas as pd
import io
import json
from google import genai
from google.genai import types
import finanzas_db as db
import streamlit as st

# ================= CLASIFICADOR IA GEMINI =================

def clasificar_proveedores_batch(proveedores_list, api_key):
    """
    Recibe una lista de tuplas (rut, nombre_proveedor).
    Llama a Gemini 2.5 Flash en lote para clasificarlos en categorías de restaurante.
    Retorna un diccionario {rut: categoria}.
    """
    if not proveedores_list:
        return {}
        
    prompt = """
    Eres un Director Financiero (CFO) experto en cadenas de restaurantes en Chile.
    Analiza la siguiente lista de proveedores (RUT y Razón Social) extraídos del SII de un restaurante (Churrasco Planet / La Terraza).
    Clasifica cada proveedor en EXACTAMENTE UNA de las siguientes categorías estratégicas:
    - Carne y Proteínas
    - Pan y Abarrotes
    - Bebidas y Licores
    - Verduras y Frutas
    - Empaques y Desechables
    - Maquinaria y Mantención
    - Servicios, Arriendos y Otros
    
    Lista de Proveedores:
    """
    for rut, nombre in proveedores_list:
        prompt += f"- RUT: {rut} | Razón Social: {nombre}\n"
        
    prompt += """
    Responde ÚNICAMENTE con un objeto JSON puro donde las claves sean los RUTs y los valores sean la Categoría asignada. Ejemplo:
    {
        "76.123.456-7": "Carne y Proteínas",
        "80.987.654-3": "Bebidas y Licores"
    }
    """
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        mapa_categorias = json.loads(response.text.strip())
        return mapa_categorias
    except Exception as e:
        print("Error en clasificación IA Gemini:", e)
        # Fallback de seguridad
        return {rut: "Servicios, Arriendos y Otros" for rut, _ in proveedores_list}

# ================= PROCESADOR DE ARCHIVOS RCV (SII) =================

def procesar_archivo_sii(file_buffer, filename, sociedad, api_key):
    """
    Procesa un archivo Excel o CSV del RCV del SII.
    Identifica columnas, clasifica proveedores con IA y guarda en base de datos evitando duplicados.
    Retorna (nuevas_cargadas, duplicadas_ignoradas).
    """
    try:
        if filename.endswith('.csv'):
            # El RCV del SII en CSV suele venir separado por punto y coma (;) y con codificación latin1
            df = pd.read_csv(file_buffer, sep=';', encoding='latin1', on_bad_lines='skip')
        else:
            df = pd.read_excel(file_buffer)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo. Asegúrate de que sea un Excel o CSV válido del SII. Detalles: {e}")
        
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.lower()
    
    # Mapeo flexible de columnas SII (Blindado contra colisiones)
    col_folio = next((c for c in df.columns if ('folio' in c or 'docto' in c or 'doc' in c) and 'fecha' not in c and 'tipo' not in c), None)
    col_rut = next((c for c in df.columns if 'rut' in c), None)
    col_razon = next((c for c in df.columns if ('razon' in c or 'razón' in c or 'nombre' in c or 'proveedor' in c) and 'rut' not in c), None)
    col_neto = next((c for c in df.columns if 'neto' in c), None)
    col_iva = next((c for c in df.columns if 'iva' in c), None)
    col_total = next((c for c in df.columns if 'total' in c), None)
    col_fecha = next((c for c in df.columns if 'fecha' in c), None)
    
    if not all([col_folio, col_rut, col_razon, col_neto, col_total]):
        raise ValueError(f"El archivo no tiene las columnas estándar del SII (Folio, RUT, Razón Social, Neto, Total). Columnas encontradas: {list(df.columns)}")
        
    # Extraer lista de proveedores únicos para clasificar en lote con Gemini
    df_proveedores = df[[col_rut, col_razon]].drop_duplicates().dropna()
    proveedores_unicos = list(zip(df_proveedores[col_rut].astype(str), df_proveedores[col_razon].astype(str)))
    
    # Llamar a Gemini para clasificar
    mapa_categorias = clasificar_proveedores_batch(proveedores_unicos, api_key)
    
    # PURGA AUTOMÁTICA DE LA BASE DE DATOS ANTES DE LA INGESTA
    db.eliminar_facturas_sociedad(sociedad)
    
    nuevas_cargadas = 0
    duplicadas_ignoradas = 0
    
    for _, row in df.iterrows():
        try:
            folio_raw = str(row[col_folio]).strip()
            if folio_raw.endswith('.0'): folio_raw = folio_raw[:-2]
            folio = folio_raw
            
            rut = str(row[col_rut]).strip()
            nombre = str(row[col_razon]).strip()
            
            # AUTO-HEALING BLINDADO CONTRA CSV CORRUPTO O COLUMNAS DESPLAZADAS
            if nombre.startswith('_arrow_') or nombre.isdigit() or len(nombre) <= 3:
                # Buscar en toda la fila alguna columna que tenga texto real de proveedor
                for c in df.columns:
                    val = str(row[c]).strip()
                    if val and not val.isdigit() and not val.startswith('_arrow_') and len(val) > 3 and c != col_rut and c != col_folio and c != col_fecha:
                        nombre = val # Encontramos el nombre real del proveedor en otra columna
                        break
                if nombre.startswith('_arrow_') or nombre.isdigit() or len(nombre) <= 3:
                    nombre = f"Proveedor RUT {rut}" # Fallback final absoluto

            neto = float(row[col_neto]) if pd.notna(row[col_neto]) else 0.0
            iva = float(row[col_iva]) if col_iva and pd.notna(row[col_iva]) else 0.0
            total = float(row[col_total]) if pd.notna(row[col_total]) else neto + iva
            
            fecha_raw = str(row[col_fecha]).strip() if col_fecha else ""
            fecha_iso = ""
            if fecha_raw:
                try:
                    dt = pd.to_datetime(fecha_raw, dayfirst=True)
                    fecha_iso = dt.strftime('%Y-%m-%d')
                except Exception:
                    fecha_iso = fecha_raw[:10]
            fecha = fecha_iso
            
            categoria = mapa_categorias.get(rut, "Servicios, Arriendos y Otros")
            
            # Filtro de hierro para Comisiones de Aplicaciones y Tarjetas
            nombre_lower = nombre.lower()
            if any(k in nombre_lower for k in ['uber', 'pedidos ya', 'pedidosya', 'rappi', 'didi', 'transbank', 'mercado pago', 'klap', 'fpay']):
                categoria = "Comisiones de Aplicaciones y Tarjetas"
            
            # Insertar en base de datos (con UNIQUE constraint)
            insertada = db.registrar_factura_sii(
                sociedad=sociedad,
                rut_proveedor=rut,
                nombre_proveedor=nombre,
                folio=folio,
                monto_neto=neto,
                monto_iva=iva,
                monto_total=total,
                fecha_emision=fecha,
                categoria_ia=categoria
            )
            
            if insertada: nuevas_cargadas += 1
            else: duplicadas_ignoradas += 1
            
        except Exception as e:
            print(f"Error al procesar fila SII: {e}")
            continue
            
    return nuevas_cargadas, duplicadas_ignoradas

# ================= MOTOR DE CONSOLIDACIÓN P&L (CASCADA VERTICAL) =================

def calcular_pl_consolidado(sociedad, fecha_inicio=None, fecha_fin=None):
    """
    Calcula el Estado de Resultados consolidado en cascada vertical.
    Separa explícitamente las comisiones de apps de delivery de los proveedores puros.
    """
    ingresos = db.obtener_ingresos(sociedad, fecha_inicio, fecha_fin)
    costos_fijos = db.obtener_costos_fijos(sociedad, fecha_inicio, fecha_fin)
    facturas_sii = db.obtener_facturas_sii(sociedad, fecha_inicio, fecha_fin)
    
    # 1. INGRESOS (Desglose por Local y Canal)
    df_ing = pd.DataFrame(ingresos)
    total_ingresos = df_ing['monto'].sum() if not df_ing.empty else 0.0
    
    ingresos_por_local = df_ing.groupby('local')['monto'].sum().to_dict() if not df_ing.empty else {}
    ingresos_por_canal = df_ing.groupby('canal')['monto'].sum().to_dict() if not df_ing.empty else {}
    
    # 2. COMPRAS / COSTOS FIJOS DIRECTOS
    df_cf = pd.DataFrame(costos_fijos)
    total_costos_fijos = df_cf['monto'].sum() if not df_cf.empty else 0.0
    
    cf_por_local = df_cf.groupby('local')['monto'].sum().to_dict() if not df_cf.empty and 'local' in df_cf.columns else {}
    cf_por_categoria = df_cf.groupby('categoria')['monto'].sum().to_dict() if not df_cf.empty else {}
    
    # 3. PROVEEDORES RCV Y COMISIONES DE APLICACIONES (SEPARACIÓN DE HIERRO)
    df_sii = pd.DataFrame(facturas_sii)
    
    if not df_sii.empty:
        df_comisiones = df_sii[df_sii['categoria_ia'] == 'Comisiones de Aplicaciones y Tarjetas']
        df_proveedores = df_sii[df_sii['categoria_ia'] != 'Comisiones de Aplicaciones y Tarjetas']
    else:
        df_comisiones = pd.DataFrame()
        df_proveedores = pd.DataFrame()
        
    total_comisiones = df_comisiones['monto_neto'].sum() if not df_comisiones.empty else 0.0
    total_proveedores_neto = df_proveedores['monto_neto'].sum() if not df_proveedores.empty else 0.0
    
    proveedores_por_categoria = df_proveedores.groupby('categoria_ia')['monto_neto'].sum().to_dict() if not df_proveedores.empty else {}
    top_proveedores = df_proveedores.groupby('nombre_proveedor')['monto_neto'].sum().sort_values(ascending=False).head(10).to_dict() if not df_proveedores.empty else {}
    top_comisiones = df_comisiones.groupby('nombre_proveedor')['monto_neto'].sum().sort_values(ascending=False).head(5).to_dict() if not df_comisiones.empty else {}
    
    # 4. MARGEN NETO REAL (CASCADA VERTICAL)
    margen_neto = total_ingresos - total_costos_fijos - total_proveedores_neto - total_comisiones
    porcentaje_margen = (margen_neto / total_ingresos * 100) if total_ingresos > 0 else 0.0
    
    return {
        "resumen": {
            "ingresos_totales": total_ingresos,
            "costos_fijos_totales": total_costos_fijos,
            "proveedores_totales_neto": total_proveedores_neto,
            "comisiones_totales": total_comisiones,
            "margen_neto": margen_neto,
            "porcentaje_margen": porcentaje_margen
        },
        "desglose_ingresos": {
            "por_local": ingresos_por_local,
            "por_canal": ingresos_por_canal
        },
        "desglose_costos_fijos": {
            "por_local": cf_por_local,
            "por_categoria": cf_por_categoria
        },
        "desglose_proveedores": {
            "por_categoria": proveedores_por_categoria,
            "top_10": top_proveedores
        },
        "desglose_comisiones": {
            "top_5": top_comisiones
        },
        "raw_data": {
            "ingresos": df_ing,
            "costos_fijos": df_cf,
            "proveedores": df_proveedores,
            "comisiones": df_comisiones
        }
    }
