# streamlit_app.py (V9)

import os
import sys
import streamlit as st

# ✅ set_page_config TEM que ser o primeiro comando Streamlit do app inteiro

st.set_page_config(
    page_title="FaixaBet",
   page_icon="🍀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

# ✅ garante imports do pacote app/
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# (Opcional) log leve
st.write("BOOT OK - streamlit_app")

from app.main import main
main()
