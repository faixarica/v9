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
    if not value:
        return "-"
    try:
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def _table_exists(db, table_name: str) -> bool:
    return bool(db.execute(text("""
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = :t
        LIMIT 1
    """), {"t": table_name}).scalar())


def _pick_hits_table(db):
    """
    Autodetecta a tabela de validação/hits/acertos existente no banco.
    Ajuste/adicione nomes aqui conforme seu projeto.
    """
    candidates = [
        "palpites_hits",            # que você já mencionou antes
        "palpites_validacoes",      # nome comum
        "validacoes_palpites",      # variação
        "palpites_resultados",      # variação
        "estatisticas_cache",       # sua tabela de cache
    ]
    for t in candidates:
        if _table_exists(db, t):
            return t
    return None


def _render_faixas(title: str, faixas_dict: dict, total_ref: int):
    st.markdown(f"#### {title}")
    linhas = []
    for k in sorted(faixas_dict.keys(), key=lambda x: int(x)):
        v = faixas_dict[k]
        pct = (v / total_ref * 100) if total_ref else 0
        linhas.append({"Faixa": k, "Qtde": v, "%": f"{pct:.2f}%"})
    st.dataframe(linhas, use_container_width=True, hide_index=True)


def _buscar_faixas_no_hits(db, hits_table: str, user_id: int, mes: int, ano: int):
    """
    Busca faixas de acerto REAL a partir de uma tabela de validação/hits.
    ESTE método supõe que a tabela tenha colunas:
      - id_usuario
      - loteria (ou tipo_loteria)
      - data (ou dt_validacao)
      - acertos (int)
    Como seu schema pode variar, ele tenta múltiplos nomes de coluna.
    """
    # tenta achar colunas possíveis
    cols = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name = :t
    """), {"t": hits_table}).fetchall()
    colset = {c.column_name for c in cols}

    # possíveis nomes (auto)
    col_user = "id_usuario" if "id_usuario" in colset else ("user_id" if "user_id" in colset else None)
    col_acertos = "acertos" if "acertos" in colset else ("hits" if "hits" in colset else None)
    col_loteria = "loteria" if "loteria" in colset else ("tipo_loteria" if "tipo_loteria" in colset else None)
    col_data = "data" if "data" in colset else ("dt_validacao" if "dt_validacao" in colset else ("created_at" if "created_at" in colset else None))

    if not all([col_user, col_acertos, col_loteria, col_data]):
        return None, f"Tabela '{hits_table}' existe, mas não tem colunas esperadas (usuário/acertos/loteria/data)."

    # busca contagens por faixa e loteria
    rows = db.execute(text(f"""
        SELECT
            {col_loteria} AS loteria,
            {col_acertos} AS acertos,
            COUNT(*) AS qtd
        FROM {hits_table}
        WHERE {col_user} = :u
          AND EXTRACT(MONTH FROM {col_data}) = :m
          AND EXTRACT(YEAR FROM {col_data}) = :a
        GROUP BY {col_loteria}, {col_acertos}
        ORDER BY {col_loteria}, {col_acertos}
    """), {"u": user_id, "m": mes, "a": ano}).fetchall()

    # normaliza
    lf = {str(x): 0 for x in [11, 12, 13, 14, 15]}
    ms = {str(x): 0 for x in [4, 5, 6]}
    total_validacoes_lf = 0
    total_validacoes_ms = 0

    for r in rows:
        lot = (str(r.loteria or "")).lower()
        a = int(r.acertos)
        q = int(r.qtd)

        # heurística de loteria
        if "loto" in lot or "lf" in lot:
            total_validacoes_lf += q
            if a in [11, 12, 13, 14, 15]:
                lf[str(a)] += q
        elif "mega" in lot or "ms" in lot:
            total_validacoes_ms += q
            if a in [4, 5, 6]:
                ms[str(a)] += q

    return {
        "lf": lf,
        "ms": ms,
        "total_validacoes_lf": total_validacoes_lf,
        "total_validacoes_ms": total_validacoes_ms,
    }, None


# =========================================================
# MAIN
# =========================================================

def listar_usuarios():
    st.markdown("## 🐵 Administração de Usuários")

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2 = st.columns(2)
        filtro_usuario = c1.text_input("Usuário")
        filtro_email = c2.text_input("E-mail")

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

            usuarios = db.execute(text(query), params).fetchall()

        if not usuarios:
            st.info("Nenhum usuário encontrado.")
            return

        st.markdown("""
        <style>
        .user-card{
            background:#fff; padding:14px; border-radius:14px;
            border:1px solid #e5e7eb; box-shadow:0 2px 4px rgba(0,0,0,0.06);
            margin-bottom:10px;
        }
        .muted{ color:#6b7280; }
        </style>
        """, unsafe_allow_html=True)

        # cards 2 colunas
        for i in range(0, len(usuarios), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j >= len(usuarios):
                    continue

                u = usuarios[i + j]
                with cols[j]:
                    st.markdown(f"""
                        <div class="user-card">
                            <b>👤 {u.usuario}</b><br>
                            <span class="muted">📧 {u.email or "-"}</span><br><br>
                            Tipo: <b>{u.tipo}</b><br>
                            Plano: <b>{u.plano}</b><br>
                            Cadastro: {_format_date(u.dt_cadastro)}<br>
                            Palpites gerados (total): <b>{u.total_palpites}</b>
                        </div>
                    """, unsafe_allow_html=True)

                    c_mes, c_ano, c_email, c_stats = st.columns([2, 2, 1.2, 1.4])

                    mes = c_mes.selectbox(
                        "Mês",
                        list(range(1, 13)),
                        format_func=lambda x: f"{x:02d}",
                        key=f"mes_{u.id}"
                    )

                    ano_atual = datetime.now().year
                    ano = c_ano.selectbox(
                        "Ano",
                        list(range(ano_atual, ano_atual - 6, -1)),
                        key=f"ano_{u.id}"
                    )

                    if c_email.button("📧 E-mail", key=f"btn_email_{u.id}", use_container_width=True):
                        enviar_email_usuario(user_id=u.id, mes=mes, ano=ano)
                        st.success("E-mail enviado!")

                    # estado separado
                    open_key = f"stats_open_{u.id}"
                    if open_key not in st.session_state:
                        st.session_state[open_key] = False

                    if c_stats.button("📊 Estatísticas", key=f"btn_stats_{u.id}", use_container_width=True):
                        st.session_state[open_key] = not st.session_state[open_key]

                    if st.session_state[open_key]:
                        with st.expander(f"📊 Estatísticas — {u.usuario} ({mes:02d}/{ano})", expanded=True):
                            with Session() as db:
                                hits_table = _pick_hits_table(db)

                                if not hits_table:
                                    st.error("Não encontrei nenhuma tabela de validação/hits no banco para calcular acertos reais.")
                                    st.info("Candidatas: palpites_hits / palpites_validacoes / estatisticas_cache")
                                else:
                                    stats, err = _buscar_faixas_no_hits(db, hits_table, u.id, mes, ano)
                                    if err:
                                        st.error(err)
                                    else:
                                        st.caption(f"Fonte: {hits_table}")

                                        # totais e percentuais reais (baseados no total de validações do mês)
                                        colA, colB = st.columns(2)
                                        with colA:
                                            total_lf = stats["total_validacoes_lf"]
                                            total_faixa_lf = sum(stats["lf"].values())
                                            pct_lf = (total_faixa_lf / total_lf * 100) if total_lf else 0
                                            st.metric("LF validados no mês", total_lf)
                                            st.metric("LF com 11–15", total_faixa_lf)
                                            st.metric("LF % (11–15)", f"{pct_lf:.2f}%")

                                        with colB:
                                            total_ms = stats["total_validacoes_ms"]
                                            total_faixa_ms = sum(stats["ms"].values())
                                            pct_ms = (total_faixa_ms / total_ms * 100) if total_ms else 0
                                            st.metric("MS validados no mês", total_ms)
                                            st.metric("MS com 4–6", total_faixa_ms)
                                            st.metric("MS % (4–6)", f"{pct_ms:.2f}%")

                                        st.divider()
                                        _render_faixas("🎯 Lotofácil — faixas 11–15", stats["lf"], stats["total_validacoes_lf"])
                                        _render_faixas("🎯 Mega-Sena — faixas 4–6", stats["ms"], stats["total_validacoes_ms"])

                                        st.markdown("### 📈 Comparativo (%)")
                                        chart_data = {
                                            "Loteria": ["Lotofácil", "Mega-Sena"],
                                            "% Faixas alvo": [pct_lf, pct_ms],
                                        }
                                        st.bar_chart(chart_data, x="Loteria")

    except SQLAlchemyError:
        logger.exception("Erro SQL em listar_usuarios")
        st.error("Erro ao carregar usuários (banco de dados).")

    except Exception:
        logger.exception("Erro inesperado em listar_usuarios")
        st.error("Erro inesperado ao carregar usuários.")
