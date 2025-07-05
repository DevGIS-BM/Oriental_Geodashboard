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
    st.session_state["gdf_province"] = gpd.read_file(data_path / "prov.geojson")

if "gdf_bv" not in st.session_state:
    st.session_state["gdf_bv"] = gpd.read_file(data_path / "bv.geojson")

if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")



gdf_province = st.session_state["gdf_province"]
gdf_bv = st.session_state["gdf_bv"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🗺️ Map of Electoral offices")

@st.cache_data
def generate_bar_chart_html(row_data):
    mapping = {"Faible": 25, "Moyenne": 50, "Bonne": 75}
    labels = ["IAM", "INWI", "ORANGE"]
    raw_values = [
        row_data.get("Couverture", "Faible"),
        row_data.get("Couvertu_1", "Faible"),
        row_data.get("Couvertu_2", "Faible")
    ]
    values = [mapping.get(v, 0) for v in raw_values]
    colors = ["blue", "purple", "orange"]

    fig, ax = plt.subplots(figsize=(3, 2))
    ax.bar(labels, values, color=colors)
    ax.set_title("Niveau de Couverture", fontsize=10)
    ax.set_ylabel("Qualité", fontsize=8)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["Faible", "Moyenne", "Bonne"])
    ax.set_ylim(0, 80)
    ax.tick_params(axis='x', labelsize=8)
    ax.tick_params(axis='y', labelsize=8)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)

    return f'<img src="data:image/png;base64,{img_base64}" width="200">'

@st.cache_resource
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

    # Ensure 'BV' column is numeric for colormap scaling
    if not pd.api.types.is_numeric_dtype(_gdf_province_data['BV']):
        _gdf_province_data['BV'] = pd.to_numeric(_gdf_province_data['BV'], errors='coerce')
        _gdf_province_data.dropna(subset=['BV'], inplace=True) 

    min_bv = _gdf_province_data['BV'].min()
    max_bv = _gdf_province_data['BV'].max()
    
    ylorrd_colors = [
        '#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
        '#FC4E2A', '#E31A1C', '#BD0026', '#800026'
    ]
    
    if min_bv == max_bv:
        colormap = LinearColormap([ylorrd_colors[0]], vmin=min_bv, vmax=max_bv, caption="BV Count by Commune")
    else:
        colormap = LinearColormap(ylorrd_colors, vmin=min_bv, vmax=max_bv, caption="BV Count by Commune")

    def style_function_choropleth(feature):
        bv_value = feature['properties']['BV']
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
        name="Province - BV Count Visual" # This name will show up if you inspect individual layers, but the FG name controls LayerControl
    ).add_to(fg_province_combined)

    # Add the colormap legend directly to the map
    colormap.add_to(m) # Colormap legend remains independent for clarity


    # Define the Tooltip layer
    tooltip_pv = folium.GeoJsonTooltip(
        fields=["region_fr", "province_f", "cercle_fr", "commune_fr", "milieu", "Population", "superficie", "BV"],
        aliases=["Région (fr)", "Province (fr)", "Cercle (fr)", "Commune (fr)", "Milieu", "Population", "Superficie", "Nombre de bureaux de vote"],
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
        name="Province - Details Tooltip" # Name for internal reference, not for LayerControl directly
    ).add_to(fg_province_combined) # Crucial: add to the combined FG

    return m

# st.subheader("🗺️ Thematic map")

# --- Get the cached base map ---
m = create_map(gdf_province)

# FeatureGroup for Bureau de vote (with clustering)
fg_bv = folium.FeatureGroup(name="Bureaux de vote").add_to(m)
cluster = MarkerCluster().add_to(fg_bv)

# --- Pre-generate all bar chart HTMLs ---
gdf_bv['bar_chart_html'] = gdf_bv.apply(generate_bar_chart_html, axis=1)

for idx, row in gdf_bv.iterrows():
    chart_html_for_popup = row['bar_chart_html']

    popup_html = f"""
    <div style="background-color:#f9f9f9; padding:8px; border-radius:6px; border:1px solid #ccc;">
    <h4 style="margin-top:0; margin-bottom:8px;">Bureau de vote:</h4>
    <table style="width:300px; font-size:13px;font-family: arial, sans-serif;">
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Bureau</th><td>{row['Nom_du__bu']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Commune</th><td>{row['Commune']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Province</th><td>{row['Province']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Machiakha</th><td>{row['Machiakha']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Type</th><td>{row['Type_de_li']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Sensibilité</th><td>{row['Sensibilit']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Accessibilité</th><td>{row['Accessibil']}</td></tr>
        <tr style="background-color: #dddddd;"><th align="left";border: 1px solid #dddddd; padding: 8px;>Électrifié</th><td>{row['Électrifi']}</td></tr>
    </table>
    <br>
    {chart_html_for_popup}
    </div>
    """

    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.DivIcon(html=f"""
            <div style="font-size:24px;">🗳️</div>
        """),
        tooltip="Bureau: "+str(row["Nom_du__bu"]),
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(cluster)

# ➕ Add new layer: Douars (no clustering)
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
st_data = st_folium(m, width="100%", height=700, returned_objects=[])