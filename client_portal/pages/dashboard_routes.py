import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from branca.colormap import LinearColormap
from pathlib import Path

# --- Load data ---
base_path = Path(__file__).resolve().parent.parent  # client_portal/
data_path = base_path.parent / "shared_data" / "geojson_files"

if "gdf_province" not in st.session_state:
    st.session_state["gdf_province"] = gpd.read_file(data_path / "prov.geojson")

if "gdf_route" not in st.session_state:
    st.session_state["gdf_route"] = gpd.read_file(data_path / "res_routier.geojson")

if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")



gdf_douars = st.session_state["gdf_douars"]
gdf_province = st.session_state["gdf_province"]
gdf_route = st.session_state["gdf_route"]

st.title("🛣️ Carte du Réseau Routier")

# Create the folium map
def create_map(_gdf_province_data):
    m = folium.Map(location=[34.95, -3.39], zoom_start=9, control_scale=True)

    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
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

    fg_province_combined = folium.FeatureGroup(name="Province").add_to(m)

    if not pd.api.types.is_numeric_dtype(_gdf_province_data['Voirier_Q']):
        _gdf_province_data['Voirier_Q'] = pd.to_numeric(_gdf_province_data['Voirier_Q'], errors='coerce')
        _gdf_province_data.dropna(subset=['Voirier_Q'], inplace=True)

    min_Voirier_Q = _gdf_province_data['Voirier_Q'].min()
    max_Voirier_Q = _gdf_province_data['Voirier_Q'].max()

    ylorrd_colors = [
        '#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C',
        '#FC4E2A', '#E31A1C', '#BD0026', '#800026'
    ]

    if min_Voirier_Q == max_Voirier_Q:
        colormap = LinearColormap([ylorrd_colors[0]], vmin=min_Voirier_Q, vmax=max_Voirier_Q, caption="Roads quality by Commune")
    else:
        colormap = LinearColormap(ylorrd_colors, vmin=min_Voirier_Q, vmax=max_Voirier_Q, caption="Roads quality by Commune")

    def style_function_choropleth(feature):
        Voirier_Q_value = feature['properties']['Voirier_Q']
        return {
            'fillColor': colormap(Voirier_Q_value) if pd.notnull(Voirier_Q_value) else '#cccccc',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        }

    folium.GeoJson(
        _gdf_province_data.__geo_interface__,
        style_function=style_function_choropleth,
        highlight_function=lambda x: {'fillOpacity': 0.9},
        name="Province - Roads quality Visual"
    ).add_to(fg_province_combined)

    colormap.add_to(m)

    tooltip_pv = folium.GeoJsonTooltip(
        fields=["region_fr", "province_f", "cercle_fr", "commune_fr", "milieu", "Population", "superficie", "Voirier_Q"],
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

    folium.GeoJson(
        _gdf_province_data,
        style_function=lambda x: {
            "fillOpacity": 0,
            "color": "transparent",
            "weight": 0,
        },
        tooltip=tooltip_pv,
        name="Province - Details Tooltip"
    ).add_to(fg_province_combined)

    return m

# --- Create base map ---
m = create_map(gdf_province)

# --- Add Route Layer ---
fg_routes = folium.FeatureGroup(name="Réseau Routier").add_to(m)

def get_route_color(etat):
    return {
        "Goudronnée": "black",
        "Piste": "DarkGray"
    }.get(etat, "gray")

for _, row in gdf_route.iterrows():
    etat = row.get("etat", "")
    props = row.to_dict()

    popup_content = f"""
    <b>Nom:</b> {props.get('nom_fr', '')}<br>
    <b>Commune:</b> {props.get('commune', '')}<br>
    <b>Cercle:</b> {props.get('cercle_fr', '')}<br>
    <b>Milieu:</b> {props.get('milieu', '')}<br>
    <b>État:</b> {props.get('etat', '')}<br>
    """

    multiline = row.geometry
    if multiline.geom_type == "MultiLineString":
        for line in multiline.geoms:
            folium.PolyLine(
                locations=[(pt[1], pt[0]) for pt in line.coords],
                color=get_route_color(etat),
                weight=3,
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=props.get("nom_fr", "Route")
            ).add_to(fg_routes)


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


# from branca.element import Template, MacroElement

# legend_html = """
# {% macro html() %}
# <div style="
#     position: fixed;
#     bottom: 50px;
#     right: 50px;
#     width: 220px;
#     z-index: 9999;
#     font-size:14px;
#     background-color: white;
#     border:2px solid grey;
#     border-radius:5px;
#     padding: 10px;
#     box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
# ">
# <b>Légende des routes</b><br>

# <div style="margin-top:8px; display:flex; align-items:center;">
#     <div style="width: 30px; height: 4px; background-color: black; margin-right: 8px;"></div>
#     <span>Goudronnée</span>
# </div>
# <div style="margin-top:8px; display:flex; align-items:center;">
#     <div style="width: 30px; height: 4px; background-color: DarkGray; margin-right: 8px;"></div>
#     <span>Piste</span>
# </div>
# </div>
# {% endmacro %}
# """

# legend = MacroElement()
# legend._template = Template(legend_html)
# m.get_root().add_child(legend)


# --- Finalize map ---
folium.LayerControl(position='topright', collapsed=False).add_to(m)
st_data = st_folium(m, width="100%", height=700)
