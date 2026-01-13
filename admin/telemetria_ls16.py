# ============================================================
# telemetria_ls16.py — Painel de Telemetria LS16 (Platinum)
# Integração total com db.py + cache + comparação oficial
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

# ------------------------------------------------------------
# 🔹 Integração com db.py (conexão central FaixaBet)
# ------------------------------------------------------------
try:
    from db import engine
except ImportError as e:
    st.error(f"❌ Falha ao importar conexão do db.py: {e}")
    st.stop()

# ------------------------------------------------------------
# ⚙️ Configurações iniciais
# ------------------------------------------------------------
if __name__ == "__main__":
   #st.set_page_config(page_title="Telemetria LS16 (Platinum)", layout="wide")
    st.markdown("""
        <div style='text-align:center; font-size:32px; font-weight:700; color:#4ade80;'>
            📊 Painel de Telemetria — LS16 (Platinum)
        </div>
        <hr>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------
# 🧠 Funções utilitárias e cache
# ------------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_telemetria():
    """Carrega últimas execuções LS16 do banco (com cache de 1 minuto)."""
    query = """
        SELECT * FROM telemetria
        WHERE modelo = 'LS16'
        ORDER BY data_execucao DESC
        LIMIT 500;
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=300)
def carregar_resultados():
    """Carrega últimos resultados oficiais da Lotofácil."""
    query = """
        SELECT concurso, dezenas, data_norm
        FROM resultados_oficiais
        ORDER BY concurso DESC
        LIMIT 100;
    """
    return pd.read_sql(query, engine)


def extrair_dezenas(val):
    """Converte colunas TEXT/ARRAY em lista de inteiros."""
    if isinstance(val, list):
        return [int(x) for x in val]
    v = str(val).replace("{", "").replace("}", "").replace("[", "").replace("]", "")
    return [int(x) for x in v.split(",") if x.strip().isdigit()]


def contar_acertos(palpite, resultado):
    """Conta quantos números do palpite batem com o resultado oficial."""
    return len(set(palpite) & set(resultado))


# ------------------------------------------------------------
# 🔍 Carregamento de dados com tratamento de erros
# ------------------------------------------------------------
try:
    df = carregar_telemetria()
except Exception as e:
    st.error(f"❌ Erro ao carregar telemetria: {e}")
    st.stop()

if df.empty:
    st.warning("⚠️ Nenhum dado encontrado na tabela telemetria (modelo LS16).")
    st.stop()

# ------------------------------------------------------------
# 📑 Tabs principais
# ------------------------------------------------------------
abas = st.tabs([
    "📈 Telemetria Geral",
    "🔢 Frequência e Temperatura",
    "🏆 Comparar com Resultados Oficiais"
])

# ============================================================
# 📈 ABA 1 — TELEMETRIA GERAL
# ============================================================
with abas[0]:
    st.markdown("### 📅 Últimos registros LS16")
    df["data_execucao"] = pd.to_datetime(df["data_execucao"])
    df["temperatura"] = pd.to_numeric(df["temperatura"], errors="coerce")

    st.dataframe(
        df[["data_execucao", "temperatura", "seed", "dezenas", "origem"]].head(20),
        use_container_width=True
    )

    col1, col2 = st.columns(2)
    with col1:
        total_exec = len(df)
        st.metric("📊 Execuções registradas", f"{total_exec}")

    with col2:
        st.metric("🌡️ Temperatura média", f"{df['temperatura'].mean():.3f}")

    st.markdown("#### 📍 Execuções por origem")
    origem_count = df["origem"].value_counts()
    fig, ax = plt.subplots()
    origem_count.plot(kind="bar", ax=ax, color="#4ade80")
    ax.set_ylabel("Qtd execuções")
    ax.set_xlabel("Origem (CLI / Streamlit / API)")
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

# ============================================================
# 🔢 ABA 2 — FREQUÊNCIA DAS DEZENAS E TEMPERATURA
# ============================================================
with abas[1]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🌡️ Distribuição das Temperaturas")
        fig, ax = plt.subplots()
        ax.hist(df["temperatura"].dropna(), bins=10, color="#4ade80", alpha=0.7)
        ax.set_xlabel("Temperatura")
        ax.set_ylabel("Frequência")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    with col2:
        st.markdown("#### 📈 Estatísticas")
        st.metric("Execuções registradas", f"{len(df)}")
        st.metric("Temperatura média", f"{df['temperatura'].mean():.3f}")
        st.metric("Desvio padrão", f"{df['temperatura'].std():.3f}")

    st.markdown("### 🔢 Frequência das dezenas (últimas 200 execuções)")
    dezenas_expandidas = []
    for dz in df["dezenas"].head(200):
        dezenas_expandidas.extend(extrair_dezenas(dz))

    if dezenas_expandidas:
        counts = pd.Series(dezenas_expandidas).value_counts().sort_index()
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(counts.index, counts.values, color="#4ade80", alpha=0.8)
        ax.set_xticks(range(1, 26))
        ax.set_xlabel("Dezena (1–25)")
        ax.set_ylabel("Frequência")
        ax.set_title("Frequência das dezenas mais geradas")
        st.pyplot(fig)
    else:
        st.info("Nenhum palpite LS16 válido para análise.")

# ============================================================
# 🏆 ABA 3 — COMPARAR COM RESULTADOS OFICIAIS
# ============================================================
with abas[2]:
    st.markdown("### 🏆 Comparação com Resultados Oficiais")

    try:
        df_res = carregar_resultados()
        df_res["dezenas"] = df_res["dezenas"].apply(extrair_dezenas)
    except Exception as e:
        st.error(f"Erro ao carregar resultados oficiais: {e}")
        st.stop()

    st.markdown("#### 🔍 Selecione um concurso para comparar")
    concurso = st.selectbox("Concurso:", df_res["concurso"])
    dezenas_oficiais = df_res.loc[df_res["concurso"] == concurso, "dezenas"].values[0]

    st.write(f"**Dezenas oficiais:** {sorted(dezenas_oficiais)}")

    comparacoes = []
    for _, row in df.head(100).iterrows():
        palpite = extrair_dezenas(row["dezenas"])
        acertos = contar_acertos(palpite, dezenas_oficiais)
        comparacoes.append({
            "data_execucao": row["data_execucao"],
            "seed": row["seed"],
            "acertos": acertos,
            "dezenas": palpite,
            "temperatura": row["temperatura"],
            "origem": row["origem"]
        })

    df_comp = pd.DataFrame(comparacoes).sort_values(by="acertos", ascending=False)
    st.markdown("#### 🧮 Top palpites (por nº de acertos)")
    st.dataframe(df_comp.head(15), use_container_width=True)

    # Distribuição de acertos
    st.markdown("#### 📊 Distribuição de acertos")
    fig, ax = plt.subplots()
    df_comp["acertos"].value_counts().sort_index().plot(kind="bar", ax=ax, color="#4ade80")
    ax.set_xlabel("Acertos")
    ax.set_ylabel("Quantidade de palpites")
    ax.set_title("Distribuição de acertos dos palpites LS16")
    st.pyplot(fig)

    # Média móvel de acertos (últimos 30)
    st.markdown("#### 📈 Média móvel (últimos 30 palpites)")
    rolling_mean = df_comp["acertos"].rolling(window=30).mean()
    fig, ax = plt.subplots()
    ax.plot(rolling_mean, color="#22c55e", linewidth=2)
    ax.set_xlabel("Execuções recentes")
    ax.set_ylabel("Média de acertos")
    ax.set_title("Tendência de performance LS16")
    st.pyplot(fig)

    st.metric("🎯 Média geral de acertos", f"{df_comp['acertos'].mean():.2f}")

# ============================================================
# 📂 Exportação
# ============================================================
with st.expander("📥 Exportar dados"):
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Baixar CSV completo", csv_data, "telemetria_ls16.csv", "text/csv")

st.markdown("<hr>", unsafe_allow_html=True)
st.caption("© FaixaBet — Inteligência aplicada à sorte.")
