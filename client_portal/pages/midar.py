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
from utils.load_once import load_data_once

load_data_once()




p_midar_quartiers = st.session_state["p_midar_quartiers"]
p_midar_mosq = st.session_state["p_midar_mosq"]
p_midar_puits = st.session_state["p_midar_puits"]

st.title("🗺️ Map of Pachalik Ben Teib")


# @st.cache_resource
def create_map(_p_midar_quartiers_data):
    m = folium.Map(location=[35.03, -3.47], zoom_start=13, control_scale=True)
    
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
    fg_pacha_combined = folium.FeatureGroup(name="Pachalik").add_to(m)

    # Ensure 'popul' column is numeric for colormap scaling
    if not pd.api.types.is_numeric_dtype(_p_midar_quartiers_data['popul']):
        _p_midar_quartiers_data['popul'] = pd.to_numeric(_p_midar_quartiers_data['popul'], errors='coerce')
        _p_midar_quartiers_data.dropna(subset=['popul'], inplace=True) 

    min_bv = _p_midar_quartiers_data['popul'].min()
    max_bv = _p_midar_quartiers_data['popul'].max()
    
    ylorrd_colors = [
        '#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
        '#FC4E2A', '#E31A1C', '#BD0026', '#800026'
    ]
    
    if min_bv == max_bv:
        colormap = LinearColormap([ylorrd_colors[0]], vmin=min_bv, vmax=max_bv, caption="population")
    else:
        colormap = LinearColormap(ylorrd_colors, vmin=min_bv, vmax=max_bv, caption="population")

    def style_function_choropleth(feature):
        bv_value = feature['properties']['popul']
        return {
            'fillColor': colormap(bv_value) if pd.notnull(bv_value) else '#cccccc',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }

    # Add the Choropleth-like GeoJson to the COMBINED FeatureGroup
    folium.GeoJson(
        _p_midar_quartiers_data.__geo_interface__,
        style_function=style_function_choropleth,
        highlight_function=lambda x: {'fillOpacity': 0.9},
        name="Pachalik - population Visual" # This name will show up if you inspect individual layers, but the FG name controls LayerControl
    ).add_to(fg_pacha_combined)

    # Add the colormap legend directly to the map
    colormap.add_to(m) # Colormap legend remains independent for clarity


    # Define the Tooltip layer
    tooltip_p = folium.GeoJsonTooltip(
        fields=["Nom_quarti", "annexe", "popul", "typ_Qrt", "covr_eau", "covr_assin", "covr_elect", "taux_godrn", "taux_eclr"],
        aliases=["Nom", "Annexe", "population", "Type", "Taux de couverture en eau", "Taux de couverture en assinissement", "Taux de couverture en éléctricité", "Taux de couverture en godron", "Taux de couverture en éclairage"],
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
        _p_midar_quartiers_data,
        style_function=lambda x: {
            "fillOpacity": 0,
            "color": "transparent", # Make the fill transparent so only the tooltip interacts
            "weight": 0,
        },
        tooltip=tooltip_p,
        name="Pachalik - Details Tooltip" # Name for internal reference, not for LayerControl directly
    ).add_to(fg_pacha_combined) # Crucial: add to the combined FG

    return m

# st.subheader("🗺️ Thematic map")

# --- Get the cached base map ---
m = create_map(p_midar_quartiers)

# ➕ Add new layer: Douars (no clustering)
fg_puits = folium.FeatureGroup(name="Puits").add_to(m)


for idx, row in p_midar_puits.iterrows():
    popup_puit = f"""
    <b>Quartier:</b> {row['Adresse']}<br>
    <b>Autorisation:</b> {row['Autorisati']}<br>
    <b>Profondeur:</b> {row['Profondeur']}<br>
    """    
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=2,
        color="blue",
        fill=True,
        fill_opacity=0.8,
        tooltip=row['Adresse'],
        popup=folium.Popup(popup_puit, max_width=300)
    ).add_to(fg_puits)


# Add LayerControl at the end
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# --- Render map ---
st_data = st_folium(m, width="100%", height=700, returned_objects=[])
