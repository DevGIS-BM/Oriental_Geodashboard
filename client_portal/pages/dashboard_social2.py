# client_portal/pages/dashboard_social.py

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from branca.colormap import LinearColormap
from pathlib import Path
import altair as alt

# ---------------------------
# Paths + load data
# ---------------------------
base_path = Path(__file__).resolve().parent.parent  # client_portal/
geo_path = base_path.parent / "shared_data" / "geojson_files"
xls_path = base_path.parent / "shared_data"

# Main social indices polygons (communes)
if "gdf_social" not in st.session_state:
    gdf_social = gpd.read_file(geo_path / "ct_driouch.geojson")
    # Ensure WGS84 for Folium
    if gdf_social.crs is not None and gdf_social.crs.to_epsg() != 4326:
        gdf_social = gdf_social.to_crs(epsg=4326)
    st.session_state["gdf_social"] = gdf_social
else:
    gdf_social = st.session_state["gdf_social"]

# Douars points
if "gdf_douars" not in st.session_state:
    gdf_douars = gpd.read_file(geo_path / "douars.geojson")
    if gdf_douars.crs is not None and gdf_douars.crs.to_epsg() != 4326:
        gdf_douars = gdf_douars.to_crs(epsg=4326)
    st.session_state["gdf_douars"] = gdf_douars
else:
    gdf_douars = st.session_state["gdf_douars"]

# Codes → labels (FR / AR)
codes_df = pd.read_excel(xls_path / "social_codes.xlsx", dtype={"code": str})
codes_df["code"] = codes_df["code"].str.zfill(3)

# Means (national, regional)
moy_df = pd.read_excel(xls_path / "moyen_indices.xlsx", dtype={"code": str})
moy_df["code"] = moy_df["code"].str.zfill(3)
moy_df = moy_df.set_index("code")

st.title("👥 Indices sociaux par commune")

# ---------------------------
# Language selection
# ---------------------------
lang = st.radio(
    "🌐 Choisissez la langue / اختر اللغة",
    options=["Français", "العربية"],
    horizontal=True,
)

label_col = "signification_fr" if lang == "Français" else "signification_ar"
label_map = dict(zip(codes_df["code"], codes_df[label_col]))

# ---------------------------
# Determine which codes exist in GeoJSON
# ---------------------------
all_codes = codes_df["code"].tolist()
available_codes = [c for c in all_codes if c in gdf_social.columns]

if not available_codes:
    st.error("Aucun code d'indice trouvé dans ct_driouch.geojson.")
    st.stop()

# Build display labels
display_options = [
    f"{code} — {label_map.get(code, code)}" for code in available_codes
]

selected_display = st.selectbox(
    "Sélectionnez un indice / اختر المؤشر",
    options=display_options,
)
selected_code = selected_display.split(" — ")[0]
selected_label = label_map.get(selected_code, selected_code)

# ---------------------------
# Prepare metric & colormap
# ---------------------------
# Coerce metric to numeric
gdf_social[selected_code] = pd.to_numeric(
    gdf_social[selected_code], errors="coerce"
)

metric_series = gdf_social[selected_code].copy()
metric_series_nonnull = metric_series.dropna()

if metric_series_nonnull.empty:
    st.error("Pas de données numériques pour cet indice.")
    st.stop()

vmin = float(metric_series_nonnull.min())
vmax = float(metric_series_nonnull.max())

ylorrd = [
    "#FFFFCC", "#FFEDA0", "#FED976", "#FEB24C", "#FD8D3C",
    "#FC4E2A", "#E31A1C", "#BD0026", "#800026"
]

if vmin == vmax:
    cmap = LinearColormap([ylorrd[0]], vmin=vmin, vmax=vmax, caption=selected_label)
else:
    cmap = LinearColormap(ylorrd, vmin=vmin, vmax=vmax, caption=selected_label)

# Precompute color for each commune (for chart)
def val_to_color(val):
    if pd.isna(val):
        return "#cccccc"
    return cmap(val)

gdf_social["__color__"] = gdf_social[selected_code].apply(val_to_color)

# ---------------------------
# Map factory
# ---------------------------
def create_map(gdf_communes: gpd.GeoDataFrame):
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

    fp.Fullscreen(
        position="topleft",
        title="Fullscreen",
        title_cancel="Exit",
        force_separate_button=True
    ).add_to(m)

    # Communes feature group
    fg_communes = folium.FeatureGroup(name="Communes – indices sociaux").add_to(m)

    # Style using same colormap as chart
    def style_fn(feat):
        val = feat["properties"].get(selected_code)
        return {
            "fillColor": val_to_color(val),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        }

    folium.GeoJson(
        gdf_communes.__geo_interface__,
        style_function=style_fn,
        highlight_function=lambda x: {"fillOpacity": 0.9},
        name=f"Choropleth – {selected_label}",
    ).add_to(fg_communes)

    # Legend
    cmap.add_to(m)

    # Tooltip fields
    tooltip_fields = []
    tooltip_aliases = []

    base_fields = ["province_f", "commune_fr", "Menages", "Population"]
    for field, alias_fr, alias_ar in [
        ("province_f", "Province", "العمالة / الإقليم"),
        ("commune_fr", "Commune", "الجماعة"),
        ("Menages", "Ménages", "الأسر"),
        ("Population", "Population", "السكان"),
    ]:
        if field in gdf_communes.columns:
            tooltip_fields.append(field)
            tooltip_aliases.append(alias_fr if lang == "Français" else alias_ar)

    # Add selected metric
    tooltip_fields.append(selected_code)
    tooltip_aliases.append(selected_label)

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
        gdf_communes,
        style_function=lambda x: {
            "fillOpacity": 0,
            "color": "transparent",
            "weight": 0,
        },
        tooltip=tooltip,
        name="Détails communes",
    ).add_to(fg_communes)

    # Douars layer
    fg_douars = folium.FeatureGroup(name="Douars").add_to(m)
    for _, row in gdf_douars.iterrows():
        if row.geometry is None:
            continue
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=5,
            color="darkgreen",
            fill=True,
            fill_opacity=0.8,
            tooltip=row.get("Douar", ""),
            popup=folium.Popup(
                f"<b>Douar:</b> {row.get('Douar','')}<br>"
                f"<b>Milieu:</b> {row.get('Milieu','')}<br>"
                f"<b>Population:</b> {row.get('Popul','')}<br>",
                max_width=300,
            ),
        ).add_to(fg_douars)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    return m

# ---------------------------
# Layout: map + chart
# ---------------------------
col_map, col_chart = st.columns([2, 2])

with col_map:
    m = create_map(gdf_social)
    st_folium(m, width="100%", height=700)

# ---------------------------
# Chart with same colors + mean lines
# ---------------------------
with col_chart:
    st.markdown(f"### 📊 {selected_label}")

    # Prepare dataframe for chart
    chart_df = gdf_social.copy()
    if "commune_fr" not in chart_df.columns:
        chart_df["commune_fr"] = chart_df.index.astype(str)

    chart_df = chart_df[["commune_fr", selected_code, "__color__"]].dropna(
        subset=[selected_code]
    )

    # Averages from moyen_indices.xlsx
    moy_nat = None
    moy_reg = None
    if selected_code in moy_df.index:
        row_moy = moy_df.loc[selected_code]
        moy_nat = row_moy.get("moy_nat", None)
        moy_reg = row_moy.get("moy_reg", None)

    # Base bars
    bars = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X("commune_fr:N", title="Commune"),
        y=alt.Y(f"{selected_code}:Q", title=selected_label),
        color=alt.Color("__color__:N", scale=None, legend=None),
        tooltip=["commune_fr", selected_code],
    ).properties(width="container", height=400)

    layers = [bars]

    # National mean line
    if moy_nat is not None and not pd.isna(moy_nat):
        if lang == "Français":
            nat_df = pd.DataFrame({"y": [moy_nat], "label": ["Moyenne nationale"]})
        else:
            nat_df = pd.DataFrame({"y": [moy_nat], "label": ["المتوسط الوطني"]})
        nat_line = alt.Chart(nat_df).mark_rule(color="white", strokeWidth=3).encode(
            y="y:Q"
        )
        nat_text = alt.Chart(nat_df).mark_text(
            align="left",
            dx=5,
            dy=-5,
            color="white",
            fontWeight="bold",  # bold text
            fontSize=14
        ).encode(
            y="y:Q",
            text="label:N",
        )
        layers.extend([nat_line, nat_text])

    # Regional mean line
    if moy_reg is not None and not pd.isna(moy_reg):
        if lang == "Français":
            reg_df = pd.DataFrame({"y": [moy_reg], "label": ["Moyenne régionale"]})
        else:
            reg_df = pd.DataFrame({"y": [moy_reg], "label": ["المتوسط الجهوي"]})
        reg_line = alt.Chart(reg_df).mark_rule(color="blue", strokeWidth=3).encode(
            y="y:Q"
        )
        reg_text = alt.Chart(reg_df).mark_text(
            align="left",
            dx=5,
            dy=10,
            color="blue",
            fontWeight="bold",  # bold text
            fontSize=14
        ).encode(
            y="y:Q",
            text="label:N",
        )
        layers.extend([reg_line, reg_text])

    final_chart = alt.layer(*layers).resolve_scale(color="independent")
    st.altair_chart(final_chart, use_container_width=True)

    # Small legend reminder
    # if lang == "Français":
    #     st.caption("Les barres reprennent les mêmes couleurs que la carte. "
    #                "Ligne verte : moyenne nationale. Ligne orange : moyenne régionale.")
    # else:
    #     st.caption("الأعمدة لها نفس ألوان الخريطة. "
    #                "الخط الأخضر: المعدل الوطني. الخط البرتقالي: المعدل الجهوي.")
