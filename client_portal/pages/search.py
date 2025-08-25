import streamlit as st
import pandas as pd
import geopandas as gpd

# --- Optional: load data once (safe if already loaded elsewhere) ---
try:
    from utils.load_once import load_data_once
    load_data_once()
except Exception:
    # If your app loads data in app.py, it's fine to skip here.
    pass

st.title("🔍 Recherche interactive")

# ---- Collect all GeoDataFrames present in session_state ----
gdf_candidates = {
    k: v for k, v in st.session_state.items() if isinstance(v, gpd.GeoDataFrame)
}

if not gdf_candidates:
    st.error("Aucun jeu de données trouvé dans la session. Assurez-vous d'avoir chargé les GeoDataFrames (ex: via app.py / load_once).")
    st.stop()

# Nice names for the selector
pretty_names = {k: k.replace("gdf_", "").replace("_", " ").title() for k in gdf_candidates}
name_to_key = {pretty_names[k]: k for k in gdf_candidates}
dataset_label = st.selectbox("Choisissez un jeu de données :", sorted(pretty_names.values()))
gdf = gdf_candidates[name_to_key[dataset_label]]

# Work on a Pandas DataFrame (without geometry)
df_base = gdf.drop(columns="geometry", errors="ignore").copy()
if df_base.empty:
    st.warning("Le jeu de données sélectionné ne contient pas de colonnes (hors géométrie).")
    st.stop()

st.caption(f"📦 **Dataset contient**:  {df_base.shape[0]} lignes, {df_base.shape[1]} colonnes")

# ---- Filter builder ----
with st.expander("➕ Ajouter des filtres", expanded=True):
    logic = st.radio("Combiner les filtres avec :", ["ET (AND)", "OU (OR)"], horizontal=True)
    n_filters = st.number_input("Nombre de filtres", min_value=1, max_value=8, value=1, step=1)

    filters = []
    all_columns = list(df_base.columns)

    for i in range(int(n_filters)):
        st.markdown(f"**Filtre {i+1}**")
        col_sel = st.selectbox(
            "Colonne",
            all_columns,
            key=f"col_{i}",
        )

        # Detect type
        is_num = pd.api.types.is_numeric_dtype(df_base[col_sel])

        if is_num:
            mode = st.radio(
                "Type de recherche",
                ["Exact", "Intervalle"],
                key=f"mode_{i}",
                horizontal=True
            )
            if mode == "Exact":
                # Use min as default value; keep within bounds
                cmin = float(df_base[col_sel].min()) if df_base[col_sel].notna().any() else 0.0
                cmax = float(df_base[col_sel].max()) if df_base[col_sel].notna().any() else 0.0
                val = st.number_input(
                    f"Valeur exacte ({col_sel})",
                    value=cmin,
                    min_value=min(cmin, cmax),
                    max_value=max(cmin, cmax),
                    key=f"num_exact_{i}"
                )
                filters.append(("num_exact", col_sel, val))
            else:  # Intervalle
                cmin = float(df_base[col_sel].min()) if df_base[col_sel].notna().any() else 0.0
                cmax = float(df_base[col_sel].max()) if df_base[col_sel].notna().any() else 0.0
                vmin, vmax = st.slider(
                    f"Intervalle ({col_sel})",
                    min_value=min(cmin, cmax),
                    max_value=max(cmin, cmax),
                    value=(min(cmin, cmax), max(cmin, cmax)),
                    key=f"num_range_{i}"
                )
                filters.append(("num_range", col_sel, (vmin, vmax)))
        else:
            mode = st.radio(
                "Type de recherche",
                ["Contient", "Commence par", "Se termine par", "Exact"],
                key=f"text_mode_{i}",
                horizontal=True
            )
            kw = st.text_input("Mot-clé / texte", key=f"text_value_{i}").strip()
            # Store even if empty; we'll handle later to avoid errors
            filters.append(("text", col_sel, (mode, kw)))

# ---- Apply filters ----
def apply_filters(df: pd.DataFrame, flts, use_and=True) -> pd.DataFrame:
    if not flts:
        return df

    masks = []
    for ftype, col, val in flts:
        if ftype == "num_exact":
            m = df[col] == val
        elif ftype == "num_range":
            vmin, vmax = val
            m = df[col].between(vmin, vmax, inclusive="both")
        elif ftype == "text":
            mode, kw = val
            # Convert to string to avoid NaN errors
            s = df[col].astype(str)
            if kw == "":
                # Empty keyword -> no-op mask (all True) to keep UX simple
                m = pd.Series(True, index=df.index)
            elif mode == "Contient":
                m = s.str.contains(kw, case=False, na=False)
            elif mode == "Commence par":
                m = s.str.startswith(kw, na=False)
            elif mode == "Se termine par":
                m = s.str.endswith(kw, na=False)
            else:  # Exact
                m = s == kw
        else:
            # Unknown filter type -> pass-through
            m = pd.Series(True, index=df.index)

        masks.append(m)

    if not masks:
        return df

    if use_and:
        combined = masks[0]
        for m in masks[1:]:
            combined &= m
    else:
        combined = masks[0]
        for m in masks[1:]:
            combined |= m

    return df[combined]

use_and_logic = (logic == "ET (AND)")
result = apply_filters(df_base, filters, use_and=use_and_logic)

# ---- Results ----
st.markdown("### 📄 Résultats")
st.success(f"{len(result)} résultat(s) trouvé(s)")
st.dataframe(result, use_container_width=True)

# ---- Download ----
if not result.empty:
    csv = result.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Télécharger les résultats (CSV)",
        data=csv,
        file_name=f"recherche_{name_to_key[dataset_label]}.csv",
        mime="text/csv",
    )
