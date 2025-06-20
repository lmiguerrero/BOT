# --- VISOR DE POLÍGONOS DE MONITOREO UNIFICADO 20/06/2025 ---
# --- Visor de polígonos y análisis de ocupaciones en una sola vista ---
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

st.set_page_config(page_title="Mapanima - Geovisor de Monitoreo Unificado", layout="wide")

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
    /* Estilo para el cuadro de estadísticas de ocupaciones */
    .stats-box {
        margin-top: 1em;
        margin-bottom: 1.5em;
        padding: 0.7em;
        background-color: white; /* Fondo blanco puro */
        border-radius: 8px;
        font-size: 16px;
        color: var(--bogota-blue-dark); /* Texto oscuro */
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
                    
                    # Rellenar valores NaN con una cadena vacía y luego convertir todas las columnas no geométricas a tipo string
                    if gdf is not None:
                        for col in gdf.columns:
                            if col != gdf.geometry.name:
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
# --- VISOR PRINCIPAL (TODO EN UNA PESTAÑA) ---
if gdf_poligonos is None:
    st.warning("⚠️ No se pudieron cargar los datos de polígonos principales. El visor no puede funcionar sin ellos.")
    st.stop() 

st.subheader("🗺️ Visor de Polígonos de Monitoreo y Ocupaciones")
st.markdown("Filtros, mapa y descarga de información cartográfica según filtros aplicados.")

# --- Nombres de columnas relevantes para polígonos ---
COLUMNAS_ATRIBUTOS_POLIGONOS = [
    'id_poligon', 'nombre_pol', 'Tipo_PMon', 'Localidad', 
    'En_Proceso', 'Provisiona', 'Consolidac', 'Caracter_1', 'Abordaje_s',
    'Total_2023', 'Lote_202', 'Lote_203', 'En_Proce_1', 'Provisio_1', 
    'Consolid_1', 'Total_2025', 'Increment_1'
]
# Las columnas del shapefile de puntos se manejarán al activar la opción de ocupaciones.

# Asegurar que las columnas existan y manejar sus tipos para polígonos
for col_name in COLUMNAS_ATRIBUTOS_POLIGONOS:
    if col_name in gdf_poligonos.columns:
        gdf_poligonos[col_name] = gdf_poligonos[col_name].astype(str).str.lower().fillna('')
    else:
        gdf_poligonos[col_name] = '' 

st.sidebar.header("🎯 Filtros")

# Filtro por 'Localidad' (multiselect)
localidad_opciones = sorted(gdf_poligonos['Localidad'].unique())
localidad_sel = st.sidebar.multiselect(
    "Filtrar por Localidad", 
    options=localidad_opciones, 
    placeholder="Selecciona una o más localidades"
)

# Filtro por 'nombre_pol' (selectbox, una sola selección)
nombre_pol_opciones = sorted(gdf_poligonos['nombre_pol'].unique())
nombre_pol_seleccionado = st.sidebar.selectbox(
    "🔍 Buscar por nombre de Polígono (nombre_pol)", 
    options=[""] + nombre_pol_opciones, 
    index=0, 
    placeholder="Selecciona un nombre"
)

# Sección de configuración del mapa
fondos_disponibles = {
    "OpenStreetMap": "OpenStreetMap",
    "CartoDB Claro (Positron)": "CartoDB positron",
    "CartoDB Oscuro": "CartoDB dark_matter",
    "Satélite (Esri)": "Esri.WorldImagery",
    "Esri NatGeo World Map": "Esri.NatGeoWorldMap",
    "Esri World Topo Map": "Esri.WorldTopoMap"
}
fondo_seleccionado = st.sidebar.selectbox("🗺️ Fondo del mapa", list(fondos_disponibles.keys()), index=1)

st.sidebar.header("🎨 Estilos del Mapa")
mostrar_relleno_poligonos = st.sidebar.checkbox("Mostrar relleno de polígonos", value=True)

# --- Nueva opción para ver ocupaciones ---
if gdf_puntos is not None:
    ver_ocupaciones = st.sidebar.checkbox("Ver ocupaciones", value=False)
else:
    ver_ocupaciones = False
    st.sidebar.info("Capa de ocupaciones no disponible para visualización.")


# Botones de acción
if "mostrar_mapa" not in st.session_state:
    st.session_state["mostrar_mapa"] = False

col_botones = st.sidebar.columns(2)
with col_botones[0]:
    if st.button("🧭 Aplicar filtros y mostrar mapa"):
        st.session_state["mostrar_mapa"] = True
with col_botones[1]:
    if st.button("🔄 Reiniciar visor"):
        st.session_state["mostrar_mapa"] = False
        st.rerun()

# Lógica para mostrar el mapa y la tabla de resultados
if st.session_state["mostrar_mapa"]:
    gdf_filtrado_poligonos = gdf_poligonos.copy()
    gdf_puntos_filtrados = None
    total_ocupaciones_filtradas = 0

    # Aplicar filtros a polígonos
    if localidad_sel:
        localidad_sel_lower = [loc.lower() for loc in localidad_sel]
        gdf_filtrado_poligonos = gdf_filtrado_poligonos[gdf_filtrado_poligonos["Localidad"].isin(localidad_sel_lower)]
    
    if nombre_pol_seleccionado and nombre_pol_seleccionado != "":
        gdf_filtrado_poligonos = gdf_filtrado_poligonos[gdf_filtrado_poligonos["nombre_pol"] == nombre_pol_seleccionado.lower()]

    st.subheader("🗺️ Mapa filtrado")

    if not gdf_filtrado_poligonos.empty:
        # Preparar GeoDataFrame de puntos para el join y visualización si aplica
        if ver_ocupaciones and gdf_puntos is not None:
            st.info("Realizando análisis espacial de ocupaciones...")
            # Asegúrate de que los CRS sean los mismos para el sjoin
            if gdf_poligonos.crs != gdf_puntos.crs:
                gdf_puntos_temp = gdf_puntos.to_crs(gdf_poligonos.crs)
            else:
                gdf_puntos_temp = gdf_puntos.copy()

            # Realizar spatial join para obtener solo los puntos dentro de los polígonos filtrados
            # y obtener los atributos del polígono para el conteo
            try:
                gdf_puntos_en_poligonos = gpd.sjoin(gdf_puntos_temp, gdf_filtrado_poligonos[['geometry', 'id_poligon']], how="inner", predicate="within")
                
                # Contar ocupaciones por polígono
                conteo_ocupaciones = gdf_puntos_en_poligonos.groupby('id_poligon').size().reset_index(name='Cantidad_Ocupaciones')
                total_ocupaciones_filtradas = conteo_ocupaciones['Cantidad_Ocupaciones'].sum()

                # Unir el conteo a los polígonos filtrados para mostrar en la tabla y tooltip
                gdf_filtrado_poligonos = pd.merge(
                    gdf_filtrado_poligonos,
                    conteo_ocupaciones,
                    on='id_poligon',
                    how='left'
                ).fillna({'Cantidad_Ocupaciones': 0})
                gdf_filtrado_poligonos['Cantidad_Ocupaciones'] = gdf_filtrado_poligonos['Cantidad_Ocupaciones'].astype(int)

                gdf_puntos_filtrados = gdf_puntos_en_poligonos # Usar estos puntos para la visualización

            except Exception as e:
                st.error(f"❌ Error durante el análisis espacial de ocupaciones: {e}")
                gdf_puntos_filtrados = None # No mostrar puntos si hay error

        bounds = gdf_filtrado_poligonos.total_bounds
        centro_lat = (bounds[1] + bounds[3]) / 2
        centro_lon = (bounds[0] + bounds[2]) / 2
        
        with st.spinner("Generando mapa..."):
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=8, tiles=fondos_disponibles[fondo_seleccionado])

            def style_function_poligonos(feature):
                return {
                    "fillColor": "#5B8EE6",
                    "color": "#1C3F93",
                    "weight": 1.5,
                    "fillOpacity": 0.6 if mostrar_relleno_poligonos else 0
                }

            tooltip_fields_poligonos = [
                "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad",
                "En_Proceso", "Provisiona", "Consolidac", "Caracter_1", "Abordaje_s",
                "Total_2023", "Lote_202", "Lote_203", "En_Proce_1", "Provisio_1", 
                "Consolid_1", "Total_2025", "Increment_1"
            ]
            tooltip_aliases_poligonos = [
                "ID Polígono:", "Nombre Polígono:", "Tipo Monitoreo:", "Localidad:",
                "En Proceso:", "Provisional:", "Consolidado:", "Carácter:", "Abordaje:",
                "Total 2023:", "Lote 202:", "Lote 203:", "En Proceso 1:", "Provisional 1:", 
                "Consolidado 1:", "Total 2025:", "Incremento 1:"
            ]

            if ver_ocupaciones and gdf_puntos is not None and 'Cantidad_Ocupaciones' in gdf_filtrado_poligonos.columns:
                tooltip_fields_poligonos.append('Cantidad_Ocupaciones')
                tooltip_aliases_poligonos.append('Ocupaciones en Polígono:')
            
            final_tooltip_fields_poligonos = []
            final_tooltip_aliases_poligonos = []
            for i, field in enumerate(tooltip_fields_poligonos):
                if field in gdf_filtrado_poligonos.columns:
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
            ).add_to(m)

            # Añadir capa de puntos si 'Ver ocupaciones' está marcado y hay puntos filtrados
            if ver_ocupaciones and gdf_puntos_filtrados is not None and not gdf_puntos_filtrados.empty:
                tooltip_fields_puntos = ['id_ocupac', 'Clasific', 'id_predio', 'Localidad', 'Fecha_Ocu', 'Observacio']
                tooltip_aliases_puntos = ['ID Ocupación:', 'Clasificación:', 'ID Predio:', 'Localidad:', 'Fecha Ocupación:', 'Observación:']
                
                final_tooltip_fields_puntos = []
                final_tooltip_aliases_puntos = []
                for i, field in enumerate(tooltip_fields_puntos):
                    if field in gdf_puntos_filtrados.columns:
                        final_tooltip_fields_puntos.append(field)
                        final_tooltip_aliases_puntos.append(tooltip_aliases_puntos[i])

                folium.GeoJson(
                    gdf_puntos_filtrados,
                    name="Ocupaciones Filtradas",
                    marker=folium.CircleMarker(radius=5, fill_color="#FF0000", color="#FF0000", fill_opacity=0.7),
                    tooltip=folium.GeoJsonTooltip(
                        fields=final_tooltip_fields_puntos,
                        aliases=final_tooltip_aliases_puntos,
                        localize=True
                    )
                ).add_to(m)
            
            folium.LayerControl().add_to(m) # Añadir control de capas

            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

            leyenda_html_poligonos = '''
            <div style="position: absolute; bottom: 10px; right: 10px; z-index: 9999;
                        background-color: white; padding: 10px; border: 1px solid #ccc;
                        font-size: 14px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
                <strong>Leyenda</strong><br>
                <i style="background:#5B8EE6; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid #1C3F93;"></i> Polígono de Monitoreo<br>
                <i style="background:#FF0000; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid #FF0000;"></i> Ocupación (Punto)<br>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(leyenda_html_poligonos))

            st_folium(m, width=1200, height=600)
    else:
        st.warning("⚠️ No se encontraron polígonos que coincidan con los filtros aplicados. Por favor, ajusta tus selecciones.")

    st.subheader("📋 Resultados filtrados")
    if not gdf_filtrado_poligonos.empty:
        cols_to_display_poligonos = [
            "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad",
            "En_Proceso", "Provisiona", "Consolidac", "Total_2023", "Lote_202",
            "Lote_203", "En_Proce_1", "Provisio_1", "Consolid_1", "Total_2025",
            "Increment_1", "Caracter_1", "Abordaje_s"
        ]
        if 'Cantidad_Ocupaciones' in gdf_filtrado_poligonos.columns:
            cols_to_display_poligonos.append('Cantidad_Ocupaciones')

        cols_to_display_poligonos = [col for col in cols_to_display_poligonos if col in gdf_filtrado_poligonos.columns]

        gdf_filtrado_display_poligonos = gdf_filtrado_poligonos[cols_to_display_poligonos].copy()

        st.dataframe(gdf_filtrado_display_poligonos)

        # Cuadro de estadísticas de ocupaciones
        if ver_ocupaciones and gdf_puntos is not None:
            st.markdown(
                f'''
                <div class="stats-box">
                    <strong>📊 Estadísticas de Ocupaciones:</strong><br>
                    Ocupaciones visibles en polígonos filtrados: <strong>{total_ocupaciones_filtradas}</strong>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with st.expander("📥 Opciones de descarga"):
            # Para descargar el shapefile de polígonos filtrados
            zip_buffer_poligonos = BytesIO()
            with zipfile.ZipFile(zip_buffer_poligonos, 'w', zipfile.ZIP_DEFLATED) as zf:
                with tempfile.TemporaryDirectory() as tmpdir_export_poligonos:
                    shp_base_path_poligonos = os.path.join(tmpdir_export_poligonos, "poligonos_monitoreo_filtrados")
                    gdf_filtrado_for_save_poligonos = gdf_filtrado_poligonos.copy()
                    if gdf_filtrado_for_save_poligonos.crs is None:
                        gdf_filtrado_for_save_poligonos.set_crs(epsg=4326, inplace=True)
                    # Excluir 'Cantidad_Ocupaciones' si no quieres que sea parte del shapefile, o conviértela si es necesario.
                    # Para simplificar, la guardamos tal cual, GeoPandas manejará el tipo de columna.
                    gdf_filtrado_for_save_poligonos.to_file(shp_base_path_poligonos + ".shp")

                    for file in os.listdir(tmpdir_export_poligonos):
                        zf.write(os.path.join(tmpdir_export_poligonos, file), file)
            zip_buffer_poligonos.seek(0)

            st.download_button(
                label="📅 Descargar shapefile de polígonos filtrado (.zip)",
                data=zip_buffer_poligonos.getvalue(),
                file_name="poligonos_monitoreo_filtrados.zip",
                mime="application/zip"
            )

            # Descargar mapa HTML
            html_bytes_mapa = m.get_root().render().encode("utf-8")
            st.download_button(
                label="🌐 Descargar mapa (HTML)",
                data=html_bytes_mapa,
                file_name="mapa_monitoreo_filtrado.html",
                mime="text/html"
            )

            # Descargar tabla de resultados como CSV (ahora incluye Cantidad_Ocupaciones)
            csv_resultados = gdf_filtrado_display_poligonos.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Descargar tabla de resultados como CSV",
                data=csv_resultados,
                file_name="resultados_filtrados.csv",
                mime="text/csv"
            )

            # Descargar puntos filtrados si están visibles
            if ver_ocupaciones and gdf_puntos_filtrados is not None and not gdf_puntos_filtrados.empty:
                zip_buffer_puntos = BytesIO()
                with zipfile.ZipFile(zip_buffer_puntos, 'w', zipfile.ZIP_DEFLATED) as zf_puntos:
                    with tempfile.TemporaryDirectory() as tmpdir_export_puntos:
                        shp_base_path_puntos = os.path.join(tmpdir_export_puntos, "ocupaciones_filtradas")
                        gdf_puntos_filtrados.to_file(shp_base_path_puntos + ".shp")

                        for file in os.listdir(tmpdir_export_puntos):
                            zf_puntos.write(os.path.join(tmpdir_export_puntos, file), file)
                zip_buffer_puntos.seek(0)

                st.download_button(
                    label="📍 Descargar shapefile de ocupaciones filtrado (.zip)",
                    data=zip_buffer_puntos.getvalue(),
                    file_name="ocupaciones_filtradas.zip",
                    mime="application/zip"
                )
    else:
        st.info("No hay datos de polígonos para mostrar en la tabla o descargar con los filtros actuales.")

# --- Footer global para la pantalla principal del visor ---
st.markdown(
    """
    <div class="fixed-footer">
        Realizado por Ing. Topográfico Luis Miguel Guerrero | © 2025. Contacto: luis.guerrero@urt.gov.co
    </div>
    """,
    unsafe_allow_html=True
)
