# dashboard.py adaptado para PostgreSQL no Neon.tech
# -------------------- [1] IMPORTS --------------------

import os
import pandas as pd
#import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt   

from collections import defaultdict
import streamlit as st
from sqlalchemy import text
from app.db import Session
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date

# -------------------- [2] CSS PERSONALIZADO --------------------

def apply_custom_css():
    st.markdown("""
        <style>
            /* ===============================
               LAYOUT GLOBAL (HEADER / LOGO)
               =============================== */

            /* Remove espaço superior padrão do Streamlit */
            .block-container {
                padding-top: 2rem !important;
            }

            /* Remove margem automática após imagens (logo) */
            img {
                margin-bottom: 0rem !important;
            }

            /* Remove margem extra antes/depois dos títulos */
            h1, h2, h3, h4 {
                margin-top: 0rem !important;
                margin-bottom: 0.2rem !important;
                padding-top: 0rem !important;
            }

            /* ===============================
               SEUS ESTILOS EXISTENTES
               =============================== */

            .card {
                padding: 12px;
                margin: 10px 0;
                border-left: 6px solid #6C63FF;
                border-radius: 10px;
                background-color: #f0f2f6;
                text-align: center;
                font-size: 16px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }

            .metric-title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
                color: #333;
            }

            .metric-value {
                font-size: 22px;
                color: #6C63FF;
            }

            .scrollable-container {
                max-height: 700px;
                overflow-y: auto;
                padding-right: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# -------------------- [3] FUNÇÃO AUXILIAR DE DATA --------------------

def _fmt_date_br(x):
    """Converte qualquer tipo de data em formato dd/mm/yyyy"""
    if isinstance(x, (datetime, date)):
        return x.strftime("%d/%m/%Y")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(x), fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return str(x)

# -------------------- [4] DASHBOARD PRINCIPAL --------------------

def grafico_frequencia_palpites():
    db = Session()
    try:
        result = db.execute(text("SELECT numeros FROM palpites"))
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=["numeros"])
    finally:
        db.close()

    todos_numeros = df["numeros"].dropna().apply(lambda x: list(map(int, x.split(","))))
    todos_numeros = pd.Series([num for sublist in todos_numeros for num in sublist])
    frequencia = todos_numeros.value_counts().sort_index()
    df_freq = pd.DataFrame({"Número": frequencia.index, "Frequência": frequencia.values})

    fig, ax = plt.subplots(figsize=(7, 3.5))
    sns.barplot(data=df_freq, x="Número", y="Frequência", palette="Blues", ax=ax)
    ax.set_title("Frequência nos Palpites dos Usuários", fontsize=14)
    ax.set_xlabel("Números")
    ax.set_ylabel("Frequência")

    return fig

    # essa def esta sem utilização(ainda)!!!!

def mostrar_telemetria():
    st.markdown("##  Telemetria dos Modelos (FaixaBet AI)")
    db = Session()

    try:
        # --------------------------------------------
        # 1) Quantidade de palpites por modelo
        # --------------------------------------------
        st.markdown("###  Quantidade de palpites gerados por modelo")
        query_qtd = text("""
            SELECT modelo, COUNT(*) AS quantidade
            FROM telemetria
            GROUP BY modelo
            ORDER BY quantidade DESC;
        """)
        df_qtd = pd.read_sql(query_qtd, db.bind)
        if df_qtd.empty:
            st.info("Ainda não há dados de telemetria registrados.")
            return
        st.bar_chart(df_qtd.set_index("modelo"))

        # --------------------------------------------
        # 2) Desempenho médio e taxas (usando LATERAL)
        # --------------------------------------------
        st.markdown("###  Desempenho médio (acertos) e taxas ≥13/≥14/15")

        query_perf = text("""
            WITH base AS (
                SELECT
                    t.modelo,
                    -- calcula acertos 1x por palpite com LATERAL (rápido e limpo)
                    h.acertos
                FROM telemetria t
                JOIN resultados_oficiais r
                  ON to_char(t.data_execucao, 'DD/MM/YYYY') = r.data
                CROSS JOIN LATERAL (
                    SELECT COUNT(*) AS acertos
                    FROM unnest(t.dezenas) AS p(num)
                    WHERE p = ANY(ARRAY[
                        r.n1, r.n2, r.n3, r.n4, r.n5,
                        r.n6, r.n7, r.n8, r.n9, r.n10,
                        r.n11, r.n12, r.n13, r.n14, r.n15
                    ])
                ) h
            )
            SELECT
                modelo,
                COUNT(*)                           AS palpites,
                ROUND(AVG(acertos)::numeric, 2)    AS media_acertos,
                COUNT(*) FILTER (WHERE acertos>=13) AS qtd_13p,
                COUNT(*) FILTER (WHERE acertos>=14) AS qtd_14p,
                COUNT(*) FILTER (WHERE acertos=15)  AS qtd_15p
            FROM base
            GROUP BY modelo
            ORDER BY media_acertos DESC, palpites DESC;
        """)

        df_perf = pd.read_sql(query_perf, db.bind)
        st.dataframe(df_perf)

        # --------------------------------------------
        # 3) Destaque do melhor modelo
        # --------------------------------------------
        if not df_perf.empty:
            best = df_perf.iloc[0]
            st.success(
                f"Melhor modelo: **{best.modelo}** — "
                f" Média: **{best.media_acertos}** — "
                f" ≥13: {best.qtd_13p} • ≥14: {best.qtd_14p} • 💎 15: {best.qtd_15p}"
            )

    except Exception as e:
        st.error(f"Erro ao carregar telemetria: {e}")

    finally:
        db.close()

def _dezenas_acertos_sql(qtd_dezenas: int, tbl_palpites: str, tbl_res: str) -> str:
    """
    Retorna SQL que:
    - pega palpites do usuário
    - junta com resultado oficial pela data (dd/mm/yyyy)
    - calcula acertos via LATERAL + unnest da coluna dezenas
    Requisitos:
    - palpites(… created_at, dezenas int[] …)
    - resultados_oficiais(… data texto dd/mm/yyyy OU data date; ajuste abaixo)
    """
    # Observação:
    # No seu código, você usa resultados_oficiais.data como algo formatável.
    # Vou cruzar por to_char(created_at,'DD/MM/YYYY') = to_char(r.data,'DD/MM/YYYY')
    # Se r.data for texto dd/mm/yyyy, a comparação vira: to_char(created_at,'DD/MM/YYYY') = r.data

    dezenas_cols = ", ".join([f"r.n{i}" for i in range(1, qtd_dezenas + 1)])

    return f"""
    WITH base AS (
        SELECT
            p.id,
            p.created_at::date AS dt,
            h.acertos
        FROM {tbl_palpites} p
        JOIN {tbl_res} r
          ON to_char(p.created_at, 'DD/MM/YYYY') = 
             CASE 
               WHEN pg_typeof(r.data)::text = 'text' THEN r.data
               ELSE to_char(r.data::date, 'DD/MM/YYYY')
             END
        CROSS JOIN LATERAL (
            SELECT COUNT(*) AS acertos
            FROM unnest(p.dezenas) AS d(num)
            WHERE d.num = ANY(ARRAY[{dezenas_cols}])
        ) h
        WHERE p.id_usuario = :uid
    )
    SELECT
        COUNT(*) AS avaliados,
        MAX(acertos) AS melhor,
        AVG(acertos)::numeric(10,2) AS media,
        COUNT(*) FILTER (WHERE dt >= date_trunc('month', CURRENT_DATE)::date AND acertos >= :min_premio) AS premiaveis_mes,
        COUNT(*) FILTER (WHERE acertos >= :min_premio) AS premiaveis_total,
        AVG(acertos) FILTER (WHERE dt >= CURRENT_DATE - INTERVAL '30 days')::numeric(10,2) AS media_30d,
        AVG(acertos) FILTER (WHERE dt <  CURRENT_DATE - INTERVAL '30 days' AND dt >= CURRENT_DATE - INTERVAL '60 days')::numeric(10,2) AS media_30d_prev
    FROM base;
    """

def mostrar_analise_acertos_topo(user_id: int, loteria=None, loteria_ativa=None):
    import streamlit as st
    from sqlalchemy import text
    from db import Session

    lot = (loteria_ativa or loteria or st.session_state.get("loteria") or "").lower().strip()

    # ---- LOTOFÁCIL (corrigido) ----
    if lot in ("lotofacil", "loto-facil", "loto fácil", "lotofácil", "lf"):

        sql = """
        WITH r_norm AS (
            SELECT
                -- normaliza data do resultado (TEXT) para DATE com segurança
                CASE
                    WHEN r.data ~ '^\\d{2}/\\d{2}/\\d{4}$' THEN to_date(r.data, 'DD/MM/YYYY')
                    WHEN r.data ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN to_date(r.data, 'YYYY-MM-DD')
                    ELSE NULL
                END AS r_dt,
                r.n1,r.n2,r.n3,r.n4,r.n5,
                r.n6,r.n7,r.n8,r.n9,r.n10,
                r.n11,r.n12,r.n13,r.n14,r.n15
            FROM resultados_oficiais r
        ),
        base AS (
            SELECT
                p.id,
                p.data_norm AS p_dt,
                h.acertos
            FROM palpites p
            JOIN r_norm r
              ON r.r_dt = p.data_norm
            CROSS JOIN LATERAL (
                SELECT COUNT(*) AS acertos
                FROM unnest(
                    regexp_split_to_array(
                        NULLIF(trim(COALESCE(p.dezenas, p.numeros)), ''),
                        '[,\\s]+'
                    )
                ) AS d(txt)
                WHERE NULLIF(d.txt,'') IS NOT NULL
                  AND d.txt ~ '^\\d+$'
                  AND (d.txt::int) = ANY(ARRAY[
                      r.n1,r.n2,r.n3,r.n4,r.n5,
                      r.n6,r.n7,r.n8,r.n9,r.n10,
                      r.n11,r.n12,r.n13,r.n14,r.n15
                  ])
            ) h
            WHERE p.id_usuario = :uid
              AND p.data_norm IS NOT NULL
              AND r.r_dt IS NOT NULL
        )
        SELECT
            COUNT(*) AS avaliados,
            COALESCE(MAX(acertos), 0) AS melhor,
            ROUND(COALESCE(AVG(acertos), 0)::numeric, 2) AS media,
            COUNT(*) FILTER (
                WHERE p_dt >= date_trunc('month', CURRENT_DATE)::date
                  AND acertos >= 11
            ) AS premiaveis_mes,
            COUNT(*) FILTER (WHERE acertos >= 11) AS premiaveis_total
        FROM base;
        """

        db = Session()
        try:
            row = db.execute(text(sql), {"uid": user_id}).fetchone()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível calcular a análise de acertos: {e}")
            return
        finally:
            db.close()

        if not row or row.avaliados == 0:
            st.info("Ainda não há palpites avaliáveis.")
            return

        taxa = (row.premiaveis_total / row.avaliados) * 100 if row.avaliados else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏆 Melhor acerto", f"{row.melhor}/15")
        c2.metric("🎯 % Premiável", f"{taxa:.1f}%")
        c3.metric("💎 Premiáveis no mês", row.premiaveis_mes)
        c4.metric("📊 Média de acertos", f"{row.media:.2f}")
        return

    if lot in ("mega-sena", "megasena", "ms"):
        sql = """
        WITH base AS (
            SELECT
                p.id,
                p.data_norm AS p_dt,
                h.acertos
            FROM palpites_m p
            JOIN resultados_oficiais_m r
            ON r.data = p.data_norm
            CROSS JOIN LATERAL (
                SELECT COUNT(*) AS acertos
                FROM unnest(
                    regexp_split_to_array(
                        NULLIF(trim(p.numeros), ''),
                        '[,\\s]+'
                    )
                ) AS d(txt)
                WHERE d.txt ~ '^\\d+$'
                AND (d.txt::int) = ANY (
                    ARRAY[r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]
                )
            ) h
            WHERE p.id_usuario = :uid
            AND p.data_norm IS NOT NULL
        )
        SELECT
            COUNT(*) AS avaliados,
            COALESCE(MAX(acertos), 0) AS melhor,
            ROUND(COALESCE(AVG(acertos), 0)::numeric, 2) AS media,
            COUNT(*) FILTER (
                WHERE p_dt >= date_trunc('month', CURRENT_DATE)::date
                AND acertos >= 4
            ) AS premiaveis_mes,
            COUNT(*) FILTER (WHERE acertos >= 4) AS premiaveis_total
        FROM base;
        """

        db = Session()
        try:
            row = db.execute(text(sql), {"uid": user_id}).fetchone()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível calcular a análise de acertos (Mega-Sena): {e}")
            return
        finally:
            db.close()

        if not row or row.avaliados == 0:
            st.info("Ainda não há palpites avaliáveis para Mega-Sena.")
            return

        taxa = (row.premiaveis_total / row.avaliados) * 100 if row.avaliados else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏆 Melhor acerto", f"{row.melhor}/6")
        c2.metric("🎯 % Premiável", f"{taxa:.1f}%")
        c3.metric("💎 Premiáveis no mês", row.premiaveis_mes)
        c4.metric("📊 Média de acertos", f"{row.media:.2f}")

        return

    # (depois a gente ajusta Mega-Sena separadamente)
    st.info("Função ainda não ajustada para esta loteria neste passo.")


def _sql_analise_acertos_megasena() -> str:
    return """
    WITH base AS (
        SELECT
            p.id,
            p.data_norm AS dt,
            h.acertos
        FROM palpites_m p
        JOIN resultados_oficiais_m r
          ON p.data_norm = r.data
        CROSS JOIN LATERAL (
            SELECT COUNT(*) AS acertos
            FROM unnest(string_to_array(p.dezenas, ',')::int[]) AS d(num)
            WHERE d.num = ANY(ARRAY[
                r.n1, r.n2, r.n3, r.n4, r.n5, r.n6
            ])
        ) h
        WHERE p.id_usuario = :uid
    )
    SELECT
        COUNT(*) AS avaliados,
        COALESCE(MAX(acertos), 0) AS melhor,
        ROUND(AVG(acertos)::numeric, 2) AS media,
        COUNT(*) FILTER (
            WHERE dt >= date_trunc('month', CURRENT_DATE)::date
              AND acertos >= :min_premio
        ) AS premiaveis_mes,
        COUNT(*) FILTER (WHERE acertos >= :min_premio) AS premiaveis_total,
        ROUND(AVG(acertos) FILTER (
            WHERE dt >= CURRENT_DATE - INTERVAL '30 days'
        )::numeric, 2) AS media_30d,
        ROUND(AVG(acertos) FILTER (
            WHERE dt < CURRENT_DATE - INTERVAL '30 days'
              AND dt >= CURRENT_DATE - INTERVAL '60 days'
        )::numeric, 2) AS media_30d_prev
    FROM base;
    """

def evolucao_30_dias(user_id: int, loteria=None, loteria_ativa=None):
    import streamlit as st
    from sqlalchemy import text
    from db import Session

    lot = (loteria_ativa or loteria or st.session_state.get("loteria") or "").lower().strip()

    # =========================================================
    # MEGA-SENA
    # =========================================================
    if lot in ("mega-sena", "megasena", "ms"):

        sql = """
        WITH dias AS (
            SELECT generate_series(
                CURRENT_DATE - INTERVAL '29 days',
                CURRENT_DATE,
                INTERVAL '1 day'
            )::date AS dia
        ),
        dados AS (
            SELECT
                p.data_norm AS dia,
                COUNT(*) AS total_palpites,
                AVG(h.acertos) AS media_acertos
            FROM palpites_m p
            JOIN resultados_oficiais_m r
              ON r.data = p.data_norm
            CROSS JOIN LATERAL (
                SELECT COUNT(*) AS acertos
                FROM unnest(
                    regexp_split_to_array(
                        NULLIF(trim(p.numeros), ''),
                        '[,\\s]+'
                    )
                ) AS d(txt)
                WHERE d.txt ~ '^\\d+$'
                  AND (d.txt::int) = ANY (
                      ARRAY[r.n1, r.n2, r.n3, r.n4, r.n5, r.n6]
                  )
            ) h
            WHERE p.id_usuario = :uid
              AND p.data_norm >= CURRENT_DATE - INTERVAL '29 days'
            GROUP BY p.data_norm
        )
        SELECT
            d.dia,
            COALESCE(x.total_palpites, 0) AS total,
            ROUND(COALESCE(x.media_acertos, 0), 2) AS media
        FROM dias d
        LEFT JOIN dados x ON x.dia = d.dia
        ORDER BY d.dia;
        """

        db = Session()
        try:
            rows = db.execute(text(sql), {"uid": user_id}).fetchall()
        except Exception as e:
            return {
                "permitido": False,
                "erro": str(e)
            }
        finally:
            db.close()

        return {
            "permitido": True,
            "loteria": "Mega-Sena",
            "dados": [
                {
                    "dia": r.dia,
                    "total_palpites": int(r.total),
                    "media_acertos": float(r.media)
                }
                for r in rows
            ]
        }

    # =========================================================
    # LOTOFÁCIL
    # =========================================================
    if lot in ("lotofacil", "lotofácil", "loto-facil", "lf"):

        sql = """
        WITH r_norm AS (
            SELECT
                CASE
                    WHEN r.data ~ '^\\d{2}/\\d{2}/\\d{4}$'
                        THEN to_date(r.data, 'DD/MM/YYYY')
                    WHEN r.data ~ '^\\d{4}-\\d{2}-\\d{2}$'
                        THEN to_date(r.data, 'YYYY-MM-DD')
                    ELSE NULL
                END AS r_dt,
                r.n1,r.n2,r.n3,r.n4,r.n5,
                r.n6,r.n7,r.n8,r.n9,r.n10,
                r.n11,r.n12,r.n13,r.n14,r.n15
            FROM resultados_oficiais r
        ),
        dias AS (
            SELECT generate_series(
                CURRENT_DATE - INTERVAL '29 days',
                CURRENT_DATE,
                INTERVAL '1 day'
            )::date AS dia
        ),
        dados AS (
            SELECT
                p.data_norm AS dia,
                COUNT(*) AS total_palpites,
                AVG(h.acertos) AS media_acertos
            FROM palpites p
            JOIN r_norm r
              ON r.r_dt = p.data_norm
            CROSS JOIN LATERAL (
                SELECT COUNT(*) AS acertos
                FROM unnest(
                    regexp_split_to_array(
                        NULLIF(trim(COALESCE(p.dezenas, p.numeros)), ''),
                        '[,\\s]+'
                    )
                ) AS d(txt)
                WHERE d.txt ~ '^\\d+$'
                  AND (d.txt::int) = ANY (
                      ARRAY[
                          r.n1,r.n2,r.n3,r.n4,r.n5,
                          r.n6,r.n7,r.n8,r.n9,r.n10,
                          r.n11,r.n12,r.n13,r.n14,r.n15
                      ]
                  )
            ) h
            WHERE p.id_usuario = :uid
              AND p.data_norm >= CURRENT_DATE - INTERVAL '29 days'
              AND r.r_dt IS NOT NULL
            GROUP BY p.data_norm
        )
        SELECT
            d.dia,
            COALESCE(x.total_palpites, 0) AS total,
            ROUND(COALESCE(x.media_acertos, 0), 2) AS media
        FROM dias d
        LEFT JOIN dados x ON x.dia = d.dia
        ORDER BY d.dia;
        """

        db = Session()
        try:
            rows = db.execute(text(sql), {"uid": user_id}).fetchall()
        except Exception as e:
            return {
                "permitido": False,
                "erro": str(e)
            }
        finally:
            db.close()

        return {
            "permitido": True,
            "loteria": "Lotofácil",
            "dados": [
                {
                    "dia": r.dia,
                    "total_palpites": int(r.total),
                    "media_acertos": float(r.media)
                }
                for r in rows
            ]
        }

    # =========================================================
    # OUTRAS LOTERIAS (ex: Mega-Sena → tratamos depois)
    # =========================================================
    return {
        "permitido": False,
        "motivo": "Loteria ainda não ajustada nesta função."
    }

def mostrar_dashboard():

    apply_custom_css()
    st.title("Painel Estatístico")

    # -------------------------------
    # 🔹 Login
    # -------------------------------
    #================= LOGOMARCA LOGIN =================
    
    usuario = st.session_state.get("usuario")
    if not usuario:
        st.error("Você precisa estar logado.")
        return

    user_id = usuario["id"]
    plano_id = usuario["id_plano"]
    tipo = usuario.get("tipo", "U")

    # -------------------------------
    # 🔹 Loteria ativa (DEFINIÇÃO ÚNICA, NO TOPO)
    # -------------------------------
    raw_loteria = st.session_state.get("loteria", "lotofacil")

    def _norm_loteria(v: str) -> str:
        s = str(v).strip().lower()
        s = s.replace(" ", "").replace("-", "").replace("_", "")
        if "mega" in s:
            return "megasena"
        return "lotofacil"

    loteria_ativa = _norm_loteria(raw_loteria)

    st.markdown("### O que você quer ver primeiro aqui?")
    op = st.radio(
        "Escolha a visão principal do topo:",
        [
            "🏆 Melhor acerto + % premiável (bem direto)",
            "📈 Evolução (últimos 30 dias) + tendência",
#            "🧠 Modelos: qual modelo dá mais acerto?",
#            "💰 Estimativa de ganhos (simulação) — depois",
        ],
        index=0,
        horizontal=False,
        key=f"enquete_topo_{loteria_ativa}"
    )
   # st.caption("Isso é uma enquete interna pra melhorar o painel.")
        
    # -------------------------------
    # 🔹 Visão do topo (Jogou, Ganhou)
    # -------------------------------
    if op.startswith("🏆"):
        mostrar_analise_acertos_topo(
            user_id=user_id,
            loteria_ativa=loteria_ativa
        )

    elif op.startswith("📈"):
        st.subheader("📈 Evolução (últimos 30 dias)")

        result = evolucao_30_dias(user_id)

        # 🔓 ADMIN SEMPRE VÊ TUDO
        if tipo == "A":
            permitido = True
            plano_label = "Admin"
        else:
            permitido = result.get("permitido", False)
            plano_label = result.get("plano", "Free")

        # 🔒 BLOQUEIO APENAS FREE
        if not permitido:
            st.info("📈 A evolução de desempenho está disponível a partir do plano Silver.")
            st.button("🚀 Fazer upgrade")
            return

        # ----------------------------------------
        # 🔓 SILVER / GOLD / PLATINUM / ADMIN
        # ----------------------------------------
        st.caption(f"Plano atual: **{plano_label}**")

        tendencia = result.get("tendencia", "neutra")

        if tendencia == "alta":
            st.success("📈 Tendência positiva nos últimos 30 dias")
        elif tendencia == "queda":
            st.warning("📉 Tendência de queda nos últimos 30 dias")
        else:
            st.info("➖ Tendência estável nos últimos 30 dias")

        df = pd.DataFrame(result.get("dados", []))
        if df.empty:
            st.info("Ainda não há dados suficientes para exibir a evolução.")
            return

        df["dia"] = pd.to_datetime(df["dia"])
        df = df.set_index("dia")

        st.markdown("#### 📊 Palpites por dia")
        st.line_chart(df["total_palpites"])

        if plano_label in ("Gold", "Platinum", "Admin"):
            st.markdown("#### 🎯 Média de acertos por dia")
            st.line_chart(df["media_acertos"])

    elif op.startswith("🧠"):
        st.info("🧠 Em breve: comparação de modelos/estratégias.")

    elif op.startswith("💰"):
        st.info("💰 Em breve: simulação de ganhos estimados.")

    # -------------------------------
    # 🔹 Verifica login
    # -------------------------------
    usuario = st.session_state.get("usuario")
    if not usuario:
        st.error("Você precisa estar logado.")
        return

    user_id = usuario["id"]
    plano_id = usuario["id_plano"]
    tipo = usuario.get("tipo", "U")

    # -------------------------------
    # 🔹 Normaliza loteria ativa do sidebar
    #    (resolve casos: "Mega-Sena", "mega-sena", "Mega Sena", etc.)
    # -------------------------------
    raw_loteria = st.session_state.get("loteria", "lotofacil")

    def _norm_loteria(v: str) -> str:
        s = str(v).strip().lower()
        s = s.replace(" ", "").replace("-", "").replace("_", "")
        # trata variações comuns
        if "mega" in s:
            return "megasena"
        if "loto" in s:
            return "lotofacil"
        # fallback seguro
        return "lotofacil"

    loteria_ativa = _norm_loteria(raw_loteria)

    if loteria_ativa == "megasena":
        TBL_RES = "resultados_oficiais_m"
        QTD_DEZENAS = 6
        loteria_label = "Mega-Sena"
    else:
        TBL_RES = "resultados_oficiais"
        QTD_DEZENAS = 15
        loteria_label = "Lotofácil"

    # -------------------------------
    # 🔹 Coleta dados principais
    # -------------------------------
    db = Session()
    try:
        # Palpites (por usuário)
        palpites_lf_user = db.execute(
            text("SELECT COUNT(*) FROM palpites WHERE id_usuario = :uid"),
            {"uid": user_id},
        ).scalar() or 0

        palpites_ms_user = db.execute(
            text("SELECT COUNT(*) FROM palpites_m WHERE id_usuario = :uid"),
            {"uid": user_id},
        ).scalar() or 0

        # Totais plataforma (somado)
        total_palpites_plataforma = (
            (db.execute(text("SELECT COUNT(*) FROM palpites")).scalar() or 0)
            + (db.execute(text("SELECT COUNT(*) FROM palpites_m")).scalar() or 0)
        )

        # Estatísticas do usuário (mantive como estava: palpites = lotofácil)
        # define tabela de palpites conforme a loteria ativa
        TBL_PALPITES = "palpites_m" if loteria_ativa == "megasena" else "palpites"

        total_user_dia = db.execute(text(f"""
            SELECT COUNT(*) FROM {TBL_PALPITES}
            WHERE id_usuario = :uid
            AND DATE(data_norm) = CURRENT_DATE
        """), {"uid": user_id}).scalar() or 0

        total_user_mes = db.execute(text(f"""
            SELECT COUNT(*) FROM {TBL_PALPITES}
            WHERE id_usuario = :uid
            AND EXTRACT(MONTH FROM data_norm) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM data_norm) = EXTRACT(YEAR FROM CURRENT_DATE)
        """), {"uid": user_id}).scalar() or 0

    finally:
        db.close()

    # -------------------------------
    # 🔹 Cards principais (mantidos)
    # -------------------------------
    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            f"<div class='card'><div class='metric-title'>Palpites Hoje</div><div class='metric-value'>{total_user_dia}</div></div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"<div class='card'><div class='metric-title'>Palpites no Mês</div><div class='metric-value'>{total_user_mes}</div></div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            f"<div class='card'><div class='metric-title'>Total Plataforma</div><div class='metric-value'>{total_palpites_plataforma}</div></div>",
            unsafe_allow_html=True,
        )

    # -------------------------------
    # 🔹 Palpites por Loteria (por usuário)
    #     - esconder card se plano não suportar
    # -------------------------------
    st.subheader("📌 Palpites por Loteria")

    # ajuste conforme sua regra real:
    # exemplo: Free (1) não tem Mega; Silver+ tem Mega
    plano_permite_ms = (tipo == "A") or (plano_id >= 2)

    if plano_permite_ms:
        cols_lot = st.columns(2)
        with cols_lot[0]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Lotofácil</div>
                    <div class="metric-value">{palpites_lf_user}</div>
                </div>
            """, unsafe_allow_html=True)
        with cols_lot[1]:
            st.markdown(f"""
                <div class="card">
                    <div class="metric-title">Mega-Sena</div>
                    <div class="metric-value">{palpites_ms_user}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # só Lotofácil
        st.markdown(f"""
            <div class="card">
                <div class="metric-title">Lotofácil</div>
                <div class="metric-value">{palpites_lf_user}</div>
            </div>
        """, unsafe_allow_html=True)

    # -------------------------------
    # 🔹 Resultados Oficiais (segue o sidebar)
    #     - key muda por loteria para não “grudar”
    # -------------------------------
    st.subheader(f"Resultados Oficiais — {loteria_label}")

    db = Session()
    try:
        concursos = db.execute(text(f"""
            SELECT concurso, data
            FROM {TBL_RES}
            ORDER BY concurso DESC
            LIMIT 50
        """)).fetchall()
    finally:
        db.close()

    if not concursos:
        st.warning("Nenhum resultado encontrado.")
        return

    opcoes = [f"{c[0]} - {_fmt_date_br(c[1])}" for c in concursos]
    concurso_sel = st.selectbox(
        "Escolha o Concurso:",
        options=opcoes,
        index=0,
        key=f"concurso_sel_{loteria_ativa}",  # ✅ reset por loteria
    )
    concurso_num = int(concurso_sel.split(" - ")[0])

    # Campos de dezenas por loteria
    campos = (
        "n1,n2,n3,n4,n5,n6"
        if QTD_DEZENAS == 6
        else "n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15"
    )

    # Busca resultado do concurso selecionado (na tabela correta)
    db = Session()
    try:
        resultado = db.execute(text(f"""
            SELECT {campos}, data, concurso
            FROM {TBL_RES}
            WHERE concurso = :c
            LIMIT 1
        """), {"c": concurso_num}).fetchone()
    except Exception as e:
        # Fallback se sua tabela Mega usar d1..d6 em vez de n1..n6
        if loteria_ativa == "megasena":
            try:
                campos_alt = "d1,d2,d3,d4,d5,d6"
                resultado = db.execute(text(f"""
                    SELECT {campos_alt}, data, concurso
                    FROM {TBL_RES}
                    WHERE concurso = :c
                    LIMIT 1
                """), {"c": concurso_num}).fetchone()
                QTD_DEZENAS = 6
            except Exception as e2:
                st.error(f"Erro ao ler resultados da Mega-Sena em {TBL_RES}: {e2}")
                return
        else:
            st.error(f"Erro ao ler resultados em {TBL_RES}: {e}")
            return
    finally:
        db.close()

    if not resultado:
        st.warning("Resultado não encontrado para o concurso selecionado.")
        return

    numeros = [int(x) for x in resultado[:QTD_DEZENAS]]
    data_sorteio = resultado[QTD_DEZENAS]
    concurso = resultado[QTD_DEZENAS + 1]

    # Card concurso/data
    st.markdown(f"""
        <div class="card" style="background: linear-gradient(90deg, #4ade80 0%, #22c55e 100%);
            color: white; font-size:18px; text-align:center; font-weight:600;">
            Concurso <span style="font-size:22px;">{concurso}</span> —
            <span style="font-weight:400;">{_fmt_date_br(data_sorteio)}</span>
        </div>
    """, unsafe_allow_html=True)

    # Bolhas dezenas
    bolhas = "".join([
        f"<span style='display:inline-block; background:#6C63FF; color:white; "
        f"border-radius:50%; width:38px; height:38px; line-height:38px; "
        f"margin:3px; font-weight:bold;'>{n:02d}</span>"
        for n in numeros
    ])
    st.markdown(f"<div style='text-align:center; margin-top:10px;'>{bolhas}</div>", unsafe_allow_html=True)

    # (Opcional) Ganhadores por faixa só Lotofácil — se você quiser reativar depois,
    # faça um SELECT que traga os campos ganhadores/rateio.

