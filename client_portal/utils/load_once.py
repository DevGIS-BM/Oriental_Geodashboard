import geopandas as gpd
import streamlit as st
from pathlib import Path

@st.cache_resource
def load_data_once():
    base_path = Path(__file__).resolve().parent.parent  # client_portal/
    data_path = base_path.parent / "shared_data" / "geojson_files"


    if "gdf_province" not in st.session_state:
        st.session_state["gdf_province"] = gpd.read_file(data_path / "prov.geojson")
    
    if "gdf_bv" not in st.session_state:
        st.session_state["gdf_bv"] = gpd.read_file(data_path / "bv.geojson")
    
    if "gdf_douars" not in st.session_state:
        st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")



    if "p_benteib_quartiers" not in st.session_state:
        st.session_state["p_benteib_quartiers"] = gpd.read_file(data_path / "pacha_benteib_quartiers.geojson")
    
    if "p_benteib_puits" not in st.session_state:
        st.session_state["p_benteib_puits"] = gpd.read_file(data_path / "pacha_benteib_puits.geojson")
    
    if "p_benteib_mosq" not in st.session_state:
        st.session_state["p_benteib_mosq"] = gpd.read_file(data_path / "pacha_benteib_mosq.geojson")
        
        

    if "p_midar_quartiers" not in st.session_state:
        st.session_state["p_midar_quartiers"] = gpd.read_file(data_path / "pacha_midar_quartiers.geojson")
    
    if "p_midar_puits" not in st.session_state:
        st.session_state["p_midar_puits"] = gpd.read_file(data_path / "pacha_midar_puits.geojson")
    
    if "p_midar_mosq" not in st.session_state:
        st.session_state["p_midar_mosq"] = gpd.read_file(data_path / "pacha_midar_mosq.geojson")