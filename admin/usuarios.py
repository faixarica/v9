# usuarios.py - administração de usuários (visão ADM)
#update qtd usuarios

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


def _calcular_estatisticas_reais(db, user_id: int, mes: int, ano: int):
    """
    Calcula estatísticas REAIS via queries diretas em palpites/resultados.
    Substitui a dependência de 'palpites_hits' que estava vazia.
    """
    stats = {
        "lf": {str(x): 0 for x in [11, 12, 13, 14, 15]},
        "ms": {str(x): 0 for x in [4, 5, 6]},
        "total_validacoes_lf": 0,
        "total_validacoes_ms": 0,
    }

    try:
        # --- LOTOFÁCIL ---
        # Cruza palpites com resultados pela data (normalizada)
        q_lf = text("""
            WITH base AS (
                SELECT
                    p.id,
                    (SELECT COUNT(*) 
                     FROM unnest(regexp_split_to_array(NULLIF(trim(COALESCE(p.dezenas, p.numeros)),''),'[,\\s]+')) d(txt)
                     WHERE d.txt ~ '^\\d+$' 
                       AND d.txt::int IN (r.n1,r.n2,r.n3,r.n4,r.n5,r.n6,r.n7,r.n8,r.n9,r.n10,r.n11,r.n12,r.n13,r.n14,r.n15)
                    ) as acertos
                FROM palpites p
                JOIN resultados_oficiais r ON r.data = p.data_norm
                WHERE p.id_usuario = :uid
                  AND EXTRACT(MONTH FROM CAST(p.created_at AS DATE)) = :m
                  AND EXTRACT(YEAR FROM CAST(p.created_at AS DATE)) = :a
            )
            SELECT acertos, COUNT(*) as qtd
            FROM base
            GROUP BY acertos
        """)
        
        rows_lf = db.execute(q_lf, {"uid": user_id, "m": mes, "a": ano}).fetchall()
        for r in rows_lf:
            acertos = r.acertos
            qtd = r.qtd
            stats["total_validacoes_lf"] += qtd
            if acertos in [11, 12, 13, 14, 15]:
                 stats["lf"][str(acertos)] += qtd

        # --- MEGA-SENA ---
        q_ms = text("""
            WITH base AS (
                SELECT
                    p.id,
                    (SELECT COUNT(*) 
                     FROM unnest(regexp_split_to_array(NULLIF(trim(p.numeros),''),'[,\\s]+')) d(txt)
                     WHERE d.txt ~ '^\\d+$' 
                       AND d.txt::int IN (r.n1,r.n2,r.n3,r.n4,r.n5,r.n6)
                    ) as acertos
                FROM palpites_m p
                JOIN resultados_oficiais_m r ON r.data = p.data_norm
                WHERE p.id_usuario = :uid
                  AND EXTRACT(MONTH FROM CAST(p.created_at AS DATE)) = :m
                  AND EXTRACT(YEAR FROM CAST(p.created_at AS DATE)) = :a
            )
            SELECT acertos, COUNT(*) as qtd
            FROM base
            GROUP BY acertos
        """)
        
        rows_ms = db.execute(q_ms, {"uid": user_id, "m": mes, "a": ano}).fetchall()
        for r in rows_ms:
            acertos = r.acertos
            qtd = r.qtd
            stats["total_validacoes_ms"] += qtd
            if acertos in [4, 5, 6]:
                 stats["ms"][str(acertos)] += qtd

        return stats, None

    except Exception as e:
        return None, f"Erro ao calcular estatísticas: {e}"


# =========================================================
# MAIN
# =========================================================

def listar_usuarios():
    st.markdown("## 🐵 Administração de Usuários")

    # [INÍCIO] Dashboard de métricas de usuários
    try:
        with Session() as db:
            # 1. Total Geral
            total_users = db.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() or 0
            
            # 2. Por Plano (agrupado)
            #    Assume planos: Free (default), Silver, Gold, Platinum
            #    COALESCE(p.nome, 'Free') garante que quem não tem plano caia no Free
            rows = db.execute(text("""
                SELECT 
                    COALESCE(p.nome, 'Free') as nome_plano,
                    COUNT(*) as qtd
                FROM usuarios u
                LEFT JOIN planos p ON p.id = u.id_plano
                GROUP BY 1
            """)).fetchall()
            
            # Normaliza para garantir que todos apareçam (mesmo zerados)
            stats = {"Free": 0, "Silver": 0, "Gold": 0, "Platinum": 0}
            for nome, qtd in rows:
                # normaliza nome (ex: "Silver " -> "Silver")
                clean_name = str(nome).strip()
                # Se for algum plano exótico, adiciona também final
                if clean_name not in stats:
                    stats[clean_name] = 0
                stats[clean_name] += qtd
            
            # Exibição
            c_tot, c_free, c_silver, c_gold, c_plat = st.columns(5)
            
            c_tot.metric("👥 Total Usuários", total_users)
            c_free.metric("🆓 Free", stats.get("Free", 0))
            c_silver.metric("🥈 Silver", stats.get("Silver", 0))
            c_gold.metric("🥇 Gold", stats.get("Gold", 0))
            c_plat.metric("💎 Platinum", stats.get("Platinum", 0))
            
            st.divider()

    except Exception as e:
        logger.error(f"Erro ao carregar estatísticas de usuários: {e}")
        st.error("Não foi possível carregar os totais de usuários.")

    # [FIM] Dashboard de métricas

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
                                # Chama cálculo em tempo real
                                stats, err = _calcular_estatisticas_reais(db, u.id, mes, ano)

                                if err:
                                    st.error(err)
                                else:
                                    st.caption("Cálculo em tempo real (baseado em resultados importados)")

                                    # totais e percentuais
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
