# client_portal/pages/dashboard_social.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.features import GeoJsonTooltip
from folium.plugins import MarkerCluster
from folium import plugins as fp
from branca.colormap import LinearColormap
from pathlib import Path

st.title("👥 Indices Sociaux – Carte Thématique")

# ---------- Paths ----------
BASE = Path(__file__).resolve().parent.parent     # client_portal/
DATA = BASE.parent / "shared_data" / "geojson_files"

# ---------- Load layers (with caching) ----------
@st.cache_data
def load_gdf(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    # Ensure WGS84 for Folium
    try:
        if gdf.crs is None:
            # Fall back: assume EPSG:4326 if already lon/lat; else user-specified file has CRS
            pass
        else:
            if gdf.crs.to_string().upper() in {"EPSG:26191", "PROJCRS[\"MERCHICH / NORD MAROC\"]", "EPSG:26191"}:
                gdf = gdf.to_crs(4326)
            elif gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
    except Exception:
        # keep as-is if transformation not possible
        pass
    return gdf

# Main polygons (communes) with social indices
gdf_ct = load_gdf(DATA / "ct_driouch.geojson")

# Optional overlays
roads_path   = DATA / "res_routier.geojson"   # rename if your file differs
schools_path = DATA / "educ_tot.geojson"      # rename if your file differs
gdf_roads   = load_gdf(roads_path)   if roads_path.exists()   else None
gdf_schools = load_gdf(schools_path) if schools_path.exists() else None

# ---------- Index code → label (Arabic) ----------
INDEX_LABELS = {
    "002": "النشاط لدى الافراد البالغين 15 سنة فأكثر",
    "003": "مؤشر البطالة لدى الافراد البالغين 15 سنة فأكثر",
    "004": "مؤشر انتشار الإعاقة",
    "005": "مؤشر الفقر المتعدد الأبعاد",
    "006": "الإعاقة (من حيث الحرمان)",
    "007": "وفيات الأطفال الأقل من 5 سنوات (من حيث الحرمان)",
    "008": "تمدرس الأطفال (من حيث الحرمان)",
    "009": "عدد سنوات التمدرس (من حيث الحرمان)",
    "010": "الكهرباء (من حيث الحرمان)",
    "011": "الماء الصالح للشرب (من حيث الحرمان)",
    "012": "المؤشر العام للتطهير السائل",
    "013": "نسبة الربط بشبكة التطهير العمومية",
    "014": "السكن (من حيث الحرمان)",
    "015": "نمط الطهي (من حيث الحرمان)",
}

# Filter to codes that actually exist in the file
available_codes = [c for c in INDEX_LABELS if c in gdf_ct.columns]
if not available_codes:
    st.error("Aucun indicateur (002..015) trouvé dans ct_driouch.geojson.")
    st.stop()

# ---------- UI controls ----------
left, right = st.columns([2,1])
with left:
    code = st.selectbox(
        "Sélectionnez un thème",
        options=available_codes,
        format_func=lambda c: f"{c} — {INDEX_LABELS[c]}",
        index=0
    )
with right:
    show_roads   = st.checkbox("Afficher le réseau routier", value=True, help="Piste = marron, Goudronnée = noir")
    show_schools = st.checkbox("Afficher les établissements scolaires", value=True)

# ---------- Prepare choropleth ----------
# Coerce numeric safely
vals = pd.to_numeric(gdf_ct[code], errors="coerce")
gdf_ct = gdf_ct.copy()
gdf_ct[code] = vals

def make_colormap(series: pd.Series) -> LinearColormap:
    s = series.dropna()
    if s.empty:
        return LinearColormap(["#dddddd", "#999999"], vmin=0, vmax=1, caption=INDEX_LABELS[code])
    vmin, vmax = float(s.min()), float(s.max())
    ylorrd = ['#FFFFCC', '#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026']
    if vmin == vmax:
        return LinearColormap([ylorrd[0]], vmin=vmin, vmax=vmax, caption=INDEX_LABELS[code])
    return LinearColormap(ylorrd, vmin=vmin, vmax=vmax, caption=INDEX_LABELS[code])

cmap = make_colormap(gdf_ct[code])

def style_fn(feat):
    v = feat["properties"].get(code, None)
    return {
        "fillColor": cmap(v) if pd.notnull(v) else "#cccccc",
        "color": "black",
        "weight": 0.6,
        "fillOpacity": 0.75,
    }

tooltip = GeoJsonTooltip(
    fields=[f for f in ["province_f","cercle_fr","commune_fr", code] if f in gdf_ct.columns],
    aliases=["Province", "Cercle", "Commune", INDEX_LABELS.get(code, code)],
    localize=True,
    sticky=False,
    labels=True,
    max_width=650,
    style="""
        background-color:#F0EFEF;
        border:2px solid #000;
        border-radius:3px;
        box-shadow:3px;
    """,
)

# ---------- Build map ----------
m = folium.Map(location=[34.95, -3.39], zoom_start=9, control_scale=True)
folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles © Esri",
    name="ESRI Terrain", overlay=False, control=True
).add_to(m)
fp.Fullscreen(position="topleft", title="Fullscreen", title_cancel="Exit", force_separate_button=True).add_to(m)

# Polygons choropleth
folium.GeoJson(gdf_ct, style_function=style_fn, tooltip=tooltip, name=INDEX_LABELS.get(code, code)).add_to(m)
cmap.add_to(m)

# ---------- Roads overlay (optional) ----------
if show_roads and gdf_roads is not None:
    fg_roads = folium.FeatureGroup(name="Réseau routier").add_to(m)

    def road_style(feat):
        etat = str(feat["properties"].get("etat", "")).strip().lower()
        color = "#5b3a29" if etat == "piste" else "#000000"  # brown vs black
        return {"color": color, "weight": 2.0, "opacity": 0.9}

    folium.GeoJson(gdf_roads, style_function=road_style, name="Routes").add_to(fg_roads)

    legend_roads = """
    <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;
                background: rgba(255,255,255,0.92); padding: 10px; border: 1px solid #ccc;
                border-radius: 6px; font-size: 12px;">
      <b>Routes</b><br>
      <span style="display:inline-block;width:14px;height:2px;background:#5b3a29;margin-right:6px;"></span> Piste<br>
      <span style="display:inline-block;width:14px;height:2px;background:#000000;margin-right:6px;"></span> Goudronnée
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_roads))

# ---------- Schools overlay (optional) ----------
if show_schools and gdf_schools is not None:
    fg_sch = folium.FeatureGroup(name="Établissements scolaires").add_to(m)
    cluster = MarkerCluster().add_to(fg_sch)

    # Be robust to null/empty geometries
    def valid_point(geom):
        try:
            return (geom is not None) and (not geom.is_empty)
        except Exception:
            return False

    for _, r in gdf_schools.iterrows():
        if not valid_point(r.geometry):
            continue
        popup = f"""
        <div style="font-size:13px">
          <b>Nom:</b> {r.get('Nom_Etabli','')}<br>
          <b>Nature:</b> {r.get('Nature','')}<br>
          <b>Secteur:</b> {r.get('Secteur','')}<br>
          <b>Commune:</b> {r.get('Commune','')}
        </div>
        """
        folium.Marker(
            location=[r.geometry.y, r.geometry.x],
            icon=folium.DivIcon(html='<div style="font-size:20px;">🏫</div>'),
            tooltip=r.get("Nom_Etabli", "Établissement"),
            popup=folium.Popup(popup, max_width=320),
        ).add_to(cluster)

# Controls + render
folium.LayerControl(position="topright", collapsed=False).add_to(m)
st_folium(m, width="100%", height=720)
