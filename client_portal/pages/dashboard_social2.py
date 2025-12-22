# client_portal/pages/dashboard_social2.py

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium import plugins as fp
from folium.features import GeoJsonTooltip
from pathlib import Path
import altair as alt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from shapely.geometry import Point

# ============================================================
# CONFIG: set your file names here
# ============================================================
REGION_GEOJSON = "region_oriental.geojson"     # <-- CHANGE to your real file
NATIONAL_GEOJSON = "maroc.geojson"             # <-- CHANGE to your real file

SCHOOLS_GEOJSON = "ecoles_driouch.geojson"     # optional layer
ROADS_GEOJSON = "routes_driouch.geojson"       # optional layer


# ============================================================
# Paths + load data
# ============================================================
base_path = Path(__file__).resolve().parent.parent  # client_portal/
geo_path = base_path.parent / "shared_data" / "geojson_files"
xls_path = base_path.parent / "shared_data"

# st.set_page_config(page_title="Indices Sociaux", layout="wide")

# ---------------------------
# Load communes (province) polygons (ct_driouch)
# ---------------------------
if "gdf_social" not in st.session_state:
    gdf_social = gpd.read_file(geo_path / "ct_driouch.geojson")
    if gdf_social.crs is not None and gdf_social.crs.to_epsg() != 4326:
        gdf_social = gdf_social.to_crs(epsg=4326)
    st.session_state["gdf_social"] = gdf_social
else:
    gdf_social = st.session_state["gdf_social"]

# ---------------------------
# Douars points
# ---------------------------
if "gdf_douars" not in st.session_state:
    gdf_douars = gpd.read_file(geo_path / "douars.geojson")
    if gdf_douars.crs is not None and gdf_douars.crs.to_epsg() != 4326:
        gdf_douars = gdf_douars.to_crs(epsg=4326)
    st.session_state["gdf_douars"] = gdf_douars
else:
    gdf_douars = st.session_state["gdf_douars"]

# ---------------------------
# Optional: schools
# ---------------------------
gdf_schools = gpd.read_file(geo_path / "educ_tot.geojson")
schools_file = geo_path / SCHOOLS_GEOJSON
if schools_file.exists():
    if "gdf_schools" not in st.session_state:
        tmp = gpd.read_file(schools_file)
        if tmp.crs is not None and tmp.crs.to_epsg() != 4326:
            tmp = tmp.to_crs(epsg=4326)
        st.session_state["gdf_schools"] = tmp
    gdf_schools = st.session_state["gdf_schools"]

# ---------------------------
# Optional: roads
# ---------------------------
gdf_roads = None
roads_file = geo_path / ROADS_GEOJSON
if roads_file.exists():
    if "gdf_roads" not in st.session_state:
        tmp = gpd.read_file(roads_file)
        if tmp.crs is not None and tmp.crs.to_epsg() != 4326:
            tmp = tmp.to_crs(epsg=4326)
        st.session_state["gdf_roads"] = tmp
    gdf_roads = st.session_state["gdf_roads"]

# ---------------------------
# Optional: region / national polygons
# ---------------------------
gdf_region = None
reg_file = geo_path / REGION_GEOJSON
if reg_file.exists():
    gdf_region = gpd.read_file(reg_file)
    if gdf_region.crs is not None and gdf_region.crs.to_epsg() != 4326:
        gdf_region = gdf_region.to_crs(epsg=4326)

gdf_national = None
nat_file = geo_path / NATIONAL_GEOJSON
if nat_file.exists():
    gdf_national = gpd.read_file(nat_file)
    if gdf_national.crs is not None and gdf_national.crs.to_epsg() != 4326:
        gdf_national = gdf_national.to_crs(epsg=4326)

# ---------------------------
# Codes → labels (FR / AR) + direction + group + alias
# ---------------------------
codes_df = pd.read_excel(xls_path / "social_codes.xlsx", dtype={"code": str})
codes_df["code"] = codes_df["code"].str.zfill(3)

# Means (national, regional, provincial)
moy_df = pd.read_excel(xls_path / "moyen_indices.xlsx", dtype={"code": str})
moy_df["code"] = moy_df["code"].str.zfill(3)
moy_df = moy_df.set_index("code")

# ============================================================
# TOP UI: language + mode buttons (styled)
# ============================================================
st.markdown(
    """
<style>
/* pill-like radio */
div[role="radiogroup"] > label {
    background: #20768A;
    padding: 8px 14px;
    border-radius: 10px;
    margin-right: 10px;
    border: 1px solid #99999955;
}
div[role="radiogroup"] > label:hover {
    border-color: #F54927;
}
</style>
""",
    unsafe_allow_html=True,
)

col_top1, col_top2,col_top3 = st.columns([2, 2, 1])




with col_top1:
    lang = st.radio(
        "🌐 Langue / اللغة",
        options=["Français", "العربية"],
        horizontal=True,
        key="lang_social",
    )

with col_top2:
    options_map = {
    "Indice Provincial": "المؤشر الإقليمي",
    "Indice Régional": "المؤشر الجهوي",
    "Indice National": "المؤشر الوطني"
}
    if lang == "Français":
        mode = st.radio(
            "Mode",
            options=["Indice Provincial", "Indice Régional", "Indice National"],
            horizontal=True,
            key="mode_social",
        )
    else:
        mode = st.radio(
            "المستوى",
            options=options_map.keys(),
            format_func=lambda x: options_map.get(x),
            horizontal=True,
            key="mode_social",
                
    )
       


st.markdown("---")

label_col = "signification_fr" if lang == "Français" else "signification_ar"

# Alias columns (optional)
alias_col = "alias_fr" if lang == "Français" else "alias_ar"
has_group = "group" in codes_df.columns
has_group_ar = "group_ar" in codes_df.columns
has_alias = alias_col in codes_df.columns

# ============================================================
# RIGHT PANEL: controls (grouping + indicator search + layers)
# ============================================================
# determine which codes exist in the polygons
all_codes = codes_df["code"].tolist()
available_codes = [c for c in all_codes if c in gdf_social.columns]
if not available_codes:
    st.error("Aucun code d'indice trouvé dans ct_driouch.geojson.")
    st.stop()

# Create a label for each code
def build_display_label(code: str) -> str:
    row = codes_df.loc[codes_df["code"] == code]
    if row.empty:
        return code
    sig = row.iloc[0].get(label_col, code)
    if has_alias and pd.notna(row.iloc[0].get(alias_col, None)):
        ali = str(row.iloc[0].get(alias_col))
        return f"{code} — {ali}"
    # fallback: shorten signification to first ~3 words
    sig_short = " ".join(str(sig).split()[:3])
    return f"{code} — {sig_short}"

# Group -> list of codes

if has_group:
    groups = codes_df["group"].fillna("Autres").unique().tolist()
else:
    groups = ["Tous"]
if lang!= "Français":
    if has_group_ar:
        groups = codes_df["group_ar"].fillna("Autres").unique().tolist()
    else:
        groups = ["Tous"]
        
with col_top3:
    if lang == "Français": 
        # st.subheader("Contrôles")
    
        if has_group:
            chosen_group = st.radio(
            "Groupes d'indices",
            options=groups, index=0,
            horizontal=True,
            key="groupe_indices",
        )
    else: 
        st.subheader("إعدادات التحكم")
        if has_group:
            chosen_group = st.radio(
            "صنف المؤشرات",
            options=groups, index=0,
            horizontal=True,
            key="groupe_indices",)
    # chosen_group = st.selectbox("Groupe", options=groups, index=0)
    group_col = "group" if lang == "Français" else ("group_ar" if has_group_ar else "group")
    group_codes = codes_df.loc[codes_df[group_col].fillna("Autres") == chosen_group, "code"].tolist()
    group_codes = [c for c in group_codes if c in available_codes]
    if not group_codes:
        group_codes = available_codes
   
# ============================================================
# MAIN LAYOUT: left chart / center map / right controls
# ============================================================
col_chart, col_map, col_ctrl = st.columns([2, 2, 1])

with col_ctrl:

    def render_code_buttons(group_codes, lang, key_prefix="ind_btn", n_cols=2):
        """
        Returns selected_code (str) using a grid of buttons.
        Persists selection in st.session_state[f"{key_prefix}_selected"].
        """
        state_key = f"{key_prefix}_selected"

        # Ensure an initial selection
        if state_key not in st.session_state or st.session_state[state_key] not in group_codes:
            st.session_state[state_key] = group_codes[0] if group_codes else None

        # Prepare labels
        items = []
        for code in group_codes:
            label = build_display_label(code)
            # keep only the "alias" part shown on button if you want:
            # e.g. "002 — Activité..." -> "Activité..."
            if "—" in label:
                short = label.split("—", 1)[1].strip()
            else:
                short = label
            items.append((code, short))

        # Grid
        cols = st.columns(n_cols)
        for i, (code, short_label) in enumerate(items):
            c = cols[i % n_cols]

            # Visual hint for selected item (simple)
            is_selected = (code == st.session_state[state_key])
            btn_label = f"✅ {short_label}" if is_selected else short_label

            if c.button(btn_label, key=f"{key_prefix}_{code}", use_container_width=True):
                st.session_state[state_key] = code

        return st.session_state[state_key]


    # indicator buttons instead of selectbox
    if lang == "Français":
        st.markdown("### Indicateurs")
    else:
        st.markdown("### المؤشرات")

    # Use 2 or 3 columns depending on how many buttons you want per row
    selected_code = render_code_buttons(
        group_codes=group_codes,
        lang=lang,
        key_prefix="social_indicator",
        n_cols=2,   # set 3 if you want more compact grid
    )


    # label full (for chart title)
    row_sel = codes_df.loc[codes_df["code"] == selected_code]
    selected_label = row_sel.iloc[0].get(label_col, selected_code) if not row_sel.empty else selected_code
col_zoom,col_coche = st.columns([2, 2])

if lang == "Français": 
    with col_coche:
        st.markdown("### Couches")
        show_douars = st.checkbox("Douars", value=False, disabled=(gdf_douars is None))
        show_schools = st.checkbox("Écoles", value=False, disabled=(gdf_schools is None))
        show_roads = st.checkbox("Routes", value=False, disabled=(gdf_roads is None))
    with col_zoom:
        st.markdown("### Options")
        if mode == "Indice Régional":
            zoom = st.slider("Zoom initial", min_value=5, max_value=14, value=7)
        elif mode == "Indice National":
            zoom = st.slider("Zoom initial", min_value=5, max_value=14, value=6)
        else:
            zoom = st.slider("Zoom initial", min_value=5, max_value=14, value=9)

else : 
    with col_zoom:
        st.markdown("### الطبقات")
        show_douars = st.checkbox("الدواوير", value=False,disabled=(gdf_douars is None))
        show_schools = st.checkbox("المدارس", value=False, disabled=(gdf_schools is None))
        show_roads = st.checkbox("الطرق", value=False, disabled=(gdf_roads is None))

        st.markdown("### إعدادات التكبير")
        if mode == "Indice Régional":
            zoom = st.slider("التكبير الأولي", min_value=5, max_value=14, value=7)
        elif mode == "Indice National":
            zoom = st.slider("التكبير الأولي", min_value=5, max_value=14, value=6)
        else:
            zoom = st.slider("التكبير الأولي", min_value=5, max_value=14, value=9)
# ============================================================
# Direction from social_codes.xlsx (up / down)
# ============================================================
direction_value = "down"
if "direction" in codes_df.columns:
    dir_series = codes_df.loc[codes_df["code"] == selected_code, "direction"]
    if not dir_series.empty and isinstance(dir_series.iloc[0], str):
        direction_value = dir_series.iloc[0].strip().lower()
        if direction_value not in ("up", "down"):
            direction_value = "down"

# ============================================================
# Metric + continuous RdYlGn colors
# ============================================================
gdf_social[selected_code] = pd.to_numeric(gdf_social[selected_code], errors="coerce")
metric_series_nonnull = gdf_social[selected_code].dropna()
if metric_series_nonnull.empty:
    st.error("Pas de données numériques pour cet indice.")
    st.stop()

vmin = float(metric_series_nonnull.min())
vmax = float(metric_series_nonnull.max())

# up => big values should be green => use RdYlGn (low red, high green)
# down => big values should be red => use reversed
base_cmap = cm.get_cmap("RdYlGn") if direction_value == "up" else cm.get_cmap("RdYlGn_r")
norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

def val_to_color(val):
    if pd.isna(val):
        return "#cccccc"
    return mcolors.to_hex(base_cmap(norm(val)))

gdf_social["__color__"] = gdf_social[selected_code].apply(val_to_color)

# ============================================================
# Means: choose which one is ACTIVE based on mode
# ============================================================
moy_nat = moy_reg = moy_pro = None

def prepare_reference_gdf(gdf_ref, value):
    """
    Return a COPY of gdf_ref with an injected numeric column [selected_code]=value.
    Avoids modifying the original GeoDataFrame.
    """
    if gdf_ref is None or getattr(gdf_ref, "empty", True) or value is None or pd.isna(value):
        return None
    gdf2 = gdf_ref.copy()
    gdf2[selected_code] = float(value)
    return gdf2


if selected_code in moy_df.index:
    row_moy = moy_df.loc[selected_code]
    moy_nat = row_moy.get("moy_nat", None)
    moy_reg = row_moy.get("moy_reg", None)
    moy_pro = row_moy.get("moy_pro", None)



if mode == "Indice Provincial":
    key, mean_val = "pro", moy_pro
elif mode == "Indice Régional":
    key, mean_val = "reg", moy_reg
else:
    key, mean_val = "nat", moy_nat

# mean_color = val_to_color(mean_val) if mean_val is not None and not pd.isna(mean_val) else "#666666"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

mean_color = (
    val_to_color(clamp(float(mean_val), vmin, vmax))
    if mean_val is not None and not pd.isna(mean_val)
    else "#666666"
)


active_mean = (key, mean_val, mean_color)




def create_map():
    center = [34.95, -3.39]
    m = folium.Map(location=center, zoom_start=zoom, control_scale=True)

    # Basemaps
    folium.TileLayer("CartoDB positron", name="CartoDB Positron").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="ESRI Terrain",
        overlay=False,
        control=True,
    ).add_to(m)

    fp.Fullscreen(
        position="topleft",
        title="Fullscreen",
        title_cancel="Exit",
        force_separate_button=True,
    ).add_to(m)

    # ------------------------------------------------------------
    # A) Background layer (UNDER communes) — only for Regional/National
    # ------------------------------------------------------------
    if (mode == "Indice National"):
        fg_bg = folium.FeatureGroup(
            name=("Maroc" if (lang == "Français") else "المغرب"  ),
            overlay=True,
            control=True,
            show=True,
        ).add_to(m)
    elif (mode == "Indice Régional"):
            fg_bg = folium.FeatureGroup(
            name=("Les régions" if (lang == "Français") else  "الجهات"),
            overlay=True,
            control=True,
            show=True,
        ).add_to(m)
    
    def add_background_reference(gdf_bg, value, layer_name, tooltip_name_fields=None):
        """
        Draw a background polygon below communes:
        - inject selected_code=value so we can color it with the SAME gradient
        - outline is subtle
        """
        if gdf_bg is None or getattr(gdf_bg, "empty", True) or value is None or pd.isna(value):
            return

        bg = gdf_bg.copy()
        bg[selected_code] = float(value)

        def bg_style_fn(feat):
            v = feat["properties"].get(selected_code)
            return {
                "fillColor": val_to_color(v),  # same gradient as communes/chart
                "color": mean_color, 
                "weight": 2,
                "fillOpacity": 0.8,
            }

        fields, aliases = [], []
        if tooltip_name_fields:
            for f, a_fr, a_ar in tooltip_name_fields:
                if f in bg.columns:
                    fields.append(f)
                    aliases.append(a_fr if lang == "Français" else a_ar)

        fields.append(selected_code)
        aliases.append(
            (f"{selected_label} (réf.)" if lang == "Français" else f"{selected_label} (مرجع)")
        )

        tooltip = GeoJsonTooltip(
            fields=fields,
            aliases=aliases,
            localize=True,
            sticky=False,
            labels=True,
            max_width=500,
            style="background-color:#F0EFEF;border:2px solid black;border-radius:3px;",
        )

        folium.GeoJson(
            bg.__geo_interface__,
            name=layer_name,
            style_function=bg_style_fn,
            tooltip=tooltip,
        ).add_to(fg_bg)

    # Add ONLY the requested background depending on mode
    if mode == "Indice Régional":
        add_background_reference(
            gdf_region,
            moy_reg,
            layer_name=("Région (référence)" if lang == "Français" else "الجهة (مرجع)"),
            tooltip_name_fields=[
                ("nom_region", "Région", "الجهة"),
                ("nom_arabe", "Nom arabe", "الاسم بالعربية"),
            ],
        )

    elif mode == "Indice National":
        add_background_reference(
            gdf_national,
            moy_nat,
            layer_name=("Maroc (référence)" if lang == "Français" else "المغرب (مرجع)"),
            tooltip_name_fields=[
                ("nom_region", "Nom", "الاسم"),
            ],
        )

    # ------------------------------------------------------------
    # B) Communes choropleth (ALWAYS ON TOP OF background)
    # ------------------------------------------------------------
    fg_communes = folium.FeatureGroup(
        name=("Communes – indices" if lang == "Français" else "الجماعات – المؤشرات"),
        overlay=True,
        control=True,
        show=True,
    ).add_to(m)

    def commune_style_fn(feat):
        val = feat["properties"].get(selected_code)
        return {
            "fillColor": val_to_color(val),  # same gradient used by chart colors
            "color": "black",
            "weight": 0.8,
            "fillOpacity": 0.75,
        }

    folium.GeoJson(
        gdf_social.__geo_interface__,
        name=f"Choropleth – {selected_label}",
        style_function=commune_style_fn,
        highlight_function=lambda x: {"weight": 2, "fillOpacity": 0.9},
    ).add_to(fg_communes)

    # ------------------------------------------------------------
    # C) Tooltip overlay (transparent) ABOVE communes choropleth
    # ------------------------------------------------------------
    tooltip_fields, tooltip_aliases = [], []
    for field, alias_fr, alias_ar in [
        ("province_f", "Province", "العمالة / الإقليم"),
        ("commune_fr", "Commune", "الجماعة"),
        ("Menages", "Ménages", "الأسر"),
        ("Population", "Population", "السكان"),
    ]:
        if field in gdf_social.columns:
            tooltip_fields.append(field)
            tooltip_aliases.append(alias_fr if lang == "Français" else alias_ar)

    tooltip_fields.append(selected_code)
    tooltip_aliases.append(selected_label)

    folium.GeoJson(
        gdf_social,
        name=("Détails communes" if lang == "Français" else "تفاصيل الجماعات"),
        style_function=lambda x: {"fillOpacity": 0, "color": "transparent", "weight": 0},
        tooltip=GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
            sticky=False,
            labels=True,
            max_width=800,
            style="background-color:#F0EFEF;border:2px solid black;border-radius:3px;",
        ),
    ).add_to(fg_communes)

    # ------------------------------------------------------------
    # D) Points / lines layers (above polygons)
    # ------------------------------------------------------------
    if show_douars:
        fg_d = folium.FeatureGroup(name=("Douars" if lang == "Français" else "الدواوير")).add_to(m)
        for _, row in gdf_douars.iterrows():
            if row.geometry is None:
                continue
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=5,
                color="darkgreen",
                fill=True,
                fill_opacity=0.85,
                tooltip=row.get("Douar", ""),
                popup=folium.Popup(
                    f"<b>Douar:</b> {row.get('Douar','')}<br>"
                    f"<b>Milieu:</b> {row.get('Milieu','')}<br>"
                    f"<b>Population:</b> {row.get('Popul','')}<br>",
                    max_width=320,
                ),
            ).add_to(fg_d)

    if show_schools and gdf_schools is not None:
        fg_s = folium.FeatureGroup(name=("Écoles" if lang == "Français" else "المدارس")).add_to(m)
        for _, row in gdf_schools.iterrows():
            if row.geometry is None:
                continue
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color="#1f77b4",
                fill=True,
                fill_opacity=0.85,
                tooltip=row.get("Nom_Etabli", row.get("Nom", "École")),
            ).add_to(fg_s)

    if show_roads and gdf_roads is not None:
        fg_r = folium.FeatureGroup(name=("Routes" if lang == "Français" else "الطرق")).add_to(m)
        folium.GeoJson(
            gdf_roads.__geo_interface__,
            style_function=lambda feat: {"color": "#444444", "weight": 2},
            name=("Routes" if lang == "Français" else "الطرق"),
        ).add_to(fg_r)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    return m


with col_map:
    m = create_map()
    map_out = st_folium(m, width="100%", height=620)

# Optional: click selection by map click location -> find commune
selected_commune_name = None
if map_out and map_out.get("last_clicked"):
    lat = map_out["last_clicked"]["lat"]
    lon = map_out["last_clicked"]["lng"]
    pt = Point(lon, lat)
    hit = gdf_social[gdf_social.geometry.contains(pt)]
    if not hit.empty:
        selected_commune_name = hit.iloc[0].get("commune_fr", None)

# ============================================================
# CHART: same colors as map + ONLY active mean line
# ============================================================
with col_chart:
    chart_df = gdf_social.copy()
    if "commune_fr" not in chart_df.columns:
        chart_df["commune_fr"] = chart_df.index.astype(str)
    if "commune_ar" not in chart_df.columns:
        chart_df["commune_ar"] = chart_df.index.astype(str)

    chart_df = chart_df[["commune_fr", "commune_ar", selected_code, "__color__"]].dropna(subset=[selected_code])
    chart_df = chart_df.sort_values(by=selected_code, ascending=False)

    if lang == "Français":
        x_field, x_title, y_title = "commune_fr", "Communes territoriales", "Pourcentage"
    else:
        x_field, x_title, y_title = "commune_ar", "الجماعات الترابية", "النسبة المئوية"

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_field}:N", title=x_title, sort=alt.SortField(field=selected_code, order="descending")),
            y=alt.Y(f"{selected_code}:Q", title=y_title),
            color=alt.Color("__color__:N", scale=None, legend=None),
            tooltip=[x_field, selected_code],
        )
        .properties(width="container", height=420)
    )

    # value labels
    labels = (
        alt.Chart(chart_df)
        .mark_text(align="center", baseline="bottom", dy=-3, color="black", fontSize=11)
        .encode(
            x=alt.X(f"{x_field}:N", sort=alt.SortField(field=selected_code, order="descending")),
            y=alt.Y(f"{selected_code}:Q"),
            text=alt.Text(f"{selected_code}:Q", format=".1f"),
        )
    )

    layers = [bars, labels]

    # Active mean only
    key, mean_val, mean_color = active_mean
    if mean_val is not None and not pd.isna(mean_val):
        if lang == "Français":
            mean_label = {
                "pro": f"Moyenne provinciale: {mean_val}",
                "reg": f"Moyenne régionale: {mean_val}",
                "nat": f"Moyenne nationale: {mean_val}",
            }[key]
        else:
            mean_label = {
                "pro": f"المتوسط الإقليمي: {mean_val}",
                "reg": f"المتوسط الجهوي: {mean_val}",
                "nat": f"المتوسط الوطني: {mean_val}",
            }[key]

        mean_df = pd.DataFrame({"y": [mean_val], "label": [mean_label]})

        mean_line = alt.Chart(mean_df).mark_rule(color=mean_color, strokeWidth=3, strokeDash=[5, 5]).encode(y="y:Q")
        mean_text = (
            alt.Chart(mean_df)
            .mark_text(align="left", dx=120, dy=-8, color=mean_color, fontWeight="bold", fontSize=12)
            .encode(y="y:Q", text="label:N")
        )
        layers.extend([mean_line, mean_text])

    # Optional: if a commune was clicked on map, emphasize it in chart (simple highlight)
    if selected_commune_name and "commune_fr" in chart_df.columns:
        sel = chart_df[chart_df["commune_fr"] == selected_commune_name]
        if not sel.empty:
            highlight = (
                alt.Chart(sel)
                .mark_bar(stroke="black", strokeWidth=2)
                .encode(
                    x=alt.X(f"{x_field}:N", sort=alt.SortField(field=selected_code, order="descending")),
                    y=alt.Y(f"{selected_code}:Q"),
                    color=alt.value("#ffffff00"),
                )
            )
            layers.append(highlight)

    final_chart = (
        alt.layer(*layers)
        .resolve_scale(color="independent")
        .properties(
            padding={"left": 20, "top": 25, "right": 20, "bottom": 10},
            title=alt.Title(text=selected_label, anchor="middle", fontSize=16, fontWeight="bold", color="grey"),
            background="white",
            height=620,
            width="container",
        )
        .configure_view(fill="white")
        .configure_axis(labelColor="black", titleColor="black")
        .configure_title(offset=60)
    )

    st.altair_chart(final_chart, use_container_width=True)

    if selected_commune_name:
        st.caption(f"Sélection carte: {selected_commune_name}")
