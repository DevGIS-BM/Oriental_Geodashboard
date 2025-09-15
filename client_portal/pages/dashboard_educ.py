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
from collections import defaultdict

# ---------------------------
# Paths + load (once per session)
# ---------------------------
base_path = Path(__file__).resolve().parent.parent  # client_portal/
data_path = base_path.parent / "shared_data" / "geojson_files"

# Communes with education stats
if "gdf_educ_communes" not in st.session_state:
    st.session_state["gdf_educ_communes"] = gpd.read_file(data_path / "educ_commune.geojson")

# Schools points
if "gdf_ecole" not in st.session_state:
    st.session_state["gdf_ecole"] = gpd.read_file(data_path / "educ_tot.geojson")

# Douars points
if "gdf_douars" not in st.session_state:
    st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")

gdf_communes = st.session_state["gdf_educ_communes"]
gdf_ecole = st.session_state["gdf_ecole"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🏫 Éducation ")
from shapely.geometry import Point

#Clean coordinates helper
def clean_points_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    # Try to build geometry from lon/lat if geometry is missing
    if "Coord_Lon" in gdf.columns and "Coord_Lat" in gdf.columns:
        missing = gdf["geometry"].isna()
        if missing.any():
            # Only create points for rows that have both lon/lat
            have_xy = missing & gdf["Coord_Lon"].notna() & gdf["Coord_Lat"].notna()
            gdf.loc[have_xy, "geometry"] = gpd.points_from_xy(
                gdf.loc[have_xy, "Coord_Lon"],
                gdf.loc[have_xy, "Coord_Lat"],
                crs="EPSG:4326",
            )

    # Drop any rows that still have no geometry
    gdf = gdf[~gdf["geometry"].isna()].copy()

    # Keep only Point geometries
    if "geometry" in gdf:
        gdf = gdf[gdf.geometry.geom_type == "Point"].copy()

    # Ensure WGS84 for folium
    try:
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
    except Exception:
        # If CRS info is broken, force-set to WGS84 to avoid folium errors
        gdf.set_crs(epsg=4326, inplace=True)

    return gdf

gdf_ecole = clean_points_gdf(gdf_ecole)

# ---------------------------
# Column aliasing (robust to variants)
# ---------------------------

ALIASES = {
    "Nombre d'éleves en primaire": ["Eleves_Pri", "Eleves_Prim", "Eleves_Primaire", "eleves_pri", "eleves_prim"],
    "Nombre d'éleves en collège": ["Eleves_Col", "Eleves_Coll", "eleves_col"],
    "Nombre d'éleves en lycée": ["Eleves_Lyc", "Eleves_Lycee", "eleves_lyc"],
    "Nombre des écoles primaires": ["Ecoles_Pri", "Nbr_Ecoles_Pri", "ecoles_pri"],
    "Nombre des écoles satellite": ["Nbr_Satell", "Ecoles_Satellite", "nbr_satell"],
    "nombre de Collèges": ["nbr_Colleg", "Nbr_College", "nbr_colleg"],
    "Nombre de Lycée": ["Nbr_Lycee", "Nbr_Lycée", "nbr_lycee"],
    "Nombre d'internats": ["Internats", "Nbr_Internats", "internats"]
}

def resolve_column(df: pd.DataFrame, canonical: str) -> str | None:
    for candidate in ALIASES.get(canonical, [canonical]):
        if candidate in df.columns:
            return candidate
    return None

actual_col_by_canonical = {canon: resolve_column(gdf_communes, canon) for canon in ALIASES.keys()}
available_metrics = {k: v for k, v in actual_col_by_canonical.items() if v is not None}

with st.sidebar:
    st.subheader("Champs détectés (communes)")
    st.write(list(gdf_communes.columns))
    if not available_metrics:
        st.error("Aucune métrique d'éducation reconnue dans 'educ_commune.geojson'.")
    else:
        st.success(f"Métriques disponibles : {list(available_metrics.keys())}")

metric_canonical = st.selectbox(
    "Metric for choropleth",
    options=list(available_metrics.keys()) if available_metrics else [],
    index=0 if available_metrics else None,
    disabled=not bool(available_metrics),
)
metric_actual = available_metrics.get(metric_canonical)

# ---------------------------
# Choropleth colormap helper
# ---------------------------
def colormap_for_series(s: pd.Series) -> LinearColormap:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
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

    # Communes / choropleth group
    fg_communes = folium.FeatureGroup(name="Communes (éducation)").add_to(m)

    if metric_actual:
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
        st.warning("Aucune métrique sélectionnée/disponible pour la carte choroplèthe.")

    # Tooltip for communes
    tooltip_fields, tooltip_aliases = [], []
    for canon in ["Nombre d'éleves en primaire", "Nombre d'éleves en collège", "Nombre d'éleves en lycée", " Nombre des écoles primaires", "Nombre des écoles satellite", "nombre de Collèges", "Nombre de Lycée", "Nombre d'internats"]:
        actual = actual_col_by_canonical.get(canon)
        if actual and actual in _gdf_communes.columns:
            tooltip_fields.append(actual)
            tooltip_aliases.append(canon)

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
# Schools by Nature → separate layers + clusters + icons
# ---------------------------

# 1) Define categories you want to separate (normalize to UPPER)
#    You can add/rename as needed to match your data's "Nature" values.
CATEGORY_CONFIG = {
    "ECOLE": {"label": "Écoles primaires", "emoji": "🏫", "size_px": 22},
    "ECOLE COMMUNAUTAIRE": {"label": "Écoles communautaires", "emoji": "🏫", "size_px": 22},
    "ETAB PREIVE": {"label": "Établissements privés", "emoji": "🏫", "size_px": 22},
    "UNITE PRESCOLAIRE": {"label": "Unités préscolaires", "emoji": "🏫", "size_px": 22},
    "COLLEGE": {"label": "Collèges", "emoji": "📚", "size_px": 22},
    "LYCEE": {"label": "Lycées", "emoji": "🎓", "size_px": 22},
    "SATELLITE": {"label": "Écoles satellites", "emoji": "✒️", "size_px": 22},
    "INTERNAT": {"label": "Internats", "emoji": "🛏️", "size_px": 22},
    "SECTEUR SCOLAIRE": {"label": "Secteur Scolaire", "emoji": "🏠", "size_px": 22},
    
    
}


# 2) Bucket rows by normalized Nature
def norm_nature(val) -> str:
    if val is None:
        return ""
    return str(val).strip().upper()

groups = defaultdict(list)
for _, row in gdf_ecole.iterrows():
    # groups[norm_nature(row.get("Nature"))].append(row)
    groups[norm_nature(row.get("Nature"))].append(row)

# 3) Build a FeatureGroup + MarkerCluster per known category
for nature_key, cfg in CATEGORY_CONFIG.items():
    rows = groups.get(nature_key, [])
    if not rows:
        continue

    fg_label = cfg["label"]
    fg_cat = folium.FeatureGroup(name=fg_label).add_to(m)
    clus = MarkerCluster().add_to(fg_cat)

    for row in rows:
        popup_html = f"""
        <div style="background-color:#f9f9f9; padding:8px; border-radius:6px; border:1px solid #ccc;">
          <h4 style="margin-top:0; margin-bottom:8px;">{fg_label}</h4>
          <table style="width:300px; font-size:13px; font-family: arial, sans-serif;">
            <tr style="background-color:#dddddd;"><th align="left">Nom</th><td>{row.get('Nom_Etabli','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Secteur</th><td>{row.get('Secteur','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Nature</th><td>{row.get('Nature','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">État du bâtiment</th><td>{row.get('Etat_Batim','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Effectif actuel</th><td>{row.get('Effectif_A','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Taux de réuissite</th><td>{row.get('Taux reuis','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Taux d'abandon</th><td>{row.get('Taux abond','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">AEP</th><td>{row.get('AEP','')}</td></tr>
            <tr style="background-color:#dddddd;"><th align="left">Assainissment</th><td>{row.get('Assainisse','')}</td></tr>
          </table>
        </div>
        """
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            icon=folium.DivIcon(html=f'<div style="font-size:{cfg["size_px"]}px;">{cfg["emoji"]}</div>'),
            tooltip=f"{fg_label}: {row.get('Nom_Etabli','')}",
            popup=folium.Popup(popup_html, max_width=320),
        ).add_to(clus)

# 4) Unknown / other Nature values → one extra group (optional)
other_keys = [k for k in groups.keys() if k and k not in CATEGORY_CONFIG]
if other_keys:
    fg_other = folium.FeatureGroup(name="Autres établissements").add_to(m)
    clus_other = MarkerCluster().add_to(fg_other)
    for k in other_keys:
        for row in groups[k]:
            popup_html = f"""
            <div style="background-color:#f9f9f9; padding:8px; border-radius:6px; border:1px solid #ccc;">
              <h4 style="margin-top:0; margin-bottom:8px;">Autre établissement</h4>
              <table style="width:300px; font-size:13px; font-family: arial, sans-serif;">
                <tr style="background-color:#dddddd;"><th align="left">Nom</th><td>{row.get('Nom_Etabli','')}</td></tr>
                <tr style="background-color:#dddddd;"><th align="left">Nature</th><td>{row.get('Nature','')}</td></tr>
                <tr style="background-color:#dddddd;"><th align="left">Catégorie</th><td>{row.get('Categorie','')}</td></tr>
              </table>
            </div>
            """
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=folium.DivIcon(html='<div style="font-size:20px;">🏢</div>'),
                tooltip=f"{row.get('Nature','')}: {row.get('Nom_Etabli','')}",
                popup=folium.Popup(popup_html, max_width=320),
            ).add_to(clus_other)

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
        color="grey",
        fill=True,
        fill_opacity=0.8,
        tooltip=row.get('Douar',''),
        popup=folium.Popup(popup_d, max_width=300),
    ).add_to(fg_douars)

# Layer control
folium.LayerControl(position="topright", collapsed=False).add_to(m)

# Render
st_folium(m, width="100%", height=700)
