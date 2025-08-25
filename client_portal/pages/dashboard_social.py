import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from branca.colormap import LinearColormap
from pathlib import Path

# --- Load data ---
base_path = Path(__file__).resolve().parent.parent  # client_portal/
data_path = base_path.parent / "shared_data" / "geojson_files"

if "gdf_social" not in st.session_state:
    st.session_state["gdf_social"] = gpd.read_file(data_path / "sociale_communes.geojson")

if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")

gdf_social = st.session_state["gdf_social"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🗺️ Indices Sociaux")

# Liste des colonnes numériques pour choropleth
theme_options = ["Population", "Menages", "Scolarisat", "analphabé", "Masculin", "Féminin", "Taux_des_h"]
selected_theme = st.selectbox("Choisir un indice social", theme_options)

# --- Fonction carte ---
def create_map(gdf, theme):
    m = folium.Map(location=[34.95, -3.39], zoom_start=9, control_scale=True)
    
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    folium.TileLayer("OpenStreetMap", name="OSM").add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenTopoMap contributors",
        name="OpenTopoMap",
        overlay=False,
        control=True
    ).add_to(m)
    fp.Fullscreen().add_to(m)

    # Assurer type numérique
    if not pd.api.types.is_numeric_dtype(gdf[theme]):
        gdf[theme] = pd.to_numeric(gdf[theme], errors="coerce")
        gdf.dropna(subset=[theme], inplace=True)

    min_val, max_val = gdf[theme].min(), gdf[theme].max()
    colormap = LinearColormap(
        colors=['#ffffcc','#a1dab4','#41b6c4','#2c7fb8','#253494'],
        vmin=min_val, vmax=max_val,
        caption=f"{theme} par commune"
    )

    def style_function(feature):
        value = feature["properties"].get(theme, None)
        return {
            "fillColor": colormap(value) if value is not None else "#cccccc",
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7
        }

    tooltip = GeoJsonTooltip(
        fields=["province_f","commune_fr", theme],
        aliases=["Province", "Commune", theme],
        localize=True,
        sticky=False,
        labels=True,
        style="background-color:#F0EFEF; border:1px solid black; border-radius:3px; padding:3px;",
    )

    folium.GeoJson(
        gdf,
        style_function=style_function,
        tooltip=tooltip,
        name="Communes Sociales"
    ).add_to(m)

    colormap.add_to(m)

    # Ajouter Douars
    fg_douars = folium.FeatureGroup(name="Douars").add_to(m)
    for _, row in gdf_douars.iterrows():
        popup_douar = f"""
        <b>Douar:</b> {row['Douar']}<br>
        <b>Milieu:</b> {row['Milieu']}<br>
        <b>Population:</b> {row['Popul']}<br>
        """
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=5, color="darkred", fill=True, fill_opacity=0.7,
            tooltip=row["Douar"],
            popup=popup_douar
        ).add_to(fg_douars)

    folium.LayerControl().add_to(m)
    return m

# --- Render ---
m = create_map(gdf_social, selected_theme)
st_data = st_folium(m, width="100%", height=700)
