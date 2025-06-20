# --- VISOR DE POLÍGONOS DE MONITOREO SIMPLE 20/06/2025 ---
# --- Visor de polígonos con filtros por nombre y localidad ---
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

st.set_page_config(page_title="Mapanima - Geovisor de Polígonos de Monitoreo Simple", layout="wide")

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
    /* Fondo de las estadísticas - ELIMINADO EN ESTA VERSIÓN */
    /*
    div[data-testid="stMarkdownContainer"] div[data-testid="stMarkdown"] > div:last-child {
        background-color: white !important;
        color: var(--bogota-blue-dark) !important;
    }
    */
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

def onedrive_a_directo(url_onedrive):
    """
    Convierte una URL corta de OneDrive (1drv.ms) a una URL de descarga directa.
    Esta función se mantiene, pero la URL de GitHub se usa directamente.
    """
    if "1drv.ms" in url_onedrive:
        try:
            r = requests.get(url_onedrive, allow_redirects=True, timeout=10) 
            r.raise_for_status()
            return r.url.replace("redir?", "download?").replace("redir=", "download=")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error al convertir URL de OneDrive a directa: {e}. Asegúrate de que la URL sea válida y accesible.")
            return url_onedrive 
    return url_onedrive

# --- Cargar datos principales ---
# Se utiliza la URL de GitHub proporcionada directamente
url_zip_monitoreo = "https://raw.githubusercontent.com/lmiguerrero/BOT/main/Pol_Monitoreo.zip"

gdf_total = descargar_y_cargar_zip(url_zip_monitoreo)

# --- Banner superior del visor ---
with st.container():
    # Placeholder de imagen con colores de la marca Bogotá
    st.image("https://placehold.co/800x100/1C3F93/FFFFFF?text=VISOR+MONITOREO", use_container_width=True) # [Image of VISOR MONITOREO banner]

# --- VISOR PRINCIPAL ---
if gdf_total is None:
    st.warning("⚠️ No se pudieron cargar los datos geográficos principales. El visor no puede funcionar sin ellos.")
    st.stop() 

st.subheader("🗺️ Visor de Polígonos de Monitoreo")
st.markdown("Filtros, mapa y descarga de información cartográfica según filtros aplicados.")

# --- Nombres de columnas relevantes del nuevo shapefile (basado en la imagen) ---
# Se asume que estos son los nombres de las columnas en el shapefile cargado
COLUMNAS_ATRIBUTOS_TEXTO = [
    'id_poligon', 'nombre_pol', 'Tipo_PMon', 'Localidad', 
    'En_Proceso', 'Provisiona', 'Consolidac', 'Caracter_1', 'Abordaje_s',
    'Total_2023', 'Lote_202', 'Lote_203', 'En_Proce_1', 'Provisio_1', 
    'Consolid_1', 'Total_2025', 'Increment_1'
]
# 'Área_Ha_' se maneja por separado ya que requiere un formato numérico para el tooltip y tabla.

# Asegurar que las columnas existan y manejar sus tipos
for col_name in COLUMNAS_ATRIBUTOS_TEXTO:
    if col_name in gdf_total.columns:
        gdf_total[col_name] = gdf_total[col_name].astype(str).str.lower().fillna('')
    else:
        gdf_total[col_name] = '' # Crea la columna si no existe, con valores vacíos

# Los campos numéricos adicionales (Total_2023, etc.) se tratarán como texto para display
# No es necesario un bucle explícito para ellos aquí si se desea mostrar tal cual o con formato simple en el tooltip.

st.sidebar.header("🎯 Filtros")

# Filtro por 'Localidad' (multiselect)
localidad_opciones = sorted(gdf_total['Localidad'].unique())
localidad_sel = st.sidebar.multiselect(
    "Filtrar por Localidad", 
    options=localidad_opciones, 
    placeholder="Selecciona una o más localidades"
)

# Filtro por 'nombre_pol' (selectbox, una sola selección)
nombre_pol_opciones = sorted(gdf_total['nombre_pol'].unique())
nombre_pol_seleccionado = st.sidebar.selectbox(
    "🔍 Buscar por nombre de Polígono (nombre_pol)", 
    options=[""] + nombre_pol_opciones, # Añadir opción vacía para "ninguna selección"
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
fondo_seleccionado = st.sidebar.selectbox("🗺️ Fondo del mapa", list(fondos_disponibles.keys()), index=1)

st.sidebar.header("🎨 Estilos del Mapa")
mostrar_relleno = st.sidebar.checkbox("Mostrar relleno de polígonos", value=True)

# Sección de Rendimiento (eliminada la opción de simplificar geometría y el header)
# st.sidebar.header("⚙️ Rendimiento")
# usar_simplify = st.sidebar.checkbox("Simplificar geometría", value=True)
# tolerancia = st.sidebar.slider("Nivel de simplificación", 0.00001, 0.001, 0.0001, step=0.00001, format="%.5f")

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
    gdf_filtrado = gdf_total.copy()
    
    # Aplicar filtros
    if localidad_sel:
        # Convertir las localidades seleccionadas a minúsculas para coincidir con los datos
        localidad_sel_lower = [loc.lower() for loc in localidad_sel]
        gdf_filtrado = gdf_filtrado[gdf_filtrado["Localidad"].isin(localidad_sel_lower)]
    
    if nombre_pol_seleccionado and nombre_pol_seleccionado != "":
        # Convertir el nombre seleccionado a minúsculas para coincidir con los datos
        gdf_filtrado = gdf_filtrado[gdf_filtrado["nombre_pol"] == nombre_pol_seleccionado.lower()]

    # La lógica de simplificación de geometría ha sido eliminada
    # if usar_simplify and not gdf_filtrado.empty:
    #    st.info(f"Geometrías simplificadas con tolerancia de {tolerancia}")
    #    gdf_filtrado["geometry"] = gdf_filtrado["geometry"].simplify(tolerancia, preserve_topology=True)

    st.subheader("🗺️ Mapa filtrado")

    if not gdf_filtrado.empty:
        # Formatear el área para mostrar en el tooltip
        if 'Área_Ha_' in gdf_filtrado.columns:
            gdf_filtrado["area_formateada"] = gdf_filtrado["Área_Ha_"].apply(
                lambda ha: f"{int(ha):,} ha + {int(round((ha - int(ha)) * 10000)):,} m²" if ha >= 0 else "N/A"
            )
        else:
            gdf_filtrado["area_formateada"] = "N/A"
        
        # Las columnas numéricas (excepto Área_Ha_) se mostrarán como están (strings por el procesamiento inicial)
        # No se requiere un formateo específico de "_str" aquí para el tooltip ya que no se realizan cálculos con ellas.

        bounds = gdf_filtrado.total_bounds
        centro_lat = (bounds[1] + bounds[3]) / 2
        centro_lon = (bounds[0] + bounds[2]) / 2
        
        with st.spinner("Generando mapa..."):
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=8, tiles=fondos_disponibles[fondo_seleccionado])

            def style_function(feature):
                # Estilo para los polígonos de monitoreo con colores de Bogotá
                return {
                    "fillColor": "#5B8EE6", # Azul claro de Bogotá para el relleno
                    "color": "#1C3F93", # Azul medio de Bogotá para el borde
                    "weight": 1.5,
                    "fillOpacity": 0.6 if mostrar_relleno else 0
                }

            # Campos y alias para el tooltip (ajustados a los nuevos atributos del shapefile)
            # Aseguramos que 'area_formateada' esté siempre disponible para el tooltip.
            tooltip_fields = [
                "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad", "area_formateada",
                "En_Proceso", "Provisiona", "Consolidac", "Total_2023", "Lote_202",
                "Lote_203", "En_Proce_1", "Provisio_1", "Consolid_1", "Total_2025",
                "Increment_1", "Caracter_1", "Abordaje_s"
            ]
            tooltip_aliases = [
                "ID Polígono:", "Nombre Polígono:", "Tipo Monitoreo:", "Localidad:", "Área (Ha):",
                "En Proceso:", "Provisional:", "Consolidado:", "Total 2023:", "Lote 202:",
                "Lote 203:", "En Proceso 1:", "Provisional 1:", "Consolidado 1:", "Total 2025:",
                "Incremento 1:", "Carácter:", "Abordaje:"
            ]
            
            # Filtrar los campos del tooltip para incluir solo los que realmente existen en gdf_filtrado
            # Y usar los nombres originales de las columnas, excepto para el área formateada.
            final_tooltip_fields = []
            final_tooltip_aliases = []
            for i, field in enumerate(tooltip_fields):
                if field in gdf_filtrado.columns or field == 'area_formateada':
                    final_tooltip_fields.append(field)
                    final_tooltip_aliases.append(tooltip_aliases[i])


            folium.GeoJson(
                gdf_filtrado,
                name="Polígonos de Monitoreo",
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(
                    fields=final_tooltip_fields,
                    aliases=final_tooltip_aliases,
                    localize=True
                )
            ).add_to(m)

            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

            # Leyenda simple para el nuevo visor con colores de Bogotá
            leyenda_html = '''
            <div style="position: absolute; bottom: 10px; right: 10px; z-index: 9999;
                        background-color: white; padding: 10px; border: 1px solid #ccc;
                        font-size: 14px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
                <strong>Leyenda</strong><br>
                <i style="background:#5B8EE6; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid #1C3F93;"></i> Polígono de Monitoreo<br>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(leyenda_html))

            st_folium(m, width=1200, height=600)
    else:
        st.warning("⚠️ No se encontraron polígonos que coincidan con los filtros aplicados. Por favor, ajusta tus selecciones.")

    st.subheader("📋 Resultados filtrados")
    if not gdf_filtrado.empty:
        # Columnas a mostrar en el dataframe (ajustadas a los nuevos atributos)
        cols_to_display_main_viewer = [
            "id_poligon", "nombre_pol", "Tipo_PMon", "Localidad", "Área_Ha_",
            "En_Proceso", "Provisiona", "Consolidac", "Total_2023", "Lote_202",
            "Lote_203", "En_Proce_1", "Provisio_1", "Consolid_1", "Total_2025",
            "Increment_1", "Caracter_1", "Abordaje_s"
        ]
        # Asegurarse de que solo se muestren las columnas que existen en el GeoDataFrame
        cols_to_display_main_viewer = [col for col in cols_to_display_main_viewer if col in gdf_filtrado.columns]

        # Crear una copia para la visualización y formatear los números si es necesario
        gdf_filtrado_display = gdf_filtrado[cols_to_display_main_viewer].copy()
        # No se requiere formateo de números adicionales ya que las columnas originales
        # ya se procesaron a string al cargar, excepto Área_Ha_ que se formateará para display.
        if 'Área_Ha_' in gdf_filtrado_display.columns:
            gdf_filtrado_display['Área_Ha_'] = gdf_filtrado_display['Área_Ha_'].apply(
                lambda x: f"{int(x):,} ha + {int(round((x - int(x)) * 10000)):,} m²" if pd.notna(x) and x >= 0 else "N/A"
            )

        st.dataframe(gdf_filtrado_display)

        # Estadísticas resumidas - ELIMINADAS EN ESTA VERSIÓN

        with st.expander("📥 Opciones de descarga"):
            # Para descargar el shapefile filtrado
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                with tempfile.TemporaryDirectory() as tmpdir_export:
                    shp_base_path = os.path.join(tmpdir_export, "poligonos_monitoreo_filtrados")
                    gdf_filtrado_for_save = gdf_filtrado.copy()
                    if gdf_filtrado_for_save.crs is None:
                        gdf_filtrado_for_save.set_crs(epsg=4326, inplace=True)
                    gdf_filtrado_for_save.to_file(shp_base_path + ".shp")

                    for file in os.listdir(tmpdir_export):
                        zf.write(os.path.join(tmpdir_export, file), file)
            zip_buffer.seek(0) # Rebovinar el buffer al inicio

            st.download_button(
                label="📅 Descargar shapefile filtrado (.zip)",
                data=zip_buffer.getvalue(),
                file_name="poligonos_monitoreo_filtrados.zip",
                mime="application/zip"
            )

            html_bytes = m.get_root().render().encode("utf-8")
            st.download_button(
                label="🌐 Descargar mapa (HTML)",
                data=html_bytes,
                file_name="mapa_monitoreo_filtrado.html",
                mime="text/html"
            )

            # Descargar tabla como CSV - ELIMINADA EN ESTA VERSIÓN
            # csv_data = gdf_filtrado_display.to_csv(index=False).encode("utf-8")
            # st.download_button(
            #     label="📄 Descargar tabla como CSV",
            #     data=csv_data,
            #     file_name="resultados_monitoreo_filtrados.csv",
            #     mime="text/csv"
            # )
    else:
        st.info("No hay datos para mostrar en la tabla o descargar con los filtros actuales.")

# --- Footer global para la pantalla principal del visor ---
st.markdown(
    """
    <div class="fixed-footer">
        Realizado por Ing. Topográfico Luis Miguel Guerrero | © 2025. Contacto: luis.guerrero@urt.gov.co
    </div>
    """,
    unsafe_allow_html=True
)
