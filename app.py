"""Lipoma Imaging Intelligence Platform - Streamlit entry point.   Start with:  python run.py"""
from __future__ import annotations

import streamlit as st

from lipoma_proto import config, licence
from lipoma_proto.ui import inject_css, loading_screen, start_warmup

st.set_page_config(page_title="Lipoma Imaging Platform", page_icon=":material/radiology:",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()

try:
    LIC = licence.load_licence()
except licence.LicenceError as exc:
    st.title("Lipoma Imaging Intelligence Platform")
    st.error(f"Licence required. {exc}")
    st.stop()

if not config.MODEL_FILE.exists():
    st.title("Lipoma Imaging Intelligence Platform")
    st.error("The trained model is missing. Start the platform with `python run.py` - it builds the model automatically.")
    st.stop()

loading_screen(start_warmup())

nav = st.navigation([
    st.Page("views/analysis.py", title="Image analysis", icon=":material/biotech:", default=True),
    st.Page("views/knowledge.py", title="Clinical knowledge", icon=":material/menu_book:"),
    st.Page("views/dataset.py", title="Dataset", icon=":material/database:"),
    st.Page("views/documentation.py", title="Documentation", icon=":material/description:"),
    st.Page("views/requirements.py", title="Technical requirements", icon=":material/settings:"),
])

st.sidebar.caption(f"Licensed to {LIC.name} - valid until {LIC.expires:%d %b %Y} ({LIC.days_left} days left)")
nav.run()
