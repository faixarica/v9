# acertos_dia_app.py — Streamlit (FaixaBet) | NASA Lab Edition (FIX FINAL)
# - Lotofácil + Mega-Sena
# - Sidebar com cores/valores visíveis (BaseWeb)
# - Datas robustas (suporta "30/12/2025", "2025-12-30", date/timestamp)
# - Cards, métricas, gráfico, export CSV

import streamlit as st
from datetime import date
from sqlalchemy import text
import pandas as pd
import altair as alt

from db import Session


# =====================================================
# 🎨 UI / CSS
# =====================================================
def apply_ui():
    st.set_page_config(
        page_title="FaixaBet • Acertos do Dia",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        /* ---------- Sidebar container ---------- */
        [data-testid="stSidebar"]{
            background: linear-gradient(180deg, #0b1c2d, #091826);
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        /* ---------- Sidebar labels ---------- */
        [data-testid="stSidebar"] label{
            color:#E8F0F7 !important;
            font-weight:600 !important;
        }

        /* ---------- BaseWeb (Selectbox) ---------- */
        /* container */
        [data-testid="stSidebar"] [data-baseweb="select"] > div{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 10px !important;
        }
        /* selected value text */
        [data-testid="stSidebar"] [data-baseweb="select"] span{
            color:#FFFFFF !important;
            font-weight:600 !important;
        }
        /* dropdown arrow */
        [data-testid="stSidebar"] [data-baseweb="select"] svg{
            fill:#FFFFFF !important;
        }

        /* ---------- Date input ---------- */
        [data-testid="stSidebar"] .stDateInput input{
            color:#FFFFFF !important;
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 10px !important;
        }

        /* ---------- Text input ---------- */
        [data-testid="stSidebar"] .stTextInput input{
            color:#FFFFFF !important;
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
            border-radius: 10px !important;
        }

        /* Placeholder */
        [data-testid="stSidebar"] input::placeholder{
            color: rgba(255,255,255,0.6) !important;
        }

        /* ---------- Slider ---------- */
        [data-testid="stSidebar"] .stSlider{
            color:#FFFFFF !important;
        }
        /* value label near slider */
        [data-testid="stSidebar"] .stSlider [data-testid="stTickBarMin"],
        [data-testid="stSidebar"] .stSlider [data-testid="stTickBarMax"]{
            color:#FFFFFF !important;
        }
        [data-testid="stSidebar"] .stSlider div{
            color:#FFFFFF !important;
        }

        /* ---------- Button ---------- */
        [data-testid="stSidebar"] .stButton button{
            border-radius: 12px !important;
            font-weight: 700 !important;
        }

        /* ---------- Main cards ---------- */
        .fb-card{
            border-radius: 16px;
            padding: 16px;
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
            border: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 16px;
        }
        .nums{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono","Courier New", monospace;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# 🧠 SQL Helpers (datas robustas)
# =====================================================
def sql_date_expr(alias: str, col: str) -> str:
    """
    Normaliza datas para ::date aceitando:
    - date/timestamp
    - 'YYYY-MM-DD'
    - 'DD/MM/YYYY'
    """
    return f"""
    (CASE
        WHEN {alias}.{col} IS NULL THEN NULL
        WHEN pg_typeof({alias}.{col})::text IN ('date','timestamp without time zone','timestamp with time zone')
            THEN {alias}.{col}::timestamp::date
        WHEN {alias}.{col}::text ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
            THEN {alias}.{col}::date
        WHEN {alias}.{col}::text ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'
            THEN to_date({alias}.{col}::text, 'DD/MM/YYYY')
        ELSE NULL
     END)
    """


# =====================================================
# 📦 Fetchers (sem data::date direto)
# =====================================================
def fetch_resultado(db, lottery: str, data_ref: date):
    if lottery == "LOTOFACIL":
        table = "resultados_oficiais"
        date_col = "data"
        concurso_col = "concurso"
        ncols = [f"n{i}" for i in range(1, 16)]
    else:
        # ajuste se seu nome real for diferente
        table = "resultados_oficiais_ms"
        date_col = "data"
        concurso_col = "concurso"
        ncols = [f"n{i}" for i in range(1, 7)]

    sql = f"""
    SELECT
        {concurso_col} AS concurso,
        {sql_date_expr('r', date_col)} AS data_norm,
        {", ".join(ncols)}
    FROM {table} r
    WHERE {sql_date_expr('r', date_col)} = :d
    ORDER BY {concurso_col} DESC
    LIMIT 1
    """
    row = db.execute(text(sql), {"d": data_ref.isoformat()}).fetchone()
    if not row:
        return None

    nums = []
    for c in ncols:
        v = getattr(row, c, None)
        if v is not None:
            nums.append(int(v))

    return {"concurso": int(row.concurso), "data": row.data_norm, "numeros": nums, "table": table}


def fetch_palpites(db, lottery: str, data_ref: date, tipo: str, user_id: int | None):
    if lottery == "LOTOFACIL":
        table = "palpites"
        date_col = "data"
    else:
        table = "palpites_m"
        date_col = "data"

    sql = f"""
    SELECT id, id_usuario, numeros, modelo,
           {sql_date_expr('p', date_col)} AS data_norm
    FROM {table} p
    WHERE {sql_date_expr('p', date_col)} = :d
    """
    params = {"d": data_ref.isoformat()}

    if tipo != "admin" and user_id:
        sql += " AND p.id_usuario = :uid"
        params["uid"] = user_id

    sql += " ORDER BY id DESC"
    return db.execute(text(sql), params).fetchall()


def parse_numbers(raw):
    if raw is None:
        return []
    s = str(raw).strip()
    s = s.replace("[", "").replace("]", "").replace(";", ",")
    s = s.replace("  ", " ").replace(" ", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    out = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
    return out


# =====================================================
# 📊 Charts
# =====================================================
def chart_faixa(df: pd.DataFrame):
    if df.empty:
        st.info("Nenhum palpite dentro da faixa selecionada.")
        return

    counts = df["qtd_acertos"].value_counts().sort_index()
    chart_df = pd.DataFrame({"acertos": counts.index.astype(int), "qtde": counts.values.astype(int)})

    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("acertos:O", title="Acertos"),
            y=alt.Y("qtde:Q", title="Quantidade"),
            tooltip=["acertos", "qtde"],
            color=alt.value("#00ffAA"),
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)


# =====================================================
# 🧪 APP
# =====================================================
def main():
    apply_ui()

    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Controles")

        lottery_label = st.selectbox(
            "🎲 Loteria",
            ["Lotofácil", "Mega-Sena"],
            key="loteria_select",
        )
        lottery = "LOTOFACIL" if lottery_label == "Lotofácil" else "MEGASENA"
        max_hits = 15 if lottery == "LOTOFACIL" else 6

        data_escolhida = st.date_input(
            "📅 Data do sorteio",
            date.today(),
            format="DD/MM/YYYY",
            key="data_sorteio",
        )

        tipo = st.selectbox(
            "👤 Tipo de usuário",
            ["admin", "user"],
            index=1,
            key="tipo_usuario",
        )

        user_id_raw = st.text_input(
            "🆔 ID do usuário (opcional)",
            placeholder="Apenas números…",
            key="user_id_input",
        )
        user_id = int(user_id_raw) if user_id_raw.strip().isdigit() else None

        st.markdown("---")

        default_min = 11 if lottery == "LOTOFACIL" else 4
        default_max = 15 if lottery == "LOTOFACIL" else 6

        min_hit = st.slider(
            "🎯 Faixa mínima de acertos",
            0, max_hits,
            default_min,
            key="faixa_min",
        )
        max_hit = st.slider(
            "🏁 Faixa máxima de acertos",
            0, max_hits,
            default_max,
            key="faixa_max",
        )

        # mini “status card” (UX)
        st.markdown(
            f"""
            <div style="padding:10px;border-radius:12px;background:rgba(255,255,255,0.06);
                        border:1px solid rgba(255,255,255,0.12); font-size:.88rem;">
                <b>Config atual</b><br>
                🎲 {lottery_label}<br>
                📅 {data_escolhida.strftime('%d/%m/%Y')}<br>
                🎯 Faixa: {min_hit}–{max_hit}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if min_hit > max_hit:
            st.error("A faixa está invertida. Ajuste min/max.")
            st.stop()

        run = st.button("🔎 Analisar acertos", use_container_width=True)

    # Header
    st.markdown(
        f"""
        <div class="fb-card">
            <b>🎯 Acertos do Dia — {lottery_label}</b><br>
            <span style="opacity:.75">Análise instantânea (datas robustas + visual limpo).</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not run:
        st.caption("Selecione os filtros no menu lateral e clique em **Analisar acertos**.")
        return

    db = Session()
    try:
        res = fetch_resultado(db, lottery, data_escolhida)
        if not res:
            st.warning("Resultado oficial não encontrado para a data/loteria informada.")
            return

        rows = fetch_palpites(db, lottery, data_escolhida, tipo, user_id)
        if not rows:
            st.info("Nenhum palpite encontrado para essa data (com os filtros atuais).")
            return

        oficiais = set(res["numeros"])
        dados = []

        for r in rows:
            nums = parse_numbers(r.numeros)
            hits = sorted(oficiais.intersection(nums))
            dados.append(
                {
                    "id": int(r.id),
                    "id_usuario": int(r.id_usuario) if r.id_usuario is not None else None,
                    "modelo": str(r.modelo) if r.modelo is not None else "—",
                    "qtd_acertos": len(hits),
                    "numeros": " ".join(f"{n:02d}" for n in sorted(nums)),
                    "acertos": " ".join(f"{n:02d}" for n in hits),
                }
            )

        df = pd.DataFrame(dados).sort_values(["qtd_acertos", "id"], ascending=[False, False])

        df_faixa = df[(df["qtd_acertos"] >= min_hit) & (df["qtd_acertos"] <= max_hit)]
        total = len(df)
        winners = len(df_faixa)
        best = int(df["qtd_acertos"].max()) if total else 0
        avg = float(df["qtd_acertos"].mean()) if total else 0.0

        # Card principal
        st.markdown(
            f"""
            <div class="fb-card">
                <b>📅 {data_escolhida.strftime('%d/%m/%Y')} • Concurso #{res['concurso']}</b><br>
                <span style="opacity:.75">Números sorteados:</span>
                <span class="nums">{", ".join(f"{n:02d}" for n in sorted(res["numeros"]))}</span><br><br>
                <b>Palpites no dia:</b> {total} &nbsp; | &nbsp;
                <b>Na faixa:</b> {winners} &nbsp; | &nbsp;
                <b>Melhor hit:</b> {best} &nbsp; | &nbsp;
                <b>Média:</b> {avg:.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs(["📌 Resumo", "🧾 Detalhes", "⬇️ Exportar"])

        with tab1:
            st.markdown("#### 📈 Distribuição (apenas faixa selecionada)")
            chart_faixa(df_faixa[["qtd_acertos"]].copy())

            st.markdown("#### 🏅 Palpites na faixa")
            if df_faixa.empty:
                st.info("Nenhum palpite dentro da faixa selecionada.")
            else:
                st.dataframe(df_faixa, use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("#### 🔎 Todos os palpites (ordenado por acertos)")
            st.dataframe(df, use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("#### ⬇️ Exportar CSV")
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar CSV",
                data=csv,
                file_name=f"acertos_{lottery.lower()}_{data_escolhida.isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.caption(f"Fonte resultados: `{res.get('table','?')}`")

    finally:
        db.close()


if __name__ == "__main__":
    main()
