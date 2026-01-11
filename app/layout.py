# app/layout.py
# Ajusta layout global da fAIxaBet
# rev: jan/2026 — versão robusta Dev/Prod

from pathlib import Path


# ======================================================
# Helpers de path (1 fonte da verdade)
# ======================================================
BASE_DIR = Path(__file__).resolve().parent.parent   # /v9
ASSETS_DIR = BASE_DIR / "assets"


# ======================================================
# CSS global
# ======================================================
def inject_global_css():
    import streamlit as st
    st.markdown(
        """
        <style>
        html, body {
            overflow-x: hidden;
        }

        /* remove espaço superior padrão */
        section.main > div {
            padding-top: 0rem !important;
        }

        /* remove header invisível do Streamlit */
        /*
        header {
            visibility: hidden;
            height: 0px;
        }
        */

        .stSpinner {
            display: none !important;
        }

        img {
            display: block;
            max-width: 100%;
            height: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ======================================================
# Loading screen
# ======================================================
def render_loading_screen(seconds: int = 12):
    import time
    import streamlit as st
    import base64

    logo_path = ASSETS_DIR / "logoRetangular.png"

    if not logo_path.exists():
        st.error(f"Logo não encontrada: {logo_path}")
        st.session_state.page = "login"
        st.rerun()
        return

    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    logo_src = f"data:image/png;base64,{logo_b64}"

    st.markdown(
        f"""
        <style>
        .fxb-loading-wrap {{
            min-height: 82vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 18px;
            text-align: center;
            padding: 0 14px;
        }}

        .fxb-logo-build {{
            width: min(280px, 70vw);
            opacity: 0;
            filter: blur(18px) contrast(0.9);
            transform: translateY(8px) scale(0.98);
            animation: fxbLogoBuild 2.6s ease-out forwards;
        }}

        @keyframes fxbLogoBuild {{
            0%   {{ opacity: 0; filter: blur(20px); }}
            70%  {{ opacity: .9; filter: blur(4px); }}
            100% {{ opacity: 1; filter: blur(0); }}
        }}

        .fxb-progress {{
            width: min(320px, 78vw);
            height: 10px;
            background: #eaeaea;
            border-radius: 999px;
            overflow: hidden;
        }}

        .fxb-progress span {{
            display: block;
            height: 100%;
            width: 0%;
            background: repeating-linear-gradient(
                45deg,
                rgba(31,170,89,.95) 0px,
                rgba(31,170,89,.95) 10px,
                rgba(255,255,255,.35) 10px,
                rgba(255,255,255,.35) 20px
            );
            animation: fxbLoad 4s ease-in-out forwards;
        }}

        @keyframes fxbLoad {{
            to {{ width: 100%; }}
        }}
        </style>

        <div class="fxb-loading-wrap">
            <img class="fxb-logo-build" src="{logo_src}" alt="fAIxaBet" />
            <div class="fxb-progress"><span></span></div>
            <div style="font-size:14px;color:#666;">
                Preparando sua melhor experiência com loterias…
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(seconds)
    st.session_state.page = "login"
    st.rerun()


# ======================================================
# Brand header (Welcome / Login)
# ======================================================
def render_brand_header(
    variant: str = "retangular",   # "retangular" | "oval"
    align: str = "center",         # "left" | "center"
    size_px: int = 240,
    subtitle: str | None = "o futuro é prever!",
    ):
    import base64
    import streamlit as st

    logo_path = (
        ASSETS_DIR / "logoOval.png"
        if variant == "oval"
        else ASSETS_DIR / "logoRetangular.png"
    )

    if not logo_path.exists():
        st.warning(f"Logo não encontrada: {logo_path}")
        return

    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    logo_src = f"data:image/png;base64,{logo_b64}"

    justify = "flex-start" if align == "left" else "center"

    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
        <div style="
            margin-top:4px;
            font-size:20px;
            font-weight:600;
            color:#1FAA59;
            letter-spacing:0.3px;
        ">
            {subtitle}
        </div>
        """

    st.markdown(
        f"""
        <div style="
            width:100%;
            display:flex;
            flex-direction:column;
            align-items:{justify};
            justify-content:center;
            text-align:{'left' if align=='left' else 'center'};
            margin:-8px 0 12px 0;
        ">
            <img src="{logo_src}" style="width:min({size_px}px,80vw); height:auto;" />
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


