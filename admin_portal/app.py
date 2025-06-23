
import streamlit as st
from auth.db_utils import verify_user
from streamlit import Page, navigation
from pathlib import Path

st.set_page_config(page_title="Admin Portal", layout="wide")

if "auth" not in st.session_state:
    st.session_state["auth"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

if not st.session_state["auth"]:
    st.title("🔒 Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = verify_user(username, password)
        if role in ["admin", "editor"]:
            st.session_state["auth"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
        else:
            st.error("❌ Invalid credentials or not authorized.")
    st.stop()

# Sidebar
with st.sidebar:
    st.title(f"Welcome, {st.session_state['username']}")
    if st.button("Logout"):
        st.session_state["auth"] = False
        st.rerun()

edit = Page("pages/edit_data.py", title="Edit Data")
pages = {"📥 Edit Data": [edit]}

if st.session_state["role"] == "admin":
    manage = Page("pages/manage_users.py", title="Manage Users")
    pages["👥 Manage Users"] = [manage]

nav = navigation(pages)
nav.run()
