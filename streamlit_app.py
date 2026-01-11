# streamlit_app.py
import os
import sys
import streamlit as st
# ================= CONFIG STREAMLIT =================
st.set_page_config(
    page_title="FaixaBet",
    layout="wide"
)

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

# Garante paths previsíveis
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# ================= MODELS DIR =================
MODELS_DIR = (
    os.getenv("FAIXABET_MODELS_DIR")
    or st.secrets.get("FAIXABET_MODELS_DIR")
)

if not MODELS_DIR:
    raise RuntimeError(
        "❌ FAIXABET_MODELS_DIR não definido no ambiente ou secrets."
    )

os.environ["FAIXABET_MODELS_DIR"] = MODELS_DIR

# ================= START APP =================
from app.main import main
main()
