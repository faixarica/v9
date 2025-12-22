# streamlit_app.py

import sys
import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

st.write("BOOT OK - streamlit_app")

from app.main import main

main()
