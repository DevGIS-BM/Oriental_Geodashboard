import streamlit as st
from auth.db_utils import verify_user
from streamlit import switch_page


# --- Configuration ---
st.set_page_config(page_title="GeoDashboard", layout="wide", initial_sidebar_state="collapsed")

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
    dashboard = st.Page("pages/dashboard.py", title="Dashboard",icon="🗺️")
    explore =st.Page("pages/explore.py", title="Explore data",icon="📊")
    search = st.Page("pages/search.py", title="Search",icon="🔍")
    settings = st.Page("pages/settings.py", title="Settings",icon="⚙️")
    nav = st.navigation({
        
        "Client Portal": [Home],
        "Main": [dashboard,explore],
        "Tools": [search,settings],

    })
    nav.run()

