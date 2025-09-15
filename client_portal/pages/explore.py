import streamlit as st
from streamlit import switch_page
import altair as alt
from pathlib import Path
import geopandas as gpd
import pandas as pd

st.markdown('<link href="styles.css" rel="stylesheet">', unsafe_allow_html=True)

# --- Auth check ---
if "auth" not in st.session_state or not st.session_state["auth"]:
    st.warning("🔒 Please log in to access this page.")
    switch_page("app.py")
    st.stop()

# --- Load once (uses your existing loader if present) ---
try:
    from utils.load_once import load_data_once
    load_data_once()
except Exception:
    # If missing, we’ll still try reading files directly below.
    pass

BASE = Path(__file__).resolve().parent.parent    # client_portal/
DATA_DIR = BASE.parent / "shared_data" / "geojson_files"

# Map human names -> (session key, filename)
CANDIDATES = {
    "Communes (Province)": ("gdf_province", "prov.geojson"),
    "Bureaux de vote (BV)": ("gdf_bv", "bv.geojson"),
    "Douars": ("gdf_douars", "douars.geojson"),
    "Réseau routier": ("gdf_routes", "res_routier.geojson"),
    "Éducation - Communes": ("gdf_educ_communes", "educ_commune.geojson"),
    "Établissements scolaires": ("gdf_ecole", "educ_tot.geojson"),  # change if different
    "Indices sociaux - Communes": ("gdf_social", "sociale_communes.geojson"),
}

# Try to ensure each dataset is available (prefer session_state, else read file if present)
available = {}
for label, (ss_key, fname) in CANDIDATES.items():
    if ss_key in st.session_state and isinstance(st.session_state[ss_key], gpd.GeoDataFrame):
        available[label] = st.session_state[ss_key]
        continue
    fpath = DATA_DIR / fname
    if fpath.exists():
        try:
            gdf = gpd.read_file(fpath)
            st.session_state[ss_key] = gdf
            available[label] = gdf
        except Exception:
            # Skip silently if unreadable
            pass

st.title("📊 Explore Data")

if not available:
    st.error("Aucune couche disponible. Vérifie le dossier `shared_data/geojson_files` ou le chargement initial.")
    st.stop()

# --- Pick dataset ---
dataset_label = st.selectbox("Choisir le jeu de données :", list(available.keys()))
gdf = available[dataset_label]

# --- Basic info ---
st.markdown(f"**Jeu de données sélectionné :** {dataset_label}")
st.write(f"**Nombre d'entités :** {len(gdf):,}")
st.write("**Colonnes :**", list(gdf.columns))

# Work on non-geometry for table/chart
df = gdf.drop(columns="geometry", errors="ignore").copy()

if df.empty or df.shape[1] == 0:
    st.info("Ce jeu de données ne contient pas d'attributs non géométriques à explorer.")
    st.stop()

# --- Type helpers ---
numeric_cols = df.select_dtypes(include="number").columns.tolist()
text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
bool_cols = df.select_dtypes(include=["bool"]).columns.tolist()
date_cols = df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()

# --- Filters (up to 3 dynamic filters) ---
with st.expander("🔎 Filtres (optionnels)"):
    filter_cols = st.multiselect("Colonnes à filtrer", df.columns.tolist(), max_selections=3)
    mask = pd.Series(True, index=df.index)
    for col in filter_cols:
        if col in numeric_cols:
            cmin, cmax = float(df[col].min()), float(df[col].max())
            vmin, vmax = st.slider(f"{col} (intervalle)", min_value=cmin, max_value=cmax, value=(cmin, vmax), step=(cmax - cmin) / 100 if cmax > cmin else 1.0)
            mask &= (df[col] >= vmin) & (df[col] <= vmax)
        elif col in text_cols:
            options = sorted(df[col].dropna().unique().tolist())
            chosen = st.multiselect(f"{col} (valeurs)", options, default=options[: min(20, len(options))])
            if chosen:
                mask &= df[col].isin(chosen)
        elif col in bool_cols:
            val = st.selectbox(f"{col}", [None, True, False], index=0, format_func=lambda x: "—" if x is None else str(x))
            if val is not None:
                mask &= (df[col] == val)
        elif col in date_cols:
            dmin, dmax = df[col].min(), df[col].max()
            start, end = st.date_input(f"{col} (intervalle)", value=(dmin.date(), dmax.date()))
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)
            mask &= (df[col] >= start) & (df[col] <= end)
        else:
            # Fallback: treat like text
            options = sorted(df[col].dropna().unique().tolist())
            chosen = st.multiselect(f"{col} (valeurs)", options, default=options[: min(20, len(options))])
            if chosen:
                mask &= df[col].isin(chosen)

df_filtered = df[mask].copy()

# --- Table ---
st.markdown("### 📋 Table")
st.dataframe(df_filtered, use_container_width=True)

# --- Chart builder ---
st.markdown("### 📈 Visualisation")
if not numeric_cols:
    st.info("Aucune colonne numérique pour la visualisation.")
else:
    # Category axis (optional)
    default_cat = text_cols[0] if text_cols else None
    category_col = st.selectbox("Axe X (catégorie) – optionnel", [None] + text_cols, index=(0 if default_cat else 0))
    value_col = st.selectbox("Valeur (numérique)", numeric_cols)

    if category_col:
        # Aggregate by category
        agg_df = df_filtered.groupby(category_col, dropna=False, as_index=False)[value_col].sum().sort_values(value_col, ascending=False)
        chart = alt.Chart(agg_df).mark_bar().encode(
            x=alt.X(f"{category_col}:N", title=category_col),
            y=alt.Y(f"{value_col}:Q", title=value_col),
            tooltip=[category_col, value_col]
        ).properties(width=800, height=420)
        st.altair_chart(chart, use_container_width=True)
    else:
        # Histogram of a numeric column
        chart = alt.Chart(df_filtered).mark_bar().encode(
            x=alt.X(f"{value_col}:Q", bin=alt.Bin(maxbins=30), title=value_col),
            y=alt.Y("count():Q", title="Effectif"),
            tooltip=[value_col, "count()"]
        ).properties(width=800, height=420)
        st.altair_chart(chart, use_container_width=True)

# --- Optional: quick preview of geometry counts by type (useful for routes vs points) ---
if "geometry" in gdf.columns:
    st.caption("Aperçu des géométries")
    try:
        st.write(gdf.geometry.geom_type.value_counts())
    except Exception:
        pass
