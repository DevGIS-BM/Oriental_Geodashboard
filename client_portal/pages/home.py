
import streamlit as st
from pathlib import Path
from streamlit import switch_page


st.markdown('<link href="styles.css" rel="stylesheet">', unsafe_allow_html=True)

# Auth check
if "auth" not in st.session_state or not st.session_state["auth"]:
    st.warning("🔒 Please log in to access this page.")
    
    switch_page("app.py")  # Send user back to login
    st.stop()


else:
    st.markdown('<link href="styles.css" rel="stylesheet">', unsafe_allow_html=True)

    # bsolute path to the image
    img_path = Path(__file__).resolve().parent.parent.parent / "images" / "indh.jpg"

    # Show the image
    # st.image(str(img_path))
    st.image(str(img_path), width=800)


    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏛️ L’INDH dans la région de l’Oriental")
        st.write("""
    Depuis son lancement en 2005 par Sa Majesté le Roi Mohammed VI, **l’Initiative Nationale pour le Développement Humain (INDH)** constitue un **levier majeur de développement territorial**.

    Dans la **région de l’Oriental**, l’INDH a permis la mise en œuvre de projets structurants et ciblés pour :

    - Réduire les inégalités sociales et spatiales.
    - Améliorer l’accès aux services de base dans les zones défavorisées.
    - Encourager l’inclusion des jeunes, des femmes et des personnes en situation de vulnérabilité.
    - Soutenir les initiatives locales à fort impact économique et social.

    Ces actions ont transformé durablement le tissu social et économique des territoires.
    
    ---
        """)

    with col2:
        st.subheader("📊 À propos de la plateforme")
        st.write("""
    Cette application digitale a été conçue pour **les décideurs publics, les responsables de programmes et les partenaires locaux** afin de fournir une **vision claire et interactive** de l’état d’avancement des projets de l’INDH dans la région.

    Elle permet de :

    - 🗺️ **Visualiser les projets** sur des cartes dynamiques.
    - 📈 **Analyser les données socio-économiques** à l’échelle provinciale et communale.
    - 🔍 **Explorer les indicateurs clés** selon des filtres thématiques, temporels et géographiques.
    - ✅ **Faciliter le suivi, l’évaluation et la planification stratégique**.
    - 🤝 Renforcer la **transparence et la redevabilité**.


    ---
        """)


    st.video("https://www.youtube.com/watch?v=V8ZBlcRFH18")  


