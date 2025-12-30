# acertos_dia_app.py — versão Streamlit (FaixaBet)
# Mostra acertos do dia com faixa 11–15, nome do usuário e data formatada.

import streamlit as st
from datetime import date
from sqlalchemy import text
from db import Session


# -----------------------------------------------------
# 🔹 Funções auxiliares
# -----------------------------------------------------
def sql_date_expr(alias, col):
    """Normaliza campos de data em diferentes formatos para comparação."""
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


def fetch_resultado(data_ref):
    """Busca resultado oficial da data informada."""
    db = Session()
    sql = f"""
    SELECT concurso, {sql_date_expr('r','data')} AS data_norm,
           n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15
    FROM resultados_oficiais r
    WHERE {sql_date_expr('r','data')} = :d
    ORDER BY concurso DESC LIMIT 1
    """
    row = db.execute(text(sql), {"d": data_ref.isoformat()}).fetchone()
    db.close()
    if not row:
        return None
    nums = [row.n1,row.n2,row.n3,row.n4,row.n5,row.n6,row.n7,row.n8,row.n9,row.n10,
            row.n11,row.n12,row.n13,row.n14,row.n15]
    return {"concurso": row.concurso, "data": row.data_norm, "numeros": nums}


def fetch_usuario_nome(id_usuario):
    """Retorna o nome do usuário pelo ID."""
    if not id_usuario:
        return None
    db = Session()
    row = db.execute(text("SELECT usuario FROM usuarios WHERE id = :uid"), {"uid": id_usuario}).fetchone()
    db.close()
    return row.usuario if row else None


# -----------------------------------------------------
# 🔹 Função principal Streamlit
# -----------------------------------------------------
def main():
    st.set_page_config(page_title="Acertos por Dia - FaixaBet", layout="centered")
    st.title("🎯 Acertos por Dia")

    # Data do sorteio (dd/mm/yyyy)
    data_escolhida = st.date_input("📅 Data do sorteio", date.today(), format="DD/MM/YYYY")

    tipo = st.selectbox("👤 Tipo de usuário", ["admin", "user"])
    # Deixar campo livre mas numérico
    user_id = st.text_input("🆔 ID do usuário (opcional)", value="", placeholder="Digite apenas números...")

    # Garantir que só contenha dígitos (não dá erro)
    user_id = int(user_id) if user_id.strip().isdigit() else None

    if st.button("🔎 Verificar acertos"):
        res = fetch_resultado(data_escolhida)
        if not res:
            st.warning("Nenhum resultado oficial encontrado.")
            return

        db = Session()
        sql = f"""
        SELECT p.id, p.id_usuario, p.numeros, p.modelo, {sql_date_expr('p','data')} AS data_norm
        FROM palpites p
        WHERE {sql_date_expr('p','data')} = :d
        """
        params = {"d": data_escolhida.isoformat()}
        if tipo != "admin" and user_id:
            sql += " AND p.id_usuario = :uid"
            params["uid"] = user_id

        rows = db.execute(text(sql + " ORDER BY p.id DESC"), params).fetchall()
        db.close()

        if not rows:
            st.warning("Nenhum palpite encontrado para esta data.")
            return

        nums_oficiais = set(res["numeros"])
        faixa = {i: 0 for i in range(11, 16)}
        total = len(rows)
        vencedores = 0

        st.markdown(f"### 📊 {total} palpites gerados em {data_escolhida.strftime('%d/%m/%Y')}")
        st.markdown(f"**Concurso #{res['concurso']}** — Números sorteados: `{', '.join(f'{n:02d}' for n in sorted(nums_oficiais))}`")

        for r in rows:
            nums = [int(x) for x in str(r.numeros).split(",") if x.strip().isdigit()]
            acertos = nums_oficiais.intersection(nums)
            qtd = len(acertos)
            if 11 <= qtd <= 15:
                faixa[qtd] += 1
                vencedores += 1
                nome = fetch_usuario_nome(r.id_usuario)
                nome_str = nome if nome else f"Usuário {r.id_usuario}"

                st.markdown(f"""
                <div style='border:1px solid #ccc; border-radius:10px; padding:8px; margin-bottom:6px;'>
                    <b>Palpite #{r.id}</b> — {nome_str} | Modelo: {r.modelo}<br>
                    🎯 <b>{qtd}</b> acertos<br>
                    <small>{', '.join(f"{n:02d}" for n in sorted(nums))}</small><br>
                    <small style='color:green;'>Acertos: {', '.join(f"{n:02d}" for n in sorted(acertos))}</small>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("### 🎯 Resumo de acertos")
        for i in range(15, 10, -1):
            st.write(f"**{i} acertos:** {faixa[i]}")

        if vencedores == 0:
            st.info("Nenhum palpite com 11–15 acertos encontrado.")


# -----------------------------------------------------
# 🔹 Execução
# -----------------------------------------------------
if __name__ == "__main__":
    main()
