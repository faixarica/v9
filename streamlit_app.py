import os
import sys
import subprocess
import streamlit as st

# ================= CONFIG STREAMLIT =================
st.set_page_config(
    page_title="FaixaBet",
    layout="wide"
)

#st.write("BOOT OK - streamlit_app")

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "app")

# ================= MODELS DIR =================
MODELS_DIR = (
    os.getenv("FAIXABET_MODELS_DIR")
    or st.secrets.get("FAIXABET_MODELS_DIR")
)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    
if not MODELS_DIR:
    raise RuntimeError(
        "❌ FAIXABET_MODELS_DIR não definido no ambiente ou secrets."
    )

os.environ["FAIXABET_MODELS_DIR"] = MODELS_DIR


# 🔹 DEV: modelos já existem (Windows / Linux local)
#if MODELS_DIR and os.path.exists(MODELS_DIR):
#    st.write(f"Usando modelos locais: {MODELS_DIR}")

# 🔹 PROD: clonar modelos privados
#else:
#    MODELS_DIR = "/mount/src/models"
#    st.write(" Clonando modelos privados...")

#    repo_url = os.getenv("MODELS_REPO_URL")
#    if not repo_url:
#        st.error("❌ MODELS_REPO_URL não definido nos Secrets (somente PROD)")
#        st.stop()

#    if not os.path.exists(MODELS_DIR):
#        subprocess.check_call(
#            ["git", "clone", "--depth", "1", repo_url, MODELS_DIR]
#        )

# Exporta variável para loaders
os.environ["FAIXABET_MODELS_DIR"] = MODELS_DIR

# ================= APP PATH =================
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# ================= START APP =================
from app.main import main
main()
