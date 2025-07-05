import streamlit as st
from streamlit import switch_page
import altair as alt
from pathlib import Path
import geopandas as gpd


st.markdown('<link href="styles.css" rel="stylesheet">', unsafe_allow_html=True)

# Auth check
if "auth" not in st.session_state or not st.session_state["auth"]:
    st.warning("🔒 Please log in to access this page.")
    
    switch_page("app.py")  # Send user back to login
    st.stop()





# --- Load data ---
# --- Load data ---
from utils.load_once import load_data_once

load_data_once()

gdf_prov = st.session_state["gdf_province"]
gdf_bv = st.session_state["gdf_bv"]


# Page title
st.title("📊 Explore Data")

# Sidebar dataset selector
dataset_option = st.selectbox("Select dataset to explore:", ["Province-level", "Electoral Offices (BV)"])

if dataset_option == "Province-level":
    st.subheader("📍 Province Data")
    df = gdf_prov.drop(columns="geometry")
    
    # Filter by commune
    communes = df['commune_fr'].unique().tolist()
    selected_communes = st.multiselect("Filter by commune:", communes, default=communes)

    df_filtered = df[df['commune_fr'].isin(selected_communes)]

    # Choose field to visualize
    numeric_fields = df_filtered.select_dtypes(include='number').columns.tolist()
    selected_field = st.selectbox("Select variable to plot:", numeric_fields)

    st.markdown("### 📋 Data Table")
    st.dataframe(df_filtered[['commune_fr', selected_field]].sort_values(by=selected_field, ascending=False), use_container_width=True)

    st.markdown("### 📈 Chart")
    chart = alt.Chart(df_filtered).mark_bar().encode(
        x=alt.X('commune_fr:N', title="Commune"),
        y=alt.Y(f"{selected_field}:Q", title=selected_field),
        tooltip=['commune_fr', selected_field]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)

else:
    st.subheader("🗳️ Electoral Office Data")
    df = gdf_bv.drop(columns="geometry")
    
    # Filter by commune or type
    communes = df['Commune'].dropna().unique().tolist()
    types = df['Type_de_li'].dropna().unique().tolist()

    selected_communes = st.multiselect("Filter by commune:", communes, default=communes)
    selected_types = st.multiselect("Filter by location type:", types, default=types)

    df_filtered = df[(df['Commune'].isin(selected_communes)) & (df['Type_de_li'].isin(selected_types))]

    # Choose field to visualize
    numeric_fields = df_filtered.select_dtypes(include='number').columns.tolist()
    selected_field = st.selectbox("Select variable to plot:", numeric_fields)

    st.markdown("### 📋 Data Table")
    st.dataframe(df_filtered[['Nom_du__bu', 'Commune', selected_field]].sort_values(by=selected_field, ascending=False), use_container_width=True)

    st.markdown("### 📊 Chart")
    chart = alt.Chart(df_filtered).mark_bar().encode(
        x=alt.X('Nom_du__bu:N', title="Bureau de vote"),
        y=alt.Y(f"{selected_field}:Q", title=selected_field),
        tooltip=['Nom_du__bu', selected_field]
    ).properties(width=700, height=400)
    st.altair_chart(chart, use_container_width=True)
