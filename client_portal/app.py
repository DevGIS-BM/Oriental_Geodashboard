import streamlit as st
from auth.db_utils import verify_user
from streamlit import switch_page
import geopandas as gpd
from pathlib import Path


# --- Configuration ---
st.set_page_config(page_title="GeoDashboard", layout="wide", initial_sidebar_state="collapsed")


# # --- Load data ---

# BASE_DIR = Path(__file__).resolve().parent.parent
# geojson_dir = BASE_DIR / "shared_data" / "geojson_files"

# province_path = geojson_dir / "prov.geojson"
# # bv_path = geojson_dir / "bv_prov.geojson"
# bv_path = geojson_dir / "bv.geojson"
# douars_path = geojson_dir / "douars.geojson"

# @st.cache_data
# def load_gdf(path):
#     return gpd.read_file(path)

# # Lostad and cache data in session state
# if "gdf_province" not in st.session_state:
#     st.session_state["gdf_province"] = load_gdf(province_path)
    
# if "gdf_bv" not in st.session_state:
#     st.session_state["gdf_bv"] = load_gdf(bv_path)


# if "gdf_douars" not in st.session_state:
#     st.session_state["gdf_douars"] = load_gdf(douars_path)



st.markdown('<link href="styles.css" rel="stylesheet">', unsafe_allow_html=True)

# --- Session State Initialization ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["just_logged_in"] = False

# --- Login Logic ---
if not st.session_state["auth"]:
    st.title("🌍 Welcome to the Regional Dashboard")

    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = verify_user(username, password)
        if role == "client":
            st.session_state["auth"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.session_state["just_logged_in"] = True
            st.success("Login successful! Redirecting...")
            st.rerun()
            switch_page("pages/home.py")
        else:
            st.error("❌ Invalid credentials or not authorized.")
    st.stop()


    
# --- Authenticated Logic ---
if st.session_state["auth"] and st.session_state["username"] and st.session_state["role"] == "client":
   
    # Sidebar for greeting and logout
    with st.sidebar:
        st.title(f"👋 Welcome,  {st.session_state['username']}")
        if st.button("Logout"):
            for key in ["auth", "username", "role", "just_logged_in"]:
                st.session_state["auth"] = False
            st.rerun()

        st.markdown("---")

        # External Links (admin portal, official sites, etc.)
        st.markdown("### 🔗 Useful Links")
        st.markdown(
            """
            <style>
                .custom-link {
                    color: #10c0301;  /* Change this to any color you want */
                    text-decoration: none;
                    font-weight: bold;
                }
                .custom-link:hover {
                    color: #faf7f7;  /* Hover color */
                }
            </style>

            - <a href="https://www.indh.ma" target="_blank" class="custom-link">🌐 INDH Website</a><br>
            - <a href="https://www.oriental.ma" target="_blank" class="custom-link">🌍 Oriental Website</a>
            """,
            unsafe_allow_html=True
        )


        st.markdown("---")
    
    Home = st.Page("pages/home.py", title="Home", icon="🖥️")
    dashboard1 = st.Page("pages/dashboard1.py", title="Général",icon="🗺️")
    dashboard_bv = st.Page("pages/dashboard_bv.py", title="Bureaux de vote",icon="🗳️")
    dashboard_route = st.Page("pages/dashboard_routes.py", title="Résau routier",icon="🚗")
    dashboard_educ = st.Page("pages/dashboard_educ.py", title="Education",icon="🏫")
    dashboard_social = st.Page("pages/dashboard_social.py", title="Indices démographiques",icon="👥")
    Benteib = st.Page("pages/benteib.py", title="Ben Teib")
    dashboard_social2 = st.Page("pages/dashboard_social2.py", title="Indices sociaux",icon="👥")
    Midar = st.Page("pages/midar.py", title="Midar")
    explore =st.Page("pages/explore.py", title="Explorer",icon="📊")
    search = st.Page("pages/search.py", title="Rechecher",icon="🔍")
    settings = st.Page("pages/settings.py", title="Paramètres",icon="⚙️")
    nav = st.navigation({
        
        "Client Portal": [Home],
        "Dashboard": [dashboard1,dashboard_bv,dashboard_route,dashboard_educ,dashboard_social],
        "Pachalik": [Benteib],
        "Indices sociaux-éconmiques": [dashboard_social2],
        "Requêtes": [explore,search],
        "Outils": [settings],

    })
    nav.run()

