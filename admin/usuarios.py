# usuario.py - administração de usuários (visão ADM)

import os
import streamlit as st
from sqlalchemy import text
from db import Session
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging
from .email_notificar_user import enviar_email_usuario
from .email_estatisticas_user import enviar_email_estatisticas_usuario


logger = logging.getLogger(__name__)

# =========================================================
# HELPERS
# =========================================================

def _format_date(value):
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
    except Exception:
        return str(value)


# =========================================================
# MAIN
# =========================================================
def listar_usuarios():
    st.markdown("## 👥 Administração de Usuários")

    # ===============================
    # FILTROS
    # ===============================
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        filtro_nome = st.text_input(
            "🔍 Filtrar por nome do usuário",
            placeholder="Ex: joão, maria, dudis"
        ).strip().lower()

    with col_f2:
        filtro_email = st.text_input(
            "🔍 Filtrar por e-mail",
            placeholder="Ex: gmail.com, @hotmail"
        ).strip().lower()

    try:
        with Session() as db:
            rows = db.execute(text("""
                SELECT
                    u.id,
                    u.usuario,
                    u.email,
                    u.tipo,
                    u.dt_cadastro,
                    COALESCE(p.nome, 'Free') AS plano,
                    (
                        SELECT COUNT(*) FROM palpites pl
                        WHERE pl.id_usuario = u.id
                    ) +
                    (
                        SELECT COUNT(*) FROM palpites_m pm
                        WHERE pm.id_usuario = u.id
                    ) AS total_palpites
                FROM usuarios u
                LEFT JOIN planos p ON p.id = u.id_plano
                ORDER BY u.dt_cadastro DESC
            """)).fetchall()

        # ===============================
        # APLICAR FILTROS
        # ===============================
        if filtro_nome:
            rows = [r for r in rows if filtro_nome in (r.usuario or "").lower()]

        if filtro_email:
            rows = [r for r in rows if filtro_email in (r.email or "").lower()]

        if not rows:
            st.warning("🔎 Nenhum usuário encontrado com os filtros aplicados.")
            return

        # ===============================
        # RESUMO POR PLANO
        # ===============================
        total = len(rows)
        total_free = sum(1 for r in rows if r.plano.lower().startswith("free"))
        total_silver = sum(1 for r in rows if r.plano.lower().startswith("silver"))
        total_gold = sum(1 for r in rows if r.plano.lower().startswith("gold"))
        total_platinum = sum(1 for r in rows if r.plano.lower().startswith("platinum"))

        st.markdown(
            f"""
            <div style='display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px;'>
                <div class='card'>Free<br><b>{total_free}</b></div>
                <div class='card'>Silver<br><b>{total_silver}</b></div>
                <div class='card'>Gold<br><b>{total_gold}</b></div>
                <div class='card'>Platinum<br><b>{total_platinum}</b></div>
                <div class='card'>Total<br><b>{total}</b></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ===============================
        # LISTAGEM EM 2 COLUNAS
        # ===============================
        for i in range(0, len(rows), 2):
            cols = st.columns(2)

            for j in range(2):
                if i + j >= len(rows):
                    continue

                r = rows[i + j]
                card_key = f"u{r.id}_i{i}_j{j}"

                with cols[j]:
                    st.markdown(f"""
                        <div style="background:#fff; padding:14px; border-radius:12px;
                                    border:1px solid #ddd; margin-bottom:12px;
                                    box-shadow:0 2px 4px rgba(0,0,0,0.06);">
                        <b>👤 {r.usuario}</b><br>
                        <span style="color:#555;">📧 {r.email or '-'}</span><br><br>
                        Tipo: <b>{r.tipo}</b><br>
                        Plano: <b>{r.plano}</b><br>
                        Cadastro: {_format_date(r.dt_cadastro)}<br>
                        Palpites gerados: <b>{r.total_palpites}</b><br>
                        Eficiência: <b>—</b>
                        </div>
                    """, unsafe_allow_html=True)

                    col_a, col_b, col_c = st.columns([2, 2, 1])

                    with col_a:
                        mes = st.selectbox(
                            "Mês",
                            list(range(1, 13)),
                            format_func=lambda x: f"{x:02d}",
                            key=f"mes_{card_key}"
                        )

                    with col_b:
                        ano = st.selectbox(
                            "Ano",
                            list(range(datetime.now().year, datetime.now().year - 5, -1)),
                            key=f"ano_{card_key}"
                        )

                    with col_c:
                        st.markdown("""
                            <style>
                            div.stButton > button {
                                background-color: #28a745;
                                color: white;
                                border-radius: 8px;
                                font-weight: 600;
                            }
                            </style>
                        """, unsafe_allow_html=True)

                        if st.button("📧 Enviar", key=f"email_{card_key}"):
                            enviar_email_usuario(
                                user_id=r.id,
                                mes=mes,
                                ano=ano
                            )
                            st.success(f"E-mail enviado ({mes:02d}/{ano})")
                        if st.button("📊 Estatísticas", key=f"stats_{card_key}"):
                            enviar_email_estatisticas_usuario(
                                user_id=r.id,
                                mes=mes,
                                ano=ano
                            )
                            st.success("Relatório de estatísticas enviado!")


    except SQLAlchemyError:
        logger.exception("Erro SQL em listar_usuarios")
        st.error("Erro ao carregar usuários (banco de dados).")
    except Exception:
        logger.exception("Erro inesperado em listar_usuarios")
        st.error("Erro inesperado ao listar usuários.")
