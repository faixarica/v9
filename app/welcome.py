# app/welcome.py
import streamlit as st
import time

def tela_welcome(seconds=2.0):
    st.markdown(
        """
        <style>
        .fxb-welcome {
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 10px;
        }
        .fxb-title {
            font-size: clamp(34px, 5vw, 46px);
            font-weight: 900;
            color: #1faa59;
            line-height: 1.1;
        }
        .fxb-sub {
            font-size: 16px;
            font-weight: 600;
            color: #2d2d2d;
            opacity: .9;
        }
        .fxb-tag {
            margin-top: 4px;
            font-size: 13px;
            color: #666;
        }
        </style>

        <div class="fxb-welcome">
            <div class="fxb-title">Bem-vindo(a) à fAIxaBet®</div>
            <div class="fxb-sub">Inteligência de dados aplicada às loterias</div>
            <div class="fxb-tag">Aqui a gente estuda o jogo. Não promete milagre.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(seconds)
    st.session_state.page = "loading"
    st.rerun()
