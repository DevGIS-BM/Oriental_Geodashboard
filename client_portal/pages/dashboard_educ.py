import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium, folium_static
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from branca.colormap import linear, ColorMap, LinearColormap

import matplotlib.pyplot as plt
import base64
from io import BytesIO
from pathlib import Path

# --- Load data ---
# from utils.load_once import load_data_once

# load_data_once()




base_path = Path(__file__).resolve().parent.parent  # client_portal/
data_path = base_path.parent / "shared_data" / "geojson_files"


if "gdf_province" not in st.session_state:
    st.session_state["gdf_province"] = gpd.read_file(data_path / "educ_commune.geojson")

# if "gdf_educ" not in st.session_state:
#     st.session_state["gdf_province"] = gpd.read_file(data_path / "educ_commune.geojson")
    
if "gdf_ecole" not in st.session_state:
    st.session_state["gdf_ecole"] = gpd.read_file(data_path / "bv.geojson")

if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")



gdf_province = st.session_state["gdf_province"]
# gdf_educ = st.session_state["gdf_educ"]
gdf_ecole = st.session_state["gdf_ecole"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🗺️ Map of Electoral offices")



# @st.cache_resource
def create_map(_gdf_province_data):
    m = folium.Map(location=[34.95, -3.39], zoom_start=9, control_scale=True)
    
    # folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    # Terrain
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: USGS, Esri, TANA, DeLorme, NAVTEQ",
        name="ESRI Terrain",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="&copy; OpenTopoMap contributors",
        name="OpenTopoMap",
        overlay=False,
        control=True
    ).add_to(m)
    
    fp.Fullscreen(position='topleft', title='Fullscreen', title_cancel='Exit', force_separate_button=True).add_to(m)

    # --- COMBINED FEATUREGROUP for Province Layers ---
    # Create ONE FeatureGroup for both the choropleth-like layer and its tooltip layer
    fg_province_combined = folium.FeatureGroup(name="Province").add_to(m)

    # Ensure 'Ecoles_Pri' column is numeric for colormap scaling
    if not pd.api.types.is_numeric_dtype(_gdf_province_data['Ecoles_Pri']):
        _gdf_province_data['Ecoles_Pri'] = pd.to_numeric(_gdf_province_data['Ecoles_Pri'], errors='coerce')
        _gdf_province_data.dropna(subset=['Ecoles_Pri'], inplace=True) 

    min_ecole = _gdf_province_data['Ecoles_Pri'].min()
    max_ecole = _gdf_province_data['Ecoles_Pri'].max()
    
    ylorrd_colors = [
        '#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
        '#FC4E2A', '#E31A1C', '#BD0026', '#800026'
    ]
    
    if min_ecole == max_ecole:
        colormap = LinearColormap([ylorrd_colors[0]], vmin=min_ecole, vmax=max_ecole, caption="Ecoles Primaire par Commune")
    else:
        colormap = LinearColormap(ylorrd_colors, vmin=min_ecole, vmax=max_ecole, caption="Ecoles Primaire par Commune")

    def style_function_choropleth(feature):
        bv_value = feature['properties']['Ecoles_Pri']
        return {
            'fillColor': colormap(bv_value) if pd.notnull(bv_value) else '#cccccc',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }

    # Add the Choropleth-like GeoJson to the COMBINED FeatureGroup
    folium.GeoJson(
        _gdf_province_data.__geo_interface__,
        style_function=style_function_choropleth,
        highlight_function=lambda x: {'fillOpacity': 0.9},
        name="Province - Ecoles Primaire Count Visual" # This name will show up if you inspect individual layers, but the FG name controls LayerControl
    ).add_to(fg_province_combined)

    # Add the colormap legend directly to the map
    colormap.add_to(m) # Colormap legend remains independent for clarity


    # Define the Tooltip layer
    tooltip_pv = folium.GeoJsonTooltip(
        fields=["province_f", "commune_fr", "Eleves_Pri", "Eleves_Col", "Eleves_Lyc", "Ecoles_Pri", "Type_Ecole", "Nbr_Satell", "nbr_Colleg", "Nbr_Lycee", "Internats"],
        aliases=["province", "commune", "Eleves Primaires", "Eleves Colège", "Eleves Lycée", "Ecoles Primaire", "Type Ecole", "Ecoles Satellite", "nbr_Colleg", "Nbr_Lycee", "Internats"],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """,
        max_width=800,
    )
    
    # Add the Tooltip GeoJson to the *SAME* COMBINED FeatureGroup
    folium.GeoJson(
        _gdf_province_data,
        style_function=lambda x: {
            "fillOpacity": 0,
            "color": "transparent", # Make the fill transparent so only the tooltip interacts
            "weight": 0,
        },
        tooltip=tooltip_pv,
        name="Education - Details Tooltip" # Name for internal reference, not for LayerControl directly
    ).add_to(fg_province_combined) # Crucial: add to the combined FG

    return m

# st.subheader("🗺️ Thematic map")

# --- Get the cached base map ---
m = create_map(gdf_province)

# FeatureGroup for Bureau de vote (with clustering)
# fg_ecole = folium.FeatureGroup(name="Education").add_to(m)
# cluster = MarkerCluster().add_to(fg_ecole)




for idx, row in gdf_ecole.iterrows():
    popup_html = f"""
    <div style="background-color:#f9f9f9; padding:8px; border-radius:6px; border:1px solid #ccc;">
    <h4 style="margin-top:0; margin-bottom:8px;">Bureau de vote:</h4>
    <table style="width:300px; font-size:13px;font-family: arial, sans-serif;"> 
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Nom d'établissement</th><td>{row["Nom_Etabli"]}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Secteur</th><td>{row['Secteur']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Nature</th><td>{row['Nature']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Categorie</th><td>{row['Categorie']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Categorie</th><td>{row['CategorieType_de_li']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Adresse</th><td>{row['etab_adres']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Operationationel</th><td>{row['Operationa']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;Etat de Batiment</th><td>{row['Etat_Batim']}</td></tr>
    </table>
    <br>
    </div>
    """

    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.DivIcon(html=f"""
            <div style="font-size:24px;">🏫</div>
        """),
        tooltip="Bureau: "+str(row["Nom_du__bu"]),
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(cluster)

➕ Add new layer: Douars (no clustering)
fg_douars = folium.FeatureGroup(name="Douars").add_to(m)


for idx, row in gdf_douars.iterrows():
    popup_douars = f"""
    <b>Douar:</b> {row['Douar']}<br>
    <b>Milieu:</b> {row['Milieu']}<br>
    <b>Population:</b> {row['Popul']}<br>
    """    
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="darkgreen",
        fill=True,
        fill_opacity=0.8,
        tooltip=row['Douar'],
        popup=folium.Popup(popup_douars, max_width=300)
    ).add_to(fg_douars)

# Add LayerControl at the end
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# --- Render map ---
# st_data = st_folium(m, width="100%", height=700, returned_objects=[])
# st_data = st_folium(m, width="100%", height=700, returned_objects=[], key="my_dashboard_map")
st_data = st_folium(m, width="100%", height=700)