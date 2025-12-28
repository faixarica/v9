# app/welcome.py
import streamlit as st
import time

def tela_welcome(seconds=2):
    # tela 1: só texto (grande, verde)
    st.markdown(
        """
        <div style="height:18vh;"></div>
        <div style="text-align:center;">
            <div style="font-size:52px; font-weight:900; color:#1faa59; line-height:1.05;">
                Bem-vindo(a) à fAIxaBet®
            </div>
            <div style="margin-top:12px; font-size:20px; font-weight:600; color:#1faa59;">
                Onde o futuro é prever
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(seconds)
    st.session_state.page = "loading"
    st.rerun()
    