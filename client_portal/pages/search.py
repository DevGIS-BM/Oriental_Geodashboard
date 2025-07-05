import streamlit as st
import pandas as pd
import geopandas as gpd

# Load your session data
# --- Load data ---
from utils.load_once import load_data_once

load_data_once()

gdf_province = st.session_state["gdf_province"]
gdf_bv = st.session_state["gdf_bv"]
gdf_douars = st.session_state["gdf_douars"]

st.title("🔍 Recherche interactive dans les données")

# Dataset selector
dataset_choice = st.selectbox("Choisissez un jeu de données :", ["Province", "Bureaux de vote", "Douars"])

# Assign correct dataset
if dataset_choice == "Province":
    df = gdf_province.drop(columns="geometry").copy()
elif dataset_choice == "Bureaux de vote":
    df = gdf_bv.drop(columns="geometry").copy()
else:
    df = gdf_douars.drop(columns="geometry").copy()

# Show column selector
column = st.selectbox("Sélectionnez une colonne à interroger :", df.columns)

# Identify column type
if pd.api.types.is_numeric_dtype(df[column]):
    search_type = st.radio("Type de recherche :", ["Exact", "Intervalle"])
    
    if search_type == "Exact":
        value = st.number_input("Valeur exacte :", value=float(df[column].min()))
        result = df[df[column] == value]

    elif search_type == "Intervalle":
        min_val, max_val = st.slider(
            "Choisissez un intervalle :",
            float(df[column].min()),
            float(df[column].max()),
            (float(df[column].min()), float(df[column].max()))
        )
        result = df[(df[column] >= min_val) & (df[column] <= max_val)]

else:
    search_type = st.radio("Type de recherche :", ["Contient", "Commence par", "Se termine par", "Exact"])
    keyword = st.text_input("Mot ou phrase à chercher :")

    if keyword:
        if search_type == "Contient":
            result = df[df[column].astype(str).str.contains(keyword, case=False, na=False)]
        elif search_type == "Commence par":
            result = df[df[column].astype(str).str.startswith(keyword, na=False)]
        elif search_type == "Se termine par":
            result = df[df[column].astype(str).str.endswith(keyword, na=False)]
        elif search_type == "Exact":
            result = df[df[column].astype(str) == keyword]
    else:
        result = df.copy()

# Show result
st.markdown("### 📄 Résultats")
st.dataframe(result, use_container_width=True)
st.success(f"{len(result)} résultat(s) trouvé(s)")
