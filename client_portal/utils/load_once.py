import geopandas as gpd
import streamlit as st
from pathlib import Path

def load_data_once():
    base_path = Path(__file__).resolve().parent.parent  # client_portal/
    data_path = base_path.parent / "shared_data" / "geojson_files"


    if "gdf_province" not in st.session_state:
        st.session_state["gdf_province"] = gpd.read_file(data_path / "prov.geojson")
    
    if "gdf_bv" not in st.session_state:
        st.session_state["gdf_bv"] = gpd.read_file(data_path / "bv.geojson")
    
    if "gdf_douars" not in st.session_state:
        st.session_state["gdf_douars"] = gpd.read_file(data_path / "douars.geojson")
