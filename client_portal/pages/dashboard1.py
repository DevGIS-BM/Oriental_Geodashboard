import streamlit as st
import geopandas as gpd
# import folium
# from streamlit_folium import st_folium
# from folium.plugins import MarkerCluster
from pathlib import Path
import pandas as pd

import altair as alt
import plotly.express as px
import plotly.graph_objects as go


if 'selected_bv' not in st.session_state:
    st.session_state.selected_bv = None
    



# Set page title
st.title("🗺️ Oriental INDH Dashboard")



alt.themes.enable("dark")

# --- Load data ---
from utils.load_once import load_data_once

load_data_once()

gdf_province = st.session_state["gdf_province"]
gdf_bv = st.session_state["gdf_bv"]
gdf_douars = st.session_state["gdf_douars"]

def make_bar(input_df, input_x, input_theme, input_color_theme):
    bar = alt.Chart(input_df).mark_bar().encode(
        x=alt.X(input_x, title=input_x.capitalize()),
        y=alt.Y(input_theme, title=input_theme.capitalize()),
        # color=alt.Color(input_color_theme)
    ).properties(
        width=600,
        height=300
    )
    return bar

# Choropleth map


def make_choropleth(input_df, input_id, input_column, input_color_theme):
    choropleth = px.choropleth_mapbox(
        input_df,
        geojson=input_df.__geo_interface__,
        locations=input_id,
        featureidkey=f"properties.{input_id}",
        color=input_column,
        color_continuous_scale=input_color_theme,
        range_color=(0, input_df[input_column].max()),
        mapbox_style="carto-positron",  # This is the tile layer like in Folium
        zoom=8,
        center={"lat": 34.95, "lon": -3.39},
        width=600,
        height=500,
        opacity=0.7,
        labels={input_column: input_column}
    )

    return choropleth

# Calculation top_bottom_two_with_theme

def top_bottom_two_with_theme(df,theme):
    top_two = df.nlargest(2, theme)[['commune_fr', theme]].reset_index(drop=True)
    bottom_two = df.nsmallest(2, theme)[['commune_fr', theme]].reset_index(drop=True)
    
    list_names = [
        top_two.loc[0, 'commune_fr'],
        top_two.loc[1, 'commune_fr'],
        bottom_two.loc[1, 'commune_fr'],
        bottom_two.loc[0, 'commune_fr']
    ]
    
    list_values = [
        top_two.loc[0, theme],
        top_two.loc[1, theme],
        bottom_two.loc[1, theme],
        bottom_two.loc[0, theme]
    ]
    
    return list_names, list_values

# Dashboard Main Panel
col = st.columns((1.5, 5, 1.5), gap='medium')
with col[0]:
    st.markdown('## Selector')
    
    theme_list = ["Menages", "Population", "Etrangers", "Marocains", "Sante", "Education", "AEP", "Elec", "Voirier", "Voirier_Q","BV"]
    
    selected_theme = st.selectbox('Select a theme', theme_list)
    df_sorted = gdf_province.sort_values(by=selected_theme, ascending=False)

    color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma', 'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    selected_color_theme = st.selectbox('Select a color theme', color_theme_list)

    st.markdown('#### Rank of communes')

    names,themes=top_bottom_two_with_theme(df_sorted,selected_theme)

   
    first_commune_name = names[0]
    first_commune_theme = themes[0]
    second_commune_name = names[1]
    second_commune_theme = themes[1]
    second=second_commune_name+': '+str(second_commune_theme)
    

    # st.metric(label=first_commune_name, value=first_commune_theme, delta= second)

    last_commune_name = names[3]
    last_commune_theme = themes[3]
    prelast_commune_name = names[2]
    prelast_commune_theme = themes[2]
    prelast=second_commune_name+': '+str(second_commune_theme)
    
    # st.metric(label=last_commune_name, value=last_commune_theme, delta= prelast)
    # Top communes
    st.markdown("### 🔼 Heigh")
    st.markdown(f"""
    * {first_commune_name}  `{first_commune_theme}`  
     * {second_commune_name}: `{second_commune_theme}`
    """)

    # Spacer
    st.markdown("---")

    # Bottom communes
    st.markdown("### 🔻 Low")
    st.markdown(f"""
    * {prelast_commune_name}  `{prelast_commune_theme}`  
     * {last_commune_name}: `{last_commune_theme}`
    """)
    
with col[1]:
    st.markdown('#### Total Population')
    
    
    # Prepare hover text with multiple lines (HTML-like tooltips)
    # gdf_bv["hover_text"] = (
    #     "N°:  " + gdf_bv["N°_Bureau"].astype(str) + "<br>" +
    #     "Nom:  " + gdf_bv["Nom_du__bu"].astype(str) + "<br>"  
    # )     
    
    # choropleth = make_choropleth(gdf_province, 'commune_fr', selected_theme, selected_color_theme)
    # # Add electoral office points to the same map
    # choropleth.add_trace(go.Scattermapbox(
    #     lat=gdf_bv.geometry.y,
    #     lon=gdf_bv.geometry.x,
    #     mode='markers',
    #     marker=go.scattermapbox.Marker(
    #         size=9,
    #         color='black',
    #         symbol='circle'
    #     ),
    #     name='Bureau',
    #     text=gdf_bv["hover_text"],  # or any column you want in the hover tooltip
    # ))    
    
    gdf_douars["hover_text"] = (
        "Douar:  " + gdf_douars["Douar"].astype(str) + "<br>" +
        "Population:  " + gdf_douars["Popul"].astype(str) + "<br>"  
    )     
    
    choropleth = make_choropleth(gdf_province, 'commune_fr', selected_theme, selected_color_theme)
    # Add electoral office points to the same map
    choropleth.add_trace(go.Scattermapbox(
        lat=gdf_douars.geometry.y,
        lon=gdf_douars.geometry.x,
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=9,
            color='black',
            symbol='circle'
        ),
        name='Douar',
        text=gdf_douars["hover_text"],  # or any column you want in the hover tooltip
    ))  
    
    st.plotly_chart(choropleth, use_container_width=True)
    
    bar= make_bar(df_sorted, 'commune_fr', selected_theme, selected_color_theme)
    st.altair_chart(bar, use_container_width=True)





with col[2]:
    st.markdown('#### Top States')

    st.dataframe(df_sorted,
                 column_order=("commune_fr", selected_theme),
                 hide_index=True,
                 width=None,
                 column_config={
                    "states": st.column_config.TextColumn(
                        "States",
                    ),
                    "population": st.column_config.ProgressColumn(
                        "Population",
                        format="%f",
                        min_value=0,
                        max_value=max(df_sorted[selected_theme]),
                     )}
                 )


