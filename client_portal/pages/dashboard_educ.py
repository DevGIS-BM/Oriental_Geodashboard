# client_portal/pages/dashboard_educ.py

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from branca.colormap import LinearColormap

import matplotlib.pyplot as plt
import base64
from io import BytesIO
from pathlib import Path

# ---------------------------
# Paths + load (once per session)
# ---------------------------
base_path = Path(__file__).resolve().parent.parent  # client_portal/
data_path = base_path.parent / "shared_data" / "geojson_files"

# Communes with education stats
if "gdf_educ_communes" not in st.session_state:
    st.session_state["gdf_educ_communes"] = gpd.read_file(data_path / "educ_commune.geojson")

# Schools points (CHANGE THIS if your schools file is named differently!)
if "gdf_ecole" not in st.session_state:
    st.session_state["gdf_ecole"] = gpd.read_file(data_path / "ecoles_driouch.geojson")

# Douars points
if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")

gdf_communes = st.session_state["gdf_educ_communes"]
gdf_ecole = st.session_state["gdf_ecole"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🏫 Éducation ")

# ---------------------------
# Column aliasing (robust to variants)
# ---------------------------
# Map canonical -> possible variants in your data
ALIASES = {
    "Eleves_Pri": ["Eleves_Pri", "Eleves_Prim", "Eleves_Primaire", "eleves_pri", "eleves_prim"],
    "Eleves_Col": ["Eleves_Col", "Eleves_Coll", "eleves_col"],
    "Eleves_Lyc": ["Eleves_Lyc", "Eleves_Lycee", "eleves_lyc"],
    "Ecoles_Pri": ["Ecoles_Pri", "Nbr_Ecoles_Pri", "ecoles_pri"],
    "Nbr_Satell": ["Nbr_Satell", "Ecoles_Satellite", "nbr_satell"],
    "nbr_Colleg": ["nbr_Colleg", "Nbr_College", "nbr_colleg"],
    "Nbr_Lycee": ["Nbr_Lycee", "Nbr_Lycée", "nbr_lycee"],
    "Internats": ["Internats", "Nbr_Internats", "internats"]
}

def resolve_column(df: pd.DataFrame, canonical: str) -> str | None:
    """Return the actual column name present in df for the canonical key."""
    for candidate in ALIASES.get(canonical, [canonical]):
        if candidate in df.columns:
            return candidate
    return None

# Build a mapping actual_col_by_canonical that exists in this file
actual_col_by_canonical = {
    canon: resolve_column(gdf_communes, canon) for canon in ALIASES.keys()
}
# Keep only those canonicals that resolved to real columns
available_metrics = {k: v for k, v in actual_col_by_canonical.items() if v is not None}

with st.sidebar:
    st.subheader("Detected columns in educ_commune")
    st.write(list(gdf_communes.columns))
    if not available_metrics:
        st.error("No known education columns were found in 'educ_commune.geojson'. Please verify field names.")
    else:
        st.success(f"Available metrics: {list(available_metrics.keys())}")

# Let user choose metric for choropleth among available ones
metric_canonical = st.selectbox(
    "Metric for choropleth",
    options=list(available_metrics.keys()),
    index=0 if available_metrics else None,
    disabled=not bool(available_metrics),
)
metric_actual = available_metrics.get(metric_canonical)

# ---------------------------
# Choropleth colormap helper
# ---------------------------
def colormap_for_series(s: pd.Series) -> LinearColormap:
    s = pd.to_numeric(s, errors="coerce")
    s = s.dropna()
    if s.empty:
        # fallback dummy colormap
        return LinearColormap(["#dddddd", "#999999"], vmin=0, vmax=1, caption="No data")
    vmin, vmax = float(s.min()), float(s.max())
    ylorrd = ['#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026']
    if vmin == vmax:
        return LinearColormap([ylorrd[0]], vmin=vmin, vmax=vmax, caption=f"{metric_canonical} par commune")
    return LinearColormap(ylorrd, vmin=vmin, vmax=vmax, caption=f"{metric_canonical} par commune")

# ---------------------------
# Map factory
# ---------------------------
def create_map(_gdf_communes: gpd.GeoDataFrame):
    m = folium.Map(location=[34.95, -3.39], zoom_start=9, control_scale=True)

    # Basemaps
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: USGS, Esri, TANA, DeLorme, NAVTEQ",
        name="ESRI Terrain", overlay=False, control=True
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="© OpenTopoMap contributors",
        name="OpenTopoMap", overlay=False, control=True
    ).add_to(m)

    fp.Fullscreen(position='topleft', title='Fullscreen', title_cancel='Exit', force_separate_button=True).add_to(m)

    # Province/commune group
    fg_communes = folium.FeatureGroup(name="Communes (éducation)").add_to(m)

    if metric_actual:
        # Coerce numeric safely
        _gdf_communes[metric_actual] = pd.to_numeric(_gdf_communes[metric_actual], errors="coerce")
        cmap = colormap_for_series(_gdf_communes[metric_actual])

        def style_fn(feat):
            val = feat["properties"].get(metric_actual)
            return {
                "fillColor": cmap(val) if pd.notnull(val) else "#cccccc",
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            }

        folium.GeoJson(
            _gdf_communes.__geo_interface__,
            style_function=style_fn,
            highlight_function=lambda x: {"fillOpacity": 0.9},
            name=f"Choropleth - {metric_canonical}",
        ).add_to(fg_communes)

        cmap.add_to(m)
    else:
        st.warning("No metric selected / available for choropleth. Showing only tooltips.")

    # Tooltip for communes
    tooltip_fields = []
    tooltip_aliases = []

    # Safely include whichever of these are available
    for canon in ["Eleves_Pri", "Eleves_Col", "Eleves_Lyc", "Ecoles_Pri", "Nbr_Satell", "nbr_Colleg", "Nbr_Lycee", "Internats"]:
        actual = actual_col_by_canonical.get(canon)
        if actual and actual in _gdf_communes.columns:
            tooltip_fields.append(actual)
            tooltip_aliases.append(canon)  # label shown

    # Always try to include commune & province names if present
    for base_field, label in [("province_f", "Province"), ("commune_fr", "Commune")]:
        if base_field in _gdf_communes.columns and base_field not in tooltip_fields:
            tooltip_fields.insert(0, base_field)
            tooltip_aliases.insert(0, label)

    tooltip = GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
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
        _gdf_communes,
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent", "weight": 0},
        tooltip=tooltip,
        name="Détails communes",
    ).add_to(fg_communes)

    return m

# Create map
m = create_map(gdf_communes)

# ---------------------------
# Schools layer (clustered)
# ---------------------------
fg_schools = folium.FeatureGroup(name="Établissements scolaires").add_to(m)
cluster = MarkerCluster().add_to(fg_schools)

for _, row in gdf_ecole.iterrows():
    # adapt keys to your schools schema; use .get to avoid KeyErrors
    popup_html = f"""
    <div style="background-color:#f9f9f9; padding:8px; border-radius:6px; border:1px solid #ccc;">
      <h4 style="margin-top:0; margin-bottom:8px;">Établissement</h4>
      <table style="width:300px; font-size:13px; font-family: arial, sans-serif;">
        <tr style="background-color:#dddddd;"><th align="left">Nom</th><td>{row.get('Nom_Etabli','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">Secteur</th><td>{row.get('Secteur','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">Nature</th><td>{row.get('Nature','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">Catégorie</th><td>{row.get('Categorie','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">Adresse</th><td>{row.get('etab_adres','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">Opérationnel</th><td>{row.get('Operationa','')}</td></tr>
        <tr style="background-color:#dddddd;"><th align="left">État du bâtiment</th><td>{row.get('Etat_Batim','')}</td></tr>
      </table>
    </div>
    """
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.DivIcon(html='<div style="font-size:24px;">🏫</div>'),
        tooltip=f"Établissement: {row.get('Nom_Etabli','')}",
        popup=folium.Popup(popup_html, max_width=320),
    ).add_to(cluster)

# ---------------------------
# Douars (no clustering)
# ---------------------------
fg_douars = folium.FeatureGroup(name="Douars").add_to(m)

for _, row in gdf_douars.iterrows():
    popup_d = f"""
    <b>Douar:</b> {row.get('Douar','')}<br>
    <b>Milieu:</b> {row.get('Milieu','')}<br>
    <b>Population:</b> {row.get('Popul','')}<br>
    """
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="darkgreen",
        fill=True,
        fill_opacity=0.8,
        tooltip=row.get('Douar',''),
        popup=folium.Popup(popup_d, max_width=300),
    ).add_to(fg_douars)

# Layer control
folium.LayerControl(position="topright", collapsed=False).add_to(m)

# Render
st_folium(m, width="100%", height=700)
