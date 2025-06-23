
import streamlit as st
from auth.db_utils import connect

st.title("📥 Edit Facilities Data")

conn = connect()
with st.form("add"):
    p = st.text_input("Province")
    c = st.text_input("Commune")
    t = st.text_input("Type")
    n = st.text_input("Name")
    lat = st.number_input("Latitude")
    lon = st.number_input("Longitude")
    if st.form_submit_button("Add"):
        conn.execute("INSERT INTO facilities (province, commune, type, name, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
                     (p, c, t, n, lat, lon))
        conn.commit()
        st.success("Added.")
conn.close()
