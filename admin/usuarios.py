# usuarios.py - administração de usuários (visão ADM)

import streamlit as st
from sqlalchemy import text
from db import Session
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import logging
from .email_notificar_user import enviar_email_usuario

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


def _percentual(acertos, total):
    if not total or total == 0:
        return "0%"
    return f"{(acertos / total) * 100:.1f}%"


# =========================================================
# MAIN
# =========================================================
def listar_usuarios():
    st.markdown("## 👥 Administração de Usuários")

    # ===============================
    # FILTROS
    # ===============================
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            filtro_usuario = st.text_input("Usuário (nome)", placeholder="Ex: carlos")

        with col2:
            filtro_email = st.text_input("E-mail", placeholder="Ex: gmail.com")

    try:
        with Session() as db:
            query = """
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
                WHERE 1 = 1
            """

            params = {}

            if filtro_usuario:
                query += " AND LOWER(u.usuario) LIKE :usuario"
                params["usuario"] = f"%{filtro_usuario.lower()}%"

            if filtro_email:
                query += " AND LOWER(u.email) LIKE :email"
                params["email"] = f"%{filtro_email.lower()}%"

            query += " ORDER BY u.dt_cadastro DESC"

            result = db.execute(text(query), params)
            rows = result.fetchall()

        if not rows:
            st.info("Nenhum usuário encontrado com os filtros aplicados.")
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

                with cols[j]:
                    st.markdown(f"""
                        <div style="background:#fff; padding:14px; border-radius:12px;
                                    border:1px solid #ddd; margin-bottom:10px;
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

                    # ===============================
                    # AÇÕES
                    # ===============================
                    col_mes, col_ano, col_email, col_stats = st.columns([2, 2, 1, 1])

                    with col_mes:
                        mes = st.selectbox(
                            "Mês",
                            list(range(1, 13)),
                            format_func=lambda x: f"{x:02d}",
                            key=f"mes_{r.id}"
                        )

                    with col_ano:
                        ano_atual = datetime.now().year
                        ano = st.selectbox(
                            "Ano",
                            list(range(ano_atual, ano_atual - 6, -1)),  # ano atual até 5 anos atrás
                            key=f"ano_{r.id}"
                        )

                    with col_email:
                        if st.button("📧 E-mail", key=f"email_{r.id}"):
                            enviar_email_usuario(user_id=r.id, mes=mes, ano=ano)
                            st.success("E-mail enviado!")

                    with col_stats:
                        if st.button("📊 Estatísticas", key=f"stats_{r.id}"):
                            st.session_state[f"stats_open_{r.id}"] = True

                    # ===============================
                    # ESTATÍSTICAS (EXPANDER)
                    # ===============================
                    # ===============================
                        # ESTATÍSTICAS (EXPANDER)
                        # ===============================
                        if st.session_state.get(f"stats_open_{r.id}"):

                            with st.expander("📊 Estatísticas do Usuário", expanded=True):

                                st.markdown(f"""
                                **Usuário:** {r.usuario}  
                                **E-mail:** {r.email or '-'}  
                                **Plano:** {r.plano}  
                                **Mês/Ano:** {mes:02d}/{ano}
                                """)

                                with Session() as db:
                                    stats_lf = _estatisticas_loteria(
                                        db, "palpites", r.id, mes, ano
                                    )
                                    stats_ms = _estatisticas_loteria(
                                        db, "palpites_m", r.id, mes, ano
                                    )

                                # -------- GRID --------
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.markdown("### 🎯 Lotofácil")
                                    st.metric("Palpites", stats_lf["total"])
                                    st.metric("% válidos", f"{stats_lf['pct_validos']:.1f}%")
                                    st.metric("% não válidos", f"{stats_lf['pct_invalidos']:.1f}%")

                                with col2:
                                    st.markdown("### 🎯 Mega-Sena")
                                    st.metric("Palpites", stats_ms["total"])
                                    st.metric("% válidos", f"{stats_ms['pct_validos']:.1f}%")
                                    st.metric("% não válidos", f"{stats_ms['pct_invalidos']:.1f}%")

                                # -------- GRÁFICO --------
                                st.markdown("### 📈 Comparativo de Palpites")

                                chart_data = {
                                    "Loteria": ["Lotofácil", "Mega-Sena"],
                                    "Válidos": [stats_lf["validos"], stats_ms["validos"]],
                                    "Não válidos": [stats_lf["invalidos"], stats_ms["invalidos"]],
                                }

                                st.bar_chart(chart_data, x="Loteria")
                            except SQLAlchemyError:
                                logger.exception("Erro SQL em listar_usuarios")
                                st.error("Erro ao carregar usuários (banco de dados).")
                            except Exception:
                                logger.exception("Erro inesperado em listar_usuarios")
                                st.error("Erro inesperado ao listar usuários.")


def _estatisticas_loteria(db, tabela: str, user_id: int, mes: int, ano: int):
    total = db.execute(text(f"""
        SELECT COUNT(*) FROM {tabela}
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    validos = db.execute(text(f"""
        SELECT COUNT(*) FROM {tabela}
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
          AND acertos IS NOT NULL
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    invalidos = total - validos

    pct_validos = (validos / total * 100) if total else 0
    pct_invalidos = 100 - pct_validos if total else 0

    return {
        "total": total,
        "validos": validos,
        "invalidos": invalidos,
        "pct_validos": pct_validos,
        "pct_invalidos": pct_invalidos
    }
