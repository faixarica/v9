import streamlit as st
from datetime import date, timedelta
from sqlalchemy import text

from app.db import Session
from app.services.email_service import enviar_email_brevo

LOT_CONFIG = {
    "Lotofácil": {
        "tabela_palpites": "palpites",
        "tabela_resultados": "resultados_oficiais",
        "resultado_data_tipo": "text",   # 👈 IMPORTANTE
        "col_data_palpites": "data_norm",
        "min_acertos_default": 11,
        "template_brevo": 7,
        "total_dezenas": 15,
    },
    "Mega-Sena": {
        "tabela_palpites": "palpites_m",
        "tabela_resultados": "resultados_oficiais_m",
        "resultado_data_tipo": "date",   # 👈 IMPORTANTE
        "col_data_palpites": "data_norm",
        "min_acertos_default": 4,
        "template_brevo": 8,
        "total_dezenas": 6,
    }
}


def tela_notificacoes_acertos(loteria_atual_sidebar: str | None = None):
    st.subheader("📢 Notificações de Acertos")

    # 🔽 Seleção explícita da loteria (controle total)
    loteria = st.selectbox(
        "🎰 Loteria",
        options=list(LOT_CONFIG.keys()),
        index=list(LOT_CONFIG.keys()).index(loteria_atual_sidebar)
        if loteria_atual_sidebar in LOT_CONFIG else 0
    )

    cfg = LOT_CONFIG[loteria]

    col1, col2, col3 = st.columns(3)

    data_concurso = col1.date_input(
        "📅 Data do concurso",
        value=date.today() - timedelta(days=1)
    )

    min_acertos = col2.number_input(
        "🎯 Acertos mínimos",
        min_value=1,
        max_value=cfg["total_dezenas"],
        value=cfg["min_acertos_default"]
    )

    dry_run = col3.checkbox(
        "🧪 Modo simulação (não envia e-mail)",
        value=True
    )

    st.divider()

    if st.button("🔍 Simular notificações"):
        executar_notificacoes(
            loteria=loteria,
            cfg=cfg,
            data_concurso=data_concurso,
            min_acertos=min_acertos,
            dry_run=True
        )

    st.divider()

    if st.button("🚀 ENVIAR notificações", type="primary"):
        st.warning("⚠️ Envio REAL de e-mails.")
        executar_notificacoes(
            loteria=loteria,
            cfg=cfg,
            data_concurso=data_concurso,
            min_acertos=min_acertos,
            dry_run=False
        )


# ======================================================
# LÓGICA (a mesma que você já tinha, só controlada)
# ======================================================
def executar_notificacoes(
    loteria: str,
    cfg: dict,
    data_concurso: date,
    min_acertos: int,
    dry_run: bool
):
    db = Session()

    try:
        # --------------------------------------------------
        # 1) RESULTADO OFICIAL (TEXT misto → CASE)
        # --------------------------------------------------
        if cfg["resultado_data_tipo"] == "text":
            # Lotofácil (data TEXT misto)
            res = db.execute(text(f"""
                SELECT *
                FROM {cfg["tabela_resultados"]}
                WHERE
                    CASE
                        WHEN data ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$'
                            THEN to_date(data, 'YYYY-MM-DD')
                        WHEN data ~ '^\\d{{2}}/\\d{{2}}/\\d{{4}}$'
                            THEN to_date(data, 'DD/MM/YYYY')
                        ELSE NULL
                    END = :data
            """), {"data": data_concurso}).fetchone()
        else:
            # Mega-Sena (data DATE)
            res = db.execute(text(f"""
                SELECT *
                FROM {cfg["tabela_resultados"]}
                WHERE data = :data
            """), {"data": data_concurso}).fetchone()


        if not res:
            st.error("❌ Resultado oficial não encontrado.")
            return

        # ignora id/data → só dezenas
        resultado = set(res[2:2 + cfg["total_dezenas"]])

        # --------------------------------------------------
        # 2) PALPITES (usa data_norm DATE)
        # --------------------------------------------------
        palpites = db.execute(text(f"""
            SELECT
                p.id,
                p.id_usuario,
                p.numeros,
                u.email,
                u.nome_completo
            FROM {cfg["tabela_palpites"]} p
            JOIN usuarios u ON u.id = p.id_usuario
            WHERE p.{cfg["col_data_palpites"]} = :data
              AND NOT EXISTS (
                  SELECT 1
                  FROM notificacoes_palpite n
                  WHERE n.id_palpite = p.id
              )
        """), {"data": data_concurso}).fetchall()

        if not palpites:
            st.info("Nenhum palpite elegível.")
            return

        enviados = 0
        st.markdown("### 📋 Prévia")

        for p in palpites:
            numeros = {int(x) for x in p.numeros.split(",")}
            acertos = len(resultado.intersection(numeros))

            if acertos < min_acertos:
                continue

            st.write(f" {p.id_usuario} - {p.nome_completo} — 🎯 {acertos} acertos")

            if not dry_run:
                enviar_email_brevo(
                    destinatario_email=p.email,
                    destinatario_nome=p.nome_completo,
                    template_id=cfg["template_brevo"],
                    params={
                        "NOME": p.nome_completo,
                        "DATA": data_concurso.strftime("%d/%m/%Y"),
                        "ACERTOS": acertos,
                        "LOTERIA": loteria
                    }
                )

                db.execute(text("""
                    INSERT INTO notificacoes_palpite
                        (id_palpite, id_usuario, acertos, canal)
                    VALUES
                        (:pid, :uid, :acertos, :canal)
                """), {
                    "pid": p.id,
                    "uid": p.id_usuario,
                    "acertos": acertos,
                    "canal": "email"
                })

                enviados += 1

        if not dry_run:
            db.commit()
            st.success(f"✅ {enviados} notificações enviadas!")
        else:
            st.info("🧪 Simulação concluída (nenhum e-mail enviado).")

    except Exception as e:
        db.rollback()
        st.error(f"Erro ao processar notificações: {e}")

    finally:
        db.close()
