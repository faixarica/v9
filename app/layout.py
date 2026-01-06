# layout.py ajusta o layout global da app.
#aff. 06/12/26 v1.0
def inject_global_css():
    import streamlit as st
    st.markdown(
        """
        <style>
        html, body { overflow-x: hidden; }
        section.main > div { padding-top: 1rem; }
        .stSpinner { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_loading_screen(seconds= 12):
    import time
    import streamlit as st
    import base64
    from pathlib import Path

    logo_path = Path("app/assets/logoRetangular.png")
    if not logo_path.exists():
        st.error(f"Logo não encontrada: {logo_path}")
        st.session_state.page = "login"
        st.rerun()

    # transforma a imagem em base64 (para usar em <img> com CSS e keyframes)
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

        /* LOGO: tamanho controlado e centralizado */
        .fxb-logo-build {{
            width: min(280px, 70vw);
            height: auto;
            opacity: 0;
            filter: blur(18px) contrast(0.9) saturate(0.9);
            transform: translateY(8px) scale(0.98);
            animation: fxbLogoBuild 2.8s ease-out forwards;
        }}

        /* “formação” da logo (keyframes) */
        @keyframes fxbLogoBuild {{
            0%   {{ opacity: 0;   filter: blur(20px) contrast(0.8); transform: translateY(10px) scale(0.97); }}
            35%  {{ opacity: .55; filter: blur(12px) contrast(0.9); }}
            70%  {{ opacity: .9;  filter: blur(5px)  contrast(1.0); transform: translateY(2px)  scale(1.0); }}
            100% {{ opacity: 1;   filter: blur(0px)  contrast(1.02); transform: translateY(0px) scale(1.0); }}
        }}

        /* BARRA */
        .fxb-progress {{
            width: min(320px, 78vw);
            height: 10px;
            background: #eaeaea;
            border-radius: 999px;
            overflow: hidden;
            box-shadow: inset 0 1px 3px rgba(0,0,0,.12);
        }}

        /* “construção craquelada” dentro da barra */
        .fxb-progress span {{
            display: block;
            height: 100%;
            width: 0%;
            border-radius: 999px;
            background:
              repeating-linear-gradient(
                45deg,
                rgba(31,170,89,.95) 0px,
                rgba(31,170,89,.95) 10px,
                rgba(255,255,255,.35) 10px,
                rgba(255,255,255,.35) 20px
              );
            animation: fxbLoad 4.3s ease-in-out forwards;
        }}

        @keyframes fxbLoad {{
            from {{ width: 0%; }}
            to   {{ width: 100%; }}
        }}

        .fxb-loading-text {{
            font-size: 14px;
            color: #666;
        }}
        </style>

        <div class="fxb-loading-wrap">
            <img class="fxb-logo-build" src="{logo_src}" alt="fAIxaBet logo" />
            <div class="fxb-progress"><span></span></div>
            <div class="fxb-loading-text">Preparando sua experiência…</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(seconds)
    st.session_state.page = "login"
    st.rerun()

