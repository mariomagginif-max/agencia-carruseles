import streamlit as st
from google import genai
import os
import time
import json
from PIL import Image
import io
import base64
import socket
import zipfile
from html2image import Html2Image
import finanzas_db as db
import finanzas_core as core
import pandas as pd
from datetime import datetime

# ================= CONFIGURACIÓN DE PÁGINA =================
st.set_page_config(page_title="Churrasco & Terraza PWA - Executive Management", page_icon="🏢", layout="wide")

# Inicialización de Estado de Sesión para Navegación Lateral por Botones
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "🏢 P&L: Sociedad Principal (3 Locales)"

# ================= CSS PREMIUM (SAAS / POWERBI BLOOMBERG COMPACT STYLE) =================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    /* Dark Executive Core */
    * { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .stApp { background-color: #0b0f19; color: #c9d1d9; }
    
    /* Premium Corporate Header */
    .premium-header { 
        text-align: center; 
        padding: 24px 20px; 
        background: linear-gradient(135deg, #161f33 0%, #0b0f19 100%); 
        border-radius: 14px; 
        margin-bottom: 25px; 
        box-shadow: 0 6px 24px rgba(0,0,0,0.6); 
        border: 1px solid #253352;
    }
    .premium-header h1 { color: #ffffff; margin-bottom: 6px; font-weight: 800; font-size: 2.1rem; letter-spacing: -0.5px; text-shadow: 0 0 20px rgba(0, 242, 254, 0.2); }
    .premium-header p { color: #00f2fe; font-size: 1.05rem; font-weight: 600; margin: 0; }
    
    /* Main Call to Action Button */
    .stButton>button { 
        font-size: 0.95rem;
        font-weight: 700; 
        border-radius: 8px; 
        border: none; 
        padding: 10px 20px; 
        transition: all 0.2s ease; 
    }
    [data-testid="stSidebar"] .stButton>button {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        border: 1px solid #253352 !important;
    }
    [data-testid="stSidebar"] .stButton>button[data-baseweb="button"] {
        background-color: #161f33 !important;
        color: #c9d1d9 !important;
    }
    [data-testid="stSidebar"] .stButton>button[data-baseweb="button"]:hover {
        border-color: #00f2fe !important;
        color: #ffffff !important;
        background-color: #1c2742 !important;
    }
    /* Estilo para botón activo en el sidebar (primario) */
    [data-testid="stSidebar"] button[kind="primary"] { 
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%) !important; 
        color: #ffffff !important; 
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3) !important;
    }
    
    /* File Uploader Container */
    [data-testid="stFileUploadDropzone"] {
        background-color: #161f33;
        border: 2px dashed #253352;
        border-radius: 10px;
        padding: 30px 15px;
        transition: all 0.2s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #00f2fe;
        background-color: #1c2742;
    }
    
    /* Sidebar Navigation Styling */
    [data-testid="stSidebar"] {
        background-color: #0e1424;
        border-right: 1px solid #253352;
    }
    
    /* Inputs & Textareas */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>select {
        background-color: #161f33;
        color: white;
        border: 1px solid #253352;
        border-radius: 6px;
        padding: 10px;
        font-size: 0.9rem;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00f2fe;
        box-shadow: 0 0 0 1px #00f2fe;
    }
    
    /* Info Boxes & Alerts - Ultra Compact */
    .stAlert {
        background-color: #161f33;
        color: #c9d1d9;
        border: 1px solid #253352;
        border-left: 4px solid #00f2fe;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 0.85rem;
    }
    
    /* KPI Metric Cards Customization - Compact & Bold */
    [data-testid="stMetricValue"] {
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        line-height: 1.2 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #00f2fe !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Glassmorphism Section Containers - Ultra Compact */
    .glass-container {
        background: rgba(22, 31, 51, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid #253352;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 20px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    
    /* Section Headers Compact */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 0;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #253352;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-title span { color: #00f2fe; }
    </style>
""", unsafe_allow_html=True)

# ================= FUNCIONES CORE DE MARKETING =================
def generar_imagen_copy(texto, output_path, marca="Churrasco Planet"):
    html_paragraphs = ""
    for line in texto.split('\n'):
        if line.strip(): html_paragraphs += f"<p>{line.strip()}</p>"
        else: html_paragraphs += "<br/>"
            
    if marca == "Churrasco Planet":
        bg_css = "background: linear-gradient(135deg, #1f0c05 0%, #4a1505 100%);"
        border_color = "#ff4400"
    else:
        bg_css = "background: linear-gradient(135deg, #05121f 0%, #082240 100%);"
        border_color = "#0088ff"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700&display=swap" rel="stylesheet">
    <style>
        body {{ width: 1080px; height: 1080px; margin: 0; padding: 0; {bg_css} display: flex; justify-content: center; align-items: center; box-sizing: border-box; font-family: 'Montserrat', sans-serif; color: white; }}
        .container {{ width: 880px; max-height: 940px; background: rgba(0, 0, 0, 0.4); border-top: 8px solid {border_color}; border-radius: 24px; padding: 50px; box-shadow: 0 20px 50px rgba(0,0,0,0.6); overflow: hidden; display: flex; flex-direction: column; justify-content: flex-start; }}
        p {{ font-size: 26px; line-height: 1.5; margin: 0 0 12px 0; text-shadow: 1px 1px 4px rgba(0,0,0,0.9); font-weight: 500; }}
        strong {{ font-weight: 700; color: {border_color}; }}
        br {{ content: ""; display: block; margin-bottom: 8px; }}
    </style>
    </head>
    <body>
        <div class="container">{html_paragraphs}</div>
    </body>
    </html>
    """
    try:
        hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu'])
        hti.output_path = os.path.dirname(output_path)
        hti.screenshot(html_str=html_content, save_as=os.path.basename(output_path), size=(1080, 1080))
    except Exception as e:
        print("Error HTML2Image:", e)
        img = Image.new('RGB', (1080, 1080), color=(15, 10, 10))
        img.save(output_path)

# ================= INICIALIZACIÓN =================
DIR_PLANTILLAS = "plantillas_fijas"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(DIR_PLANTILLAS, exist_ok=True)

# ================= SIDEBAR DE NAVEGACIÓN CORPORATIVA (BOTONES PUROS) =================
with st.sidebar:
    st.markdown("<div style='padding: 15px 10px; text-align: center;'><h2 style='color: white; font-weight: 800; font-size: 1.4rem; margin:0;'>🏢 Menú Corporativo</h2></div>", unsafe_allow_html=True)
    
    col_l1, col_l2 = st.columns(2)
    if os.path.exists("logos/churrasco_planet.png"):
        col_l1.image("logos/churrasco_planet.png", use_container_width=True)
    if os.path.exists("logos/la_terraza.png"):
        col_l2.image("logos/la_terraza.png", use_container_width=True)
        
    st.markdown("---")
    st.markdown("<p style='color: #8b949e; font-size: 0.75rem; font-weight: 700; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;'>📌 Módulos de Gestión</p>", unsafe_allow_html=True)
    
    opciones = [
        "🚀 Ensamblador IA (Marketing)", 
        "🏢 P&L: Sociedad Principal (3 Locales)", 
        "🏪 P&L: Local Maipú (Independiente)", 
        "📥 Carga RCV SII & Registro Móvil", 
        "⚙️ Plantillas de Marca (Config)"
    ]
    
    for op in opciones:
        if st.button(op, use_container_width=True, type="primary" if st.session_state.modulo_activo == op else "secondary"):
            st.session_state.modulo_activo = op
            st.rerun()
            
    st.markdown("---")
    
    with st.expander("🔑 Configuración Avanzada (API Key)"):
        api_key = st.text_input("Gemini API Key", value="", type="password")
        st.markdown("[👉 Obtener API Key Gratis aquí](https://aistudio.google.com/app/apikey)")
        
    st.markdown("---")
    st.info("💡 **Navegación SaaS:** Selecciona cualquier módulo en este menú para ver la información a pantalla completa.")

# ================= HEADER PRINCIPAL =================
st.markdown("<div class='premium-header'><h1>🏢 Churrasco & Terraza PWA</h1><p>Sistema Integral de Gestión Ejecutiva y P&L en Cascada</p></div>", unsafe_allow_html=True)

# ================= EJECUCIÓN MODULAR A PANTALLA COMPLETA =================
modulo_activo = st.session_state.modulo_activo

# ----------------- VISTA 1: ENSAMBLADOR IA DE MARKETING -----------------
if modulo_activo == "🚀 Ensamblador IA (Marketing)":
    st.markdown("<div class='section-title'><span>🎨</span> Motor de Ensamblado de Marketing IA</div>", unsafe_allow_html=True)
    
    c1_up, c2_up = st.columns([2, 1])
    with c1_up:
        st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
        st.subheader("Paso 1: Sube tu Diseño Principal")
        imagen_portada = st.file_uploader("🖼️ Selecciona tu Slide 1 (Soporta .jpg, .png, .mp4, .mov)", type=["png", "jpg", "jpeg", "mp4", "mov"])
        st.markdown("</div>", unsafe_allow_html=True)
    with c2_up:
        st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
        st.subheader("Paso 2: Detalles")
        marca_forzada = st.radio("🏢 Marca:", ["Churrasco Planet", "La Terraza Familiar"])
        instruccion_agente = st.text_area("💬 Contexto (Opcional):", placeholder="Ej: 'Oferta exclusiva por el día del niño, válido hasta el domingo.'")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    if st.button("🚀 INICIAR ENSAMBLADO MÁGICO", type="primary", use_container_width=True):
        if not imagen_portada:
            st.warning("⚠️ Sube un diseño primero para continuar.")
        else:
            try:
                temp_dir = "temp_promo"
                os.makedirs(temp_dir, exist_ok=True)
                
                portada_bytes = imagen_portada.getvalue()
                is_video = imagen_portada.name.lower().endswith(('.mp4', '.mov'))
                
                img_promo_s1 = os.path.join(temp_dir, "promo_agente_s1.mp4" if is_video else "promo_agente_s1.png")
                with open(img_promo_s1, "wb") as f:
                    f.write(portada_bytes)
                
                with st.spinner("🧠 IA Analizando tu diseño para extraer estrategia y redactar copys..."):
                    client = genai.Client(api_key=api_key)
                    
                    try:
                        prompt_agente = f"""
                        Eres un Director de Marketing experto en redes sociales.
                        Analiza detalladamente este material (Slide 1) que el cliente ya diseñó.
                        Identifica exactamente qué producto se está promocionando, el precio si aparece, y la intención de venta.
                        Contexto adicional del cliente (opcional): "{instruccion_agente}".
                        
                        Devuelve un JSON estricto con esta estructura:
                        {{
                        "marca": "{marca_forzada}",
                        "copy": "Texto muy persuasivo para Instagram basado en la imagen/video. Usa MUCHOS EMOJIS atractivos y añade hashtags relevantes al final. Si es comida, hazlo sonar delicioso. REGLA ESTRICTA: PROHIBIDO mencionar PedidosYa o Rappi. SOLO puedes mencionar Uber Eats si hablas explícitamente de delivery.",
                        "musica": "Nombre de una canción comercial en tendencia en Instagram/TikTok que combine con el post."
                        }}
                        """
                        
                        if is_video:
                            video_file = client.files.upload(file=img_promo_s1)
                            while video_file.state.name == "PROCESSING":
                                time.sleep(2)
                                video_file = client.files.get(name=video_file.name)
                            if video_file.state.name == "FAILED": raise Exception("Error procesando video en Gemini.")
                                
                            from google.genai import types
                            conf = types.GenerateContentConfig(response_mime_type="application/json")
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=[video_file, prompt_agente], config=conf)
                        else:
                            imagen_pil = Image.open(io.BytesIO(portada_bytes)).convert("RGB")
                            def llamar_ia_con_reintentos(prompt, imgs, max_intentos=3):
                                for i in range(max_intentos):
                                    try:
                                        from google.genai import types
                                        conf = types.GenerateContentConfig(response_mime_type="application/json")
                                        return client.models.generate_content(model='gemini-2.5-flash', contents=[prompt, *imgs], config=conf)
                                    except Exception as e:
                                        if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e): raise Exception("QUOTA")
                                        if i == max_intentos - 1: raise e
                                        time.sleep(4)
                            response = llamar_ia_con_reintentos(prompt_agente, [imagen_pil])
                            
                        datos_agente = json.loads(response.text.strip())
                        if "Automático" not in marca_forzada: datos_agente["marca"] = marca_forzada
                            
                    except Exception as e:
                        if str(e) == "QUOTA": raise e
                        st.error(f"Error IA: {e}")
                        datos_agente = {
                            "marca": marca_forzada, 
                            "copy": "🔥 ¡Atención! 🔥 Hoy tenemos una promoción que te dejará sin palabras. 🍔🌭 Visítanos y descubre por qué somos los favoritos. ¡No te quedes con el antojo! 👇\n\n#OfertaEspecial #FoodLovers #PromoDelDia",
                            "musica": "Canción viral en tendencia"
                        }
                        
                with st.spinner("🎨 Ensamblando Carrusel Final con tus Pantallas Oficiales..."):
                    datos_agente['marca'] = marca_forzada
                        
                    # SLIDE 2
                    img_promo_s2 = os.path.join(temp_dir, "promo_agente_s2.png")
                    try:
                        ruta_dir_oficial = os.path.join(BASE_DIR, "plantillas_fijas", "2_direcciones.png")
                        if os.path.exists(ruta_dir_oficial):
                            Image.open(ruta_dir_oficial).convert("RGB").resize((1080, 1080)).save(img_promo_s2, "PNG")
                        else:
                            s2_template = "logos/s2_hand_churrasco.png" if datos_agente['marca'] == "Churrasco Planet" else "logos/s2_hand_terraza.png"
                            Image.open(s2_template).convert("RGB").resize((1080, 1080)).save(img_promo_s2, "PNG")
                    except Exception as e:
                        st.error(f"Error generando Slide 2: {e}")
                        img_promo_s2 = None
                        
                    # SLIDE 3
                    img_promo_s3 = os.path.join(temp_dir, "promo_agente_s3.png")
                    try:
                        texto_cierre_fijo = "¡Comida de otro planeta! 🪐\n\nVisítanos en nuestras 4 direcciones:\n📍 Tegualda 1836, Ñuñoa.\n📍 Manuel Montt 1954, Providencia.\n📍 Toesca 1969, Santiago Centro.\n📍 El Olimpo 272, Maipú.\n\nCompra en: 🛒\nchurrascoplanet.cl\n\n#ChurrascoPlanet" if datos_agente['marca'] == "Churrasco Planet" else "¡Los mejores bajones de Santiago! 🍔\n\nVisítanos en:\n📍 Manuel Montt 1954, Providencia.\n📍 Toesca 1969, Santiago Centro.\n📍 El Olimpo 272, Maipú.\n\nCompra en: 🛒\nlaterrazafamiliar.cl\n\n#LaTerrazaFamiliar"
                        copy_final = f"{datos_agente.get('copy', '')}\n\n---\n{texto_cierre_fijo}"
                        generar_imagen_copy(copy_final, img_promo_s3, marca=datos_agente['marca'])
                    except Exception as e:
                        st.error(f"Error generando Slide 3: {e}")
                        img_promo_s3 = None
                        copy_final = "Error generando texto."
                
            except Exception as e:
                if str(e) == "QUOTA":
                    st.warning("⚠️ Límite de la API Gratuita de Google alcanzado. Espera 1 minuto.")
                    st.stop()
                else: raise e
            
            st.success("✨ ¡Tu paquete de Instagram está listo para publicarse!")
            
            c_txt, c_sim = st.columns([1, 2])
            with c_txt:
                st.info(f"🎵 **Música sugerida:** {datos_agente.get('musica', 'Audio Trending')}")
                st.text_area("Copiar Texto para Instagram:", copy_final, height=400)
                
                st.markdown("---")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(img_promo_s1, os.path.basename(img_promo_s1))
                    if img_promo_s2: zip_file.write(img_promo_s2, os.path.basename(img_promo_s2))
                    if img_promo_s3: zip_file.write(img_promo_s3, os.path.basename(img_promo_s3))
                    zip_file.writestr("texto_instagram.txt", copy_final)
                    
                st.download_button(
                    label="📥 DESCARGAR CARRUSEL (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="paquete_instagram_listo.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
                
            with c_sim:
                st.markdown("### Previsualización")
                cp1, cp2, cp3 = st.columns(3)
                if is_video: cp1.video(img_promo_s1); cp1.caption("1. Video")
                else: cp1.image(img_promo_s1, use_container_width=True, caption="1. Portada")
                if img_promo_s2: cp2.image(img_promo_s2, use_container_width=True, caption="2. Direcciones")
                if img_promo_s3: cp3.image(img_promo_s3, use_container_width=True, caption="3. Cierre")

# ----------------- VISTA 2 Y 3: ESTADOS DE RESULTADOS (P&L VERTICAL EN CASCADA) -----------------
elif "P&L:" in modulo_activo:
    sociedad_activa = "Sociedad_Principal" if "Principal" in modulo_activo else "Local_Maipu"
    titulo_vista = "Sociedad Principal (Providencia, Ñuñoa, Stgo Centro)" if "Principal" in modulo_activo else "Local Maipú (Independiente)"
    
    st.markdown(f"<div class='section-title'><span>📊</span> Estado de Resultados P&L - {titulo_vista}</div>", unsafe_allow_html=True)
    
    # Barra de Filtros de Fecha (Predeterminado desde el 1 de Enero para capturar historial)
    c_f1, c_f2 = st.columns(2)
    f_ini = c_f1.date_input("📅 Fecha Inicio Filtro", datetime(datetime.now().year, 1, 1)).isoformat()
    f_fin = c_f2.date_input("📅 Fecha Fin Filtro", datetime.now()).isoformat()
    
    st.markdown("---")
    
    # Obtener cálculo financiero en cascada
    pl_data = core.calcular_pl_consolidado(sociedad_activa, f_ini, f_fin)
    res = pl_data["resumen"]
    
    # TARJETAS KPI DE ALTO NIVEL (5 COLUMNAS) - COMPACT & BOLD
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🟢 Ingresos Totales", f"${res['ingresos_totales']:,.0f}")
    k2.metric("🟡 Compras / Costos Fijos", f"${res['costos_fijos_totales']:,.0f}")
    k3.metric("🛒 Proveedores Insumos", f"${res['proveedores_totales_neto']:,.0f}")
    k4.metric("🔴 Comisiones Apps", f"${res['comisiones_totales']:,.0f}")
    k5.metric("🏆 Margen Neto Real", f"${res['margen_neto']:,.0f}", f"{res['porcentaje_margen']:.1f}%")
    
    st.markdown("---")
    
    # CASCADA VERTICAL: SECCIÓN 1 - INGRESOS
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'><span>🟢 1.</span> Ingresos por Canal de Venta</div>", unsafe_allow_html=True)
    if pl_data["desglose_ingresos"]["por_canal"]:
        df_ing_canal = pd.DataFrame(list(pl_data["desglose_ingresos"]["por_canal"].items()), columns=["Canal de Venta", "Monto Ingresado"])
        st.dataframe(df_ing_canal.style.format({"Monto Ingresado": "${:,.0f}"}), use_container_width=True)
    else: st.info("No hay ingresos registrados en este periodo.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # CASCADA VERTICAL: SECCIÓN 2 - COMPRAS DIRECTAS Y COSTOS FIJOS
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'><span>🟡 2.</span> Compras Directas y Costos Fijos por Categoría</div>", unsafe_allow_html=True)
    if pl_data["desglose_costos_fijos"]["por_categoria"]:
        df_cf_cat = pd.DataFrame(list(pl_data["desglose_costos_fijos"]["por_categoria"].items()), columns=["Categoría de Costo", "Monto Gastado"])
        st.dataframe(df_cf_cat.style.format({"Monto Gastado": "${:,.0f}"}), use_container_width=True)
    else: st.info("No hay costos fijos registrados en este periodo.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # CASCADA VERTICAL: SECCIÓN 3 - PROVEEDORES RCV (INSUMOS)
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'><span>🛒 3.</span> Proveedores RCV SII (Insumos de Comida y Empaques)</div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.85rem; color:#8b949e; margin-bottom:15px;'>Listado ejecutivo agrupado por Razón Social. Haz clic en cada proveedor para auditar RUT, Folio y Fechas.</p>", unsafe_allow_html=True)
    
    df_provs = pl_data["raw_data"]["proveedores"]
    if not df_provs.empty:
        proveedores_agrupados = df_provs.groupby("nombre_proveedor")
        for nombre_prov, group in proveedores_agrupados:
            monto_total_prov = group['monto_total'].sum()
            with st.expander(f"🏢 {nombre_prov} — Monto Total: ${monto_total_prov:,.0f}"):
                df_detalle = group[["rut_proveedor", "folio", "monto_total", "fecha_emision"]].copy()
                df_detalle.columns = ["RUT / Deudor", "N° Factura (Folio)", "Monto Total ($)", "Fecha Emisión"]
                st.dataframe(df_detalle.style.format({"Monto Total ($)": "${:,.0f}"}), use_container_width=True)
                
        st.markdown("<p style='font-size:0.95rem; font-weight:700; color:#00f2fe; margin-top:20px; margin-bottom:8px;'>🏆 Top 5 Proveedores Mayores</p>", unsafe_allow_html=True)
        df_top_prov = pd.DataFrame(list(pl_data["desglose_proveedores"]["top_10"].items())[:5], columns=["Razón Social", "Monto Neto"])
        st.table(df_top_prov.style.format({"Monto Neto": "${:,.0f}"}))
    else: st.info("No hay facturas de proveedores de insumos en este periodo.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # CASCADA VERTICAL: SECCIÓN 4 - COMISIONES DE APLICACIONES Y TARJETAS
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'><span>🔴 4.</span> Comisiones de Aplicaciones y Tarjetas (SII)</div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.85rem; color:#8b949e; margin-bottom:10px;'>Facturas automáticas de Uber B.V., PedidosYa, Transbank y pasarelas de pago separadas para mantener la pureza contable.</p>", unsafe_allow_html=True)
    if not pl_data["raw_data"]["comisiones"].empty:
        df_com_cat = pl_data["raw_data"]["comisiones"].groupby("nombre_proveedor")["monto_neto"].sum().reset_index()
        df_com_cat.columns = ["Entidad / Aplicación", "Comisión Neta Facturada"]
        st.dataframe(df_com_cat.style.format({"Comisión Neta Facturada": "${:,.0f}"}), use_container_width=True)
    else: st.info("No hay facturas de comisiones de aplicaciones en este periodo.")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # SECCIÓN 5: POWERBI DASHBOARDS
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'><span>📈 5.</span> Inteligencia de Negocios (BI Dashboards)</div>", unsafe_allow_html=True)
    bi1, bi2 = st.columns(2)
    with bi1:
        st.markdown("<p style='font-size:0.9rem; font-weight:700; color:#c9d1d9;'>Distribución de Ingresos por Canal</p>", unsafe_allow_html=True)
        if not pl_data["raw_data"]["ingresos"].empty:
            df_bi_ing = pl_data["raw_data"]["ingresos"].groupby(["canal"])["monto"].sum().reset_index()
            st.bar_chart(df_bi_ing, x="canal", y="monto")
        else: st.info("Sin datos para graficar.")
    with bi2:
        st.markdown("<p style='font-size:0.9rem; font-weight:700; color:#c9d1d9;'>Distribución de Gasto en Insumos (IA)</p>", unsafe_allow_html=True)
        if not pl_data["raw_data"]["proveedores"].empty:
            df_bi_sii = pl_data["raw_data"]["proveedores"].groupby(["categoria_ia"])["monto_neto"].sum().reset_index()
            st.bar_chart(df_bi_sii, x="categoria_ia", y="monto_neto")
        else: st.info("Sin datos para graficar.")
    st.markdown("</div>", unsafe_allow_html=True)

# ----------------- VISTA 4: CARGA RCV SII Y REGISTRO MÓVIL -----------------
elif modulo_activo == "📥 Carga RCV SII & Registro Móvil":
    st.markdown("<div class='section-title'><span>📥</span> Centro de Ingesta de Datos y Registro Móvil</div>", unsafe_allow_html=True)
    
    c1_c, c2_c = st.columns(2)
    
    with c1_c:
        st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
        st.subheader("📥 1. Carga RCV del SII (Excel o CSV)")
        st.info("Sube el archivo mensual del SII. El sistema clasificará proveedores y separará las comisiones de apps automáticamente.")
        
        soc_ingesta = st.radio("Destino de Ingesta SII:", ["Sociedad Principal (3 Locales)", "Local Maipú (Independiente)"])
        soc_act_ing = "Sociedad_Principal" if "Principal" in soc_ingesta else "Local_Maipu"
        
        archivo_sii = st.file_uploader("Selecciona archivo RCV", type=["csv", "xlsx", "xls"], key="up_sii_mod")
        
        if archivo_sii:
            if st.button("⚡ Procesar Facturas SII con IA Gemini", type="primary", use_container_width=True):
                with st.spinner("🤖 Analizando facturas, separando comisiones y clasificando con Gemini..."):
                    try:
                        nuevas, duplicadas = core.procesar_archivo_sii(archivo_sii, archivo_sii.name, soc_act_ing, api_key)
                        st.success(f"✅ Proceso Completado: **{nuevas} facturas nuevas cargadas** | **{duplicadas} duplicadas ignoradas**.")
                    except Exception as e:
                        st.error(f"Error procesando archivo: {e}")
                        
        st.markdown("---")
        if st.button("🧹 Limpiar Facturas SII de esta Sociedad (Reiniciar Ingesta)", type="secondary", use_container_width=True):
            db.eliminar_facturas_sociedad(soc_act_ing)
            st.success("✅ Base de datos limpiada exitosamente. Ahora puedes volver a subir tu archivo del SII para una carga 100% limpia.")
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
                        
    with c2_c:
        st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
        st.subheader("📱 2. Ingreso Rápido Móvil")
        st.info("Reporta ingresos de ventas diarias o compras/costos fijos directos.")
        
        with st.form("form_movil_mod"):
            soc_form = st.radio("Sociedad:", ["Sociedad Principal", "Local Maipú"], horizontal=True)
            soc_act_form = "Sociedad_Principal" if "Principal" in soc_form else "Local_Maipu"
            
            tipo_reg = st.selectbox("Tipo de Movimiento", ["Ingreso Venta", "Costo Fijo Directo / Compra"])
            
            if "Principal" in soc_form:
                local_reg = st.selectbox("Local", ["Providencia", "Ñuñoa", "Santiago Centro"])
            else:
                local_reg = st.selectbox("Local", ["Maipú"])
                
            if tipo_reg == "Ingreso Venta":
                cat_reg = st.selectbox("Canal de Venta", ["UberEats", "PedidosYa", "Transbank", "Efectivo", "DidiFood", "Otro"])
            else:
                cat_reg = st.selectbox("Categoría de Costo", ["Sueldos y Leyes Sociales", "Arriendo", "Luz, Agua y Gas", "Marketing", "Mantención", "Insumo Directo", "Otro"])
                
            monto_reg = st.number_input("Monto ($ CLP)", min_value=0.0, step=1000.0)
            fecha_reg = st.date_input("Fecha", datetime.now()).isoformat()
            notas_reg = st.text_input("Notas (Opcional)")
            
            if st.form_submit_button("💾 Guardar Movimiento", type="primary", use_container_width=True):
                if monto_reg > 0:
                    if tipo_reg == "Ingreso Venta":
                        db.registrar_ingreso(soc_act_form, local_reg, cat_reg, monto_reg, fecha_reg, notas_reg)
                    else:
                        db.registrar_costo_fijo(soc_act_form, local_reg, cat_reg, monto_reg, fecha_reg, notas_reg)
                    st.success("✅ Registro guardado exitosamente en la base de datos.")
                else:
                    st.warning("⚠️ Ingresa un monto mayor a 0.")
        st.markdown("</div>", unsafe_allow_html=True)

# ----------------- VISTA 5: PLANTILLAS DE MARCA (CONFIGURACIÓN) -----------------
elif modulo_activo == "⚙️ Plantillas de Marca (Config)":
    st.markdown("<div class='section-title'><span>⚙️</span> Configuración de Plantillas Oficiales de Marca</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    st.write("Sube aquí el diseño corporativo para la **Segunda Pantalla** (Direcciones). El sistema pegará esta imagen automáticamente detrás de la Portada en todos tus carruseles de marketing.")
    
    ruta_dir = os.path.join(DIR_PLANTILLAS, "2_direcciones.png")
    
    if os.path.exists(ruta_dir): 
        st.success("✅ Tienes una plantilla activa instalada.")
        col1, col2 = st.columns([1, 3])
        with col1: st.image(ruta_dir, caption="Plantilla Actual", width=200)
    else:
        st.info("ℹ️ Estás usando la plantilla por defecto (Mano con teléfono).")
        
        file_dir = st.file_uploader("Actualizar Plantilla de Direcciones", type=["png", "jpg", "jpeg"])
        if file_dir:
            Image.open(file_dir).convert("RGB").save(ruta_dir, "PNG")
            st.success("Plantilla guardada exitosamente. Se aplicará a tus próximos ensamblados.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
