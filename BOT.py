# --- VISOR DE POLÍGONOS DE MONITOREO CON ANÁLISIS DE OCUPACIONES 20/06/2025 ---
# --- Visor de polígonos y análisis espacial con capa de puntos ---
# --- Miguel Guerrero / Adaptado por Gemini ---

import streamlit as st
import geopandas as gpd
import pandas as pd
import zipfile
import tempfile
import os
import folium
import requests
from io import BytesIO
from streamlit_folium import st_folium

st.set_page_config(page_title="Mapanima - Geovisor de Polígonos de Monitoreo y Análisis", layout="wide")

# --- Estilos generales e institucionales (Actualizados con la marca Bogotá) ---
st.markdown("""
    <style>
    /* Colores base de la marca Bogotá: Ajuste para un tono principal menos oscuro */
    :root {
        --bogota-blue-dark: #06038D; /* Pantone 2738 C - para acentos o texto oscuro */
        --bogota-blue-medium: #1C3F93; /* Nuevo color principal de fondo (antes era acento) */
        --bogota-blue-light: #5B8EE6; /* Un azul más claro para elementos interactivos */
        --text-color-light: white;
        --text-color-dark: black;
    }

    /* Estilos generales de la aplicación */
    html, body, .stApp {
        background-color: var(--bogota-blue-medium); /* Fondo azul medio de Bogotá */
        color: var(--text-color-light);
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--bogota-blue-dark); /* Sidebar con el azul oscuro principal */
        color: var(--text-color-light);
    }
    .stButton>button, .stDownloadButton>button {
        background-color: var(--bogota-blue-light); /* Botones con azul claro de Bogotá */
        color: var(--text-color-light);
        border: none;
        border-radius: 6px;
        transition: background-color 0.3s ease; /* Suaviza el cambio de color al pasar el ratón */
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #79A3EF; /* Tono ligeramente diferente al pasar el ratón */
    }
    /* Estilos para los campos de entrada */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>div>input {
        color: var(--text-color-dark);
        background-color: var(--text-color-light);
        border-radius: 4px;
    }
    /* Contorno para el mapa */
    .element-container:has(> iframe) {
        height: 650px !important;
        border: 2px solid var(--bogota-blue-light); /* Contorno con azul claro de Bogotá */
        border-radius: 8px;
    }
    /* Tooltips de Folium */
    .leaflet-tooltip {
        background-color: rgba(255, 255, 255, 0.9);
        color: var(--text-color-dark);
        font-weight: bold;
    }
    /* Dataframe de Streamlit */
    .stDataFrame {
        background-color: var(--text-color-light);
        color: var(--text-color-dark);
        border-radius: 8px;
    }
    /* Botones de descarga específicos */
    .stDownloadButton > button {
        background-color: var(--text-color-light);
        color: var(--bogota-blue-dark);
        border: 1px solid var(--bogota-blue-medium);
        border-radius: 6px;
        font-weight: bold;
    }
    /* Estilo para el pie de página fijo */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px 0;
        background-color: var(--bogota-blue-dark); /* Fondo azul oscuro */
        color: #b0c9a8; /* Texto claro (puede ajustarse a un tono de azul más claro si se prefiere) */
        font-size: 0.8em;
        z-index: 1000; /* Asegura que esté por encima de otros contenidos */
        border-top: 1px solid var(--bogota-blue-medium); /* Un borde sutil con azul medio */
    }
    /* Estilo para etiquetas (labels) de los widgets */
    label {
        color: var(--text-color-light) !important;
        font-weight: bold;
    }
    /* Asegurar que las etiquetas de checkbox y slider también sean blancas */
    .stCheckbox > label,
    .stSlider > label,
    .stCheckbox label > div, /* Nuevo selector para el texto anidado dentro del checkbox */
    .stSlider label > div { /* Nuevo selector para el texto anidado dentro del slider */
        color: var(--text-color-light) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Función para descargar y cargar archivos ZIP de shapefiles ---
@st.cache_data
def descargar_y_cargar_zip(url):
    """
    Descarga un archivo ZIP desde una URL, lo extrae, y carga el shapefile contenido
    en un GeoDataFrame, manejando diferentes codificaciones.
    """
    try:
        with st.spinner("Cargando datos geográficos principales... Esto puede tardar unos segundos."):
            r = requests.get(url)
            r.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
            with zipfile.ZipFile(BytesIO(r.content)) as zip_ref:
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_ref.extractall(tmpdir)
                    shp_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
                    if not shp_path:
                        st.error("❌ Error: No se encontró ningún archivo .shp en el ZIP descargado. Asegúrate de que el ZIP contenga un shapefile válido.")
                        return None
                    
                    gdf = None
                    try:
                        gdf = gpd.read_file(shp_path[0])
                    except Exception as e:
                        st.warning(f"⚠️ Advertencia: Error al cargar shapefile con encoding predeterminado. Intentando con 'latin1'. (Detalle: {e})")
                        try:
                            gdf = gpd.read_file(shp_path[0], encoding='latin1')
                        except Exception as e_latin1:
                            st.error(f"❌ Error crítico: No se pudo cargar el shapefile ni con encoding predeterminado ni con 'latin1'. (Detalle: {e_latin1})")
                            return None
                    
                    # Asegurarse de que el GeoDataFrame final esté en CRS 4326 para Folium
                    if gdf is not None and gdf.crs != "EPSG:4326":
                        st.info("ℹ️ Reproyectando datos a EPSG:4326 para compatibilidad con el mapa.")
                        gdf = gdf.to_crs(epsg=4326)

                    # Asegurarse de que 'Área_Ha_' sea numérica y sin NaN si existe
                    if gdf is not None and 'Área_Ha_' in gdf.columns:
                        gdf['Área_Ha_'] = pd.to_numeric(gdf['Área_Ha_'], errors='coerce').fillna(0).round(2)
                    
                    # Rellenar valores NaN con una cadena vacía y luego convertir todas las columnas no geométricas a tipo string
                    if gdf is not None:
                        for col in gdf.columns:
                            # Evitar convertir 'Área_Ha_' a string si es una columna numérica
                            if col != gdf.geometry.name and col != 'Área_Ha_': 
                                gdf[col] = gdf[col].fillna('').astype(str) 

                    return gdf

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP al descargar el archivo ZIP: {e}. Por favor, verifica la URL y tu conexión a internet.")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"❌ Error de conexión al descargar el archivo ZIP: {e}. Asegúrate de tener conexión a internet.")
        return None
    except zipfile.BadZipFile:
        st.error("❌ El archivo descargado no es un ZIP válido. Asegúrate de que la URL apunte a un archivo ZIP.")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar el archivo ZIP: {e}. Por favor, contacta al soporte.")
        return None

@st.cache_data
def descargar_y_cargar_zip_puntos(url):
    """
    Descarga un archivo ZIP de puntos desde una URL, lo extrae, y carga el shapefile contenido
    en un GeoDataFrame, manejando diferentes codificaciones y renombrando 'localidas' a 'Localidad'.
    """
    try:
        with st.spinner("Cargando datos de puntos... Esto puede tardar unos segundos."):
            r = requests.get(url)
            r.raise_for_status()
            with zipfile.ZipFile(BytesIO(r.content)) as zip_ref:
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_ref.extractall(tmpdir)
                    shp_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
                    if not shp_path:
                        st.error("❌ Error: No se encontró ningún archivo .shp en el ZIP de puntos. Asegúrate de que el ZIP contenga un shapefile válido.")
                        return None
                    
                    gdf = None
                    try:
                        gdf = gpd.read_file(shp_path[0])
                    except Exception as e:
                        st.warning(f"⚠️ Advertencia: Error al cargar shapefile de puntos con encoding predeterminado. Intentando con 'latin1'. (Detalle: {e})")
                        try:
                            gdf = gpd.read_file(shp_path[0], encoding='latin1')
                        except Exception as e_latin1:
                            st.error(f"❌ Error crítico: No se pudo cargar el shapefile de puntos ni con encoding predeterminado ni con 'latin1'. (Detalle: {e_latin1})")
                            return None
                    
                    if gdf is not None:
                        # Renombrar 'localidas' a 'Localidad'
                        if 'localidas' in gdf.columns:
                            gdf.rename(columns={'localidas': 'Localidad'}, inplace=True)
                            st.info("ℹ️ Columna 'localidas' renombrada a 'Localidad' en la capa de puntos.")
                        
                        # Asegurarse de que el GeoDataFrame final esté en CRS 4326 para Folium
                        if gdf.crs != "EPSG:4326":
                            st.info("ℹ️ Reproyectando datos de puntos a EPSG:4326 para compatibilidad con el mapa.")
                            gdf = gdf.to_crs(epsg=4326)

                        # Convertir columnas a string para consistencia, excepto geometría
                        for col in gdf.columns:
                            if col != gdf.geometry.name:
                                gdf[col] = gdf[col].fillna('').astype(str)
                    return gdf

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP al descargar el archivo ZIP de puntos: {e}. Por favor, verifica la URL y tu conexión a internet.")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"❌ Error de conexión al descargar el archivo ZIP de puntos: {e}. Asegúrate de tener conexión a internet.")
        return None
    except zipfile.BadZipFile:
        st.error("❌ El archivo descargado no es un ZIP de puntos válido. Asegúrate de que la URL apunte a un archivo ZIP.")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar el archivo ZIP de puntos: {e}. Por favor, contacta al soporte.")
        return None

# --- Cargar datos principales (polígonos) ---
url_zip_poligonos = "https://raw.githubusercontent.com/lmiguerrero/BOT/main/Pol_Monitoreo.zip"
gdf_poligonos = descargar_y_cargar_zip(url_zip_poligonos)

# --- Cargar datos de puntos ---
url_zip_puntos = "https://raw.githubusercontent.com/lmiguerrero/BOT/main/OcuIle25.zip"
gdf_puntos = descargar_y_cargar_zip_puntos(url_zip_puntos)


# --- Banner superior del visor ---
with st.container():
    st.image("https://placehold.co/800x100/1C3F93/FFFFFF?text=VISOR+GEOGRÁFICO", use_container_width=True) # 
# --- Pestañas del visor ---
tab1, tab2 = st.tabs(["🗺️ Visor Principal", "📊 Análisis de Ocupaciones"])

# --- TAB 1: VISOR PRINCIPAL (Polígonos) ---
with tab1:
    if gdf_poligonos is None:
        st.warning("⚠️ No se pudieron cargar los datos de polígonos principales. El visor no puede funcionar sin ellos.")
        st.stop() 

    st.subheader("🗺️ Visor de Polígonos de Monitoreo")
    st.markdown("Filtros, mapa y descarga de información cartográfica según filtros aplicados.")

    # --- Nombres de columnas relevantes para polígonos ---
    COLUMNAS_ATRIBUTOS_POLIGONOS = [
        'id_poligon', 'nombre_pol', 'Tipo_PMon', 'Localidad', 
        'En_Proceso', 'Provisiona', 'Consolidac', 'Caracter_1', 'Abordaje_s',
        'Total_2023', 'Lote_202', 'Lote_203', 'En_Proce_1', 'Provisio_1', 
        'Consolid_1', 'Total_2025', 'Increment_1'
    ]

    # Asegurar que las columnas existan y manejar sus tipos para polígonos
    for col_name in COLUMNAS_ATRIBUTOS_POLIGONOS:
        if col_name in gdf_poligonos.columns:
            gdf_poligonos[col_name] = gdf_poligonos[col_name].astype(str).str.lower().fillna('')
        else:
            gdf_poligonos[col_name] = '' 

    st.sidebar.header("🎯 Filtros Polígonos")

    # Filtro por 'Localidad' (multiselect) - POLÍGONOS
    localidad_opciones_poligonos = sorted(gdf_poligonos['Localidad'].unique())
    localidad_sel_poligonos = st.sidebar.multiselect(
        "Filtrar por Localidad (Polígonos)", 
        options=localidad_opciones_poligonos, 
        placeholder="Selecciona una o más localidades"
    )

    # Filtro por 'nombre_pol' (selectbox, una sola selección) - POLÍGONOS
    nombre_pol_opciones_poligonos = sorted(gdf_poligonos['nombre_pol'].unique())
    nombre_pol_seleccionado_poligonos = st.sidebar.selectbox(
        "🔍 Buscar por nombre de Polígono (nombre_pol)", 
        options=[""] + nombre_pol_opciones_poligonos, 
        index=0, 
        placeholder="Selecciona un nombre"
    )

    # Sección de configuración del mapa (se mantiene)
    fondos_disponibles = {
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB Claro (Positron)": "CartoDB positron",
        "CartoDB Oscuro": "CartoDB dark_matter",
        "Satélite (Esri)": "Esri.WorldImagery",
        "Esri NatGeo World Map": "Esri.NatGeoWorldMap",
        "Esri World Topo Map": "Esri.WorldTopoMap"
    }
    fondo_seleccionado_poligonos = st.sidebar.selectbox("🗺️ Fondo del mapa (Polígonos)", list(fondos_disponibles.keys()), index=1)

    st.sidebar.header("🎨 Estilos del Mapa Polígonos")
    mostrar_relleno_poligonos = st.sidebar.checkbox("Mostrar relleno de polígonos", value=True)

    # Botones de acción para polígonos
    if "mostrar_mapa_poligonos" not in st.session_state:
        st.session_state["mostrar_mapa_poligonos"] = False

    col_botones_poligonos = st.sidebar.columns(2)
    with col_botones_poligonos[0]:
        if st.button("🧭 Aplicar filtros y mostrar mapa (Polígonos)"):
            st.session_state["mostrar_mapa_poligonos"] = True
    with col_botones_poligonos[1]:
        if st.button("🔄 Reiniciar visor (Polígonos)"):
            st.session_state["mostrar_mapa_poligonos"] = False
            st.rerun()

    if st.session_state["mostrar_mapa_poligonos"]:
        gdf_filtrado_poligonos = gdf_poligonos.copy()
        
        # Aplicar filtros a polígonos
        if localidad_sel_poligonos:
            localidad_sel_poligonos_lower = [loc.lower() for loc in localidad_sel_poligonos]
            gdf_filtrado_poligonos = gdf_filtrado_poligonos[gdf_filtrado_poligonos["Localidad"].isin(localidad_sel_poligonos_lower)]
        
        if nombre_pol_seleccionado_poligonos and nombre_pol_seleccionado_poligonos != "":
            gdf_filtrado_poligonos = gdf_filtrado_poligonos[gdf_filtrado_poligonos["nombre_pol"] == nombre_pol_seleccionado_poligonos.lower()]

        st.subheader("🗺️ Mapa de Polígonos filtrado")

        if not gdf_filtrado_poligonos.empty:
            if 'Área_Ha_' in gdf_filtrado_poligonos.columns:
                gdf_filtrado_poligonos["area_formateada"] = gdf_filtrado_poligonos["Área_Ha_"].apply(
                    lambda ha: f"{int(ha):,} ha + {int(round((ha - int(ha)) * 10000)):,} m²" if ha >= 0 else "N/A"
                )
            else:
                gdf_filtrado_poligonos["area_formateada"] = "N/A"
            
            bounds_poligonos = gdf_filtrado_poligonos.total_bounds
            centro_lat_poligonos = (bounds_poligonos[1] + bounds_poligonos[3]) / 2
            centro_lon_poligonos = (bounds_poligonos[0] + bounds_poligonos[2]) / 2
            
            with st.spinner("Generando mapa de polígonos..."):
                m_poligonos = folium.Map(location=[centro_lat_poligonos, centro_lon_poligonos], zoom_start=8, tiles=fondos_disponibles[fondo_seleccionado_poligonos])

                def style_function_poligonos(feature):
                    return {
                        "fillColor": "#5B8EE6",
                        "color": "#1C3F93",
                        "weight": 1.5,
                        "fillOpacity": 0.6 if mostrar_relleno_poligonos else 0
                    }

                tooltip_fields_poligonos = [
                    "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad", "area_formateada",
                    "En_Proceso", "Provisiona", "Consolidac", "Caracter_1", "Abordaje_s",
                    "Total_2023", "Lote_202", "Lote_203", "En_Proce_1", "Provisio_1", 
                    "Consolid_1", "Total_2025", "Increment_1"
                ]
                tooltip_aliases_poligonos = [
                    "ID Polígono:", "Nombre Polígono:", "Tipo Monitoreo:", "Localidad:", "Área (Ha):",
                    "En Proceso:", "Provisional:", "Consolidado:", "Carácter:", "Abordaje:",
                    "Total 2023:", "Lote 202:", "Lote 203:", "En Proceso 1:", "Provisional 1:", 
                    "Consolidado 1:", "Total 2025:", "Incremento 1:"
                ]
                
                final_tooltip_fields_poligonos = []
                final_tooltip_aliases_poligonos = []
                for i, field in enumerate(tooltip_fields_poligonos):
                    if field in gdf_filtrado_poligonos.columns or field == 'area_formateada':
                        final_tooltip_fields_poligonos.append(field)
                        final_tooltip_aliases_poligonos.append(tooltip_aliases_poligonos[i])


                folium.GeoJson(
                    gdf_filtrado_poligonos,
                    name="Polígonos de Monitoreo",
                    style_function=style_function_poligonos,
                    tooltip=folium.GeoJsonTooltip(
                        fields=final_tooltip_fields_poligonos,
                        aliases=final_tooltip_aliases_poligonos,
                        localize=True
                    )
                ).add_to(m_poligonos)

                m_poligonos.fit_bounds([[bounds_poligonos[1], bounds_poligonos[0]], [bounds_poligonos[3], bounds_poligonos[2]]])

                leyenda_html_poligonos = '''
                <div style="position: absolute; bottom: 10px; right: 10px; z-index: 9999;
                            background-color: white; padding: 10px; border: 1px solid #ccc;
                            font-size: 14px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
                    <strong>Leyenda</strong><br>
                    <i style="background:#5B8EE6; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid #1C3F93;"></i> Polígono de Monitoreo<br>
                </div>
                '''
                m_poligonos.get_root().html.add_child(folium.Element(leyenda_html_poligonos))

                st_folium(m_poligonos, width=1200, height=600)
        else:
            st.warning("⚠️ No se encontraron polígonos que coincidan con los filtros aplicados. Por favor, ajusta tus selecciones.")

        st.subheader("📋 Resultados filtrados (Polígonos)")
        if not gdf_filtrado_poligonos.empty:
            cols_to_display_poligonos = [
                "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad", "Área_Ha_",
                "En_Proceso", "Provisiona", "Consolidac", "Total_2023", "Lote_202",
                "Lote_203", "En_Proce_1", "Provisio_1", "Consolid_1", "Total_2025",
                "Increment_1", "Caracter_1", "Abordaje_s"
            ]
            cols_to_display_poligonos = [col for col in cols_to_display_poligonos if col in gdf_filtrado_poligonos.columns]

            gdf_filtrado_display_poligonos = gdf_filtrado_poligonos[cols_to_display_poligonos].copy()
            if 'Área_Ha_' in gdf_filtrado_display_poligonos.columns:
                gdf_filtrado_display_poligonos['Área_Ha_'] = gdf_filtrado_display_poligonos['Área_Ha_'].apply(
                    lambda x: f"{int(x):,} ha + {int(round((x - int(x)) * 10000)):,} m²" if pd.notna(x) and x >= 0 else "N/A"
                )

            st.dataframe(gdf_filtrado_display_poligonos)

            with st.expander("📥 Opciones de descarga (Polígonos)"):
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    with tempfile.TemporaryDirectory() as tmpdir_export:
                        shp_base_path = os.path.join(tmpdir_export, "poligonos_monitoreo_filtrados")
                        gdf_filtrado_for_save = gdf_filtrado_poligonos.copy()
                        if gdf_filtrado_for_save.crs is None:
                            gdf_filtrado_for_save.set_crs(epsg=4326, inplace=True)
                        gdf_filtrado_for_save.to_file(shp_base_path + ".shp")

                        for file in os.listdir(tmpdir_export):
                            zf.write(os.path.join(tmpdir_export, file), file)
                zip_buffer.seek(0)

                st.download_button(
                    label="📅 Descargar shapefile filtrado (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="poligonos_monitoreo_filtrados.zip",
                    mime="application/zip"
                )

                html_bytes = m_poligonos.get_root().render().encode("utf-8")
                st.download_button(
                    label="🌐 Descargar mapa (HTML)",
                    data=html_bytes,
                    file_name="mapa_monitoreo_filtrado.html",
                    mime="text/html"
                )
        else:
            st.info("No hay datos de polígonos para mostrar en la tabla o descargar con los filtros actuales.")

# --- TAB 2: ANÁLISIS DE OCUPACIONES (Puntos) ---
with tab2:
    st.subheader("📊 Análisis de Ocupaciones por Polígono")
    st.markdown("Realiza un análisis espacial para contar las ocupaciones (puntos) dentro de cada polígono de monitoreo.")

    if gdf_poligonos is None or gdf_puntos is None:
        st.warning("⚠️ No se pudieron cargar los datos de polígonos o de puntos. El análisis no puede funcionar sin ambos.")
        st.stop()

    st.info("Cargando y procesando puntos para el análisis. Esto puede tardar un momento...")

    # Realizar el Spatial Join
    # Asegúrate de que ambas capas tengan una columna de índice única si no tienen una.
    # Convertir 'id_poligon' y 'id_ocupac' a string para asegurar consistencia en el merge si los tipos originales varían
    gdf_poligonos_for_join = gdf_poligonos.copy()
    if 'id_poligon' in gdf_poligonos_for_join.columns:
        gdf_poligonos_for_join['id_poligon'] = gdf_poligonos_for_join['id_poligon'].astype(str)

    gdf_puntos_for_join = gdf_puntos.copy()
    if 'id_ocupac' in gdf_puntos_for_join.columns:
        gdf_puntos_for_join['id_ocupac'] = gdf_puntos_for_join['id_ocupac'].astype(str)
    
    # Asegúrate de que las columnas de nombre y localidad estén en el formato correcto (string) y en minúsculas
    for col in ['nombre_pol', 'Localidad']:
        if col in gdf_poligonos_for_join.columns:
            gdf_poligonos_for_join[col] = gdf_poligonos_for_join[col].astype(str).str.lower()
    if 'Localidad' in gdf_puntos_for_join.columns: # Points layer also has Localidad (after renaming from 'localidas')
        gdf_puntos_for_join['Localidad'] = gdf_puntos_for_join['Localidad'].astype(str).str.lower()


    try:
        # Spatial join: Encontrar qué puntos caen dentro de qué polígonos
        # Usamos `how='left'` para mantener todos los polígonos, incluso si no tienen puntos.
        # Luego filtraremos para los que sí tienen intersección si es necesario.
        # Es crucial que la capa de polígonos sea la `right` para que los atributos de polígono se unan a los puntos.
        # Pero para contar puntos *por* polígono, queremos el resultado de la unión de puntos *a* polígonos.
        # Usaremos `inner` join y luego contaremos, lo que es más directo para "puntos por polígono".
        
        # Primero, asegúrate de que el CRS sea el mismo para el sjoin
        if gdf_poligonos_for_join.crs != gdf_puntos_for_join.crs:
            gdf_puntos_for_join = gdf_puntos_for_join.to_crs(gdf_poligonos_for_join.crs)

        gdf_joined_analysis = gpd.sjoin(gdf_puntos_for_join, gdf_poligonos_for_join, how="inner", predicate="within")

        st.success(f"Se encontraron {len(gdf_joined_analysis)} ocupaciones con correspondencia en polígonos.")

        if not gdf_joined_analysis.empty:
            # Contar la cantidad de ocupaciones por polígono (usando el id_poligon de la capa de polígonos)
            conteo_ocupaciones = gdf_joined_analysis.groupby('id_poligon').size().reset_index(name='Cantidad_Ocupaciones')

            # Unir el conteo con la información original de los polígonos
            # Seleccionamos solo las columnas relevantes de los polígonos para la tabla final
            poligono_info_cols_for_analysis = ['id_poligon', 'nombre_pol', 'Localidad', 'Área_Ha_']
            poligono_info_cols_for_analysis = [col for col in poligono_info_cols_for_analysis if col in gdf_poligonos.columns]

            # Aseguramos que 'id_poligon' sea string en ambos para el merge
            df_resultado_analisis = pd.merge(
                gdf_poligonos[poligono_info_cols_for_analysis].astype({'id_poligon': str}),
                conteo_ocupaciones.astype({'id_poligon': str}),
                on='id_poligon',
                how='left'
            ).fillna({'Cantidad_Ocupaciones': 0}) # Rellenar polígonos sin ocupaciones con 0

            df_resultado_analisis['Cantidad_Ocupaciones'] = df_resultado_analisis['Cantidad_Ocupaciones'].astype(int)
            
            # Formatear el Área_Ha_ para la tabla de resultados del análisis
            if 'Área_Ha_' in df_resultado_analisis.columns:
                df_resultado_analisis["Área_Ha_"] = df_resultado_analisis["Área_Ha_"].apply(
                    lambda ha: f"{int(ha):,} ha + {int(round((ha - int(ha)) * 10000)):,} m²" if pd.notna(ha) and ha >= 0 else "N/A"
                )

            st.markdown("### 📈 Resumen de Ocupaciones por Polígono")
            st.dataframe(df_resultado_analisis)

            # Visualización de los resultados en el mapa
            if st.checkbox("Mostrar mapa de análisis (Polígonos con Puntos)", value=True):
                # Calcular bounds que incluyan ambas capas si ambas tienen geometrías
                bounds_union = gdf_poligonos.total_bounds
                if not gdf_puntos.empty:
                    # Concat para calcular los bounds de ambos juntos
                    combined_gdf = gpd.GeoDataFrame(pd.concat([gdf_poligonos.geometry, gdf_puntos.geometry], ignore_index=True), crs=gdf_poligonos.crs)
                    bounds_union = combined_gdf.total_bounds
                
                centro_lat_analisis = (bounds_union[1] + bounds_union[3]) / 2
                centro_lon_analisis = (bounds_union[0] + bounds_union[2]) / 2

                with st.spinner("Generando mapa de análisis..."):
                    m_analisis = folium.Map(location=[centro_lat_analisis, centro_lon_analisis], zoom_start=8, tiles=fondos_disponibles["OpenStreetMap"]) # Usar un fondo neutro

                    # Añadir polígonos
                    folium.GeoJson(
                        gdf_poligonos,
                        name="Polígonos de Monitoreo",
                        style_function=lambda x: {
                            "fillColor": "#5B8EE6",
                            "color": "#1C3F93",
                            "weight": 1.5,
                            "fillOpacity": 0.3
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=['id_poligon', 'nombre_pol', 'Localidad', 'Área_Ha_'],
                            aliases=['ID Polígono:', 'Nombre:', 'Localidad:', 'Área (Ha):'],
                            localize=True
                        )
                    ).add_to(m_analisis)

                    # Añadir puntos de ocupación
                    folium.GeoJson(
                        gdf_puntos,
                        name="Puntos de Ocupación",
                        marker=folium.CircleMarker(radius=3, fill_color="#FF0000", color="#FF0000", fill_opacity=0.7),
                        tooltip=folium.GeoJsonTooltip(
                            fields=['id_ocupac', 'Clasific', 'id_predio', 'Localidad', 'Fecha_Ocu', 'Observacio'],
                            aliases=['ID Ocupación:', 'Clasificación:', 'ID Predio:', 'Localidad:', 'Fecha Ocupación:', 'Observación:'],
                            localize=True
                        )
                    ).add_to(m_analisis)

                    folium.LayerControl().add_to(m_analisis) # Añadir control de capas

                    st_folium(m_analisis, width=1200, height=600)

            # Opciones de descarga para el análisis
            with st.expander("📥 Opciones de descarga (Análisis de Ocupaciones)"):
                csv_analisis = df_resultado_analisis.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Descargar resultados de análisis como CSV",
                    data=csv_analisis,
                    file_name="analisis_ocupaciones_por_poligono.csv",
                    mime="text/csv"
                )

        else:
            st.info("No se encontraron ocupaciones dentro de los polígonos de monitoreo.")

    except Exception as e:
        st.error(f"❌ Error al realizar el análisis de ocupaciones: {e}")
        st.exception(e)


# --- Footer global para la pantalla principal del visor ---
st.markdown(
    """
    <div class="fixed-footer">
        Realizado por Ing. Topográfico Luis Miguel Guerrero | © 2025. Contacto: luis.guerrero@urt.gov.co
    </div>
    """,
    unsafe_allow_html=True
)
