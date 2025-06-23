
import streamlit as st
from auth.db_utils import create_user

st.title("👥 Manage Users")

with st.form("create"):
    u = st.text_input("Username")
    e = st.text_input("Email")
    p = st.text_input("Password", type="password")
    r = st.selectbox("Role", ["admin", "editor", "client"])
    if st.form_submit_button("Create"):
        if create_user(u, e, p, r):
            st.success("User created")
        else:
            st.error("Username already exists")
