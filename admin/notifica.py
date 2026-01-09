
import streamlit as st
import smtplib

from datetime import date, timedelta
from sqlalchemy import text
from db import Session

import streamlit as st
from datetime import date, timedelta
from sqlalchemy import text

from db import Session
from utils.email_service import enviar_email


def processar_notificacoes_acertos():
    """
    Verifica palpites do dia anterior, compara com resultado oficial
    e envia notificações automáticas aos usuários.
    """

    st.markdown("### 🚀 Processar Notificações de Acertos")

    db = Session()
    ontem = date.today() - timedelta(days=1)

    try:
        # 1️⃣ Resultado oficial
        res = db.execute(text("""
            SELECT n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,
                   n11,n12,n13,n14,n15
            FROM resultados_oficiais
            WHERE data = :data
        """), {"data": ontem}).fetchone()

        if not res:
            st.warning(f"Nenhum resultado oficial encontrado para {ontem}.")
            return

        resultado = set(res)

        # 2️⃣ Palpites não notificados
        palpites = db.execute(text("""
            SELECT
                p.id,
                p.id_usuario,
                p.numeros,
                u.email,
                u.nome
            FROM palpites p
            JOIN usuarios u ON u.id = p.id_usuario
            WHERE DATE(p.data) = :data
              AND NOT EXISTS (
                  SELECT 1
                  FROM notificacoes_palpite n
                  WHERE n.id_palpite = p.id
              )
        """), {"data": ontem}).fetchall()

        if not palpites:
            st.info("Nenhum palpite pendente para notificação.")
            return

        enviados = 0

        for palpite in palpites:
            try:
                numeros = {int(x) for x in palpite.numeros.split(",")}
                acertos = len(resultado.intersection(numeros))

                # Mensagem base
                msg = (
                    f"Olá, {palpite.nome}!\n\n"
                    f"📅 Concurso: {ontem.strftime('%d/%m/%Y')}\n"
                    f"🎯 Seus acertos: {acertos}\n\n"
                )

                # Só notifica por e-mail se >= 11
                if acertos >= 11:
                    msg += (
                        "🎉 Parabéns!\n"
                        "Seu palpite foi premiado na Lotofácil!\n\n"
                        "Continue acompanhando seus resultados na FaixaBet 🍀"
                    )

                    enviar_email(
                        palpite.email,
                        "FaixaBet – Resultado do seu palpite",
                        msg
                    )
                    canal = "email"
                    enviados += 1
                else:
                    # Não envia e-mail, mas registra como processado
                    canal = "interno"

                # 3️⃣ Registrar notificação (sempre)
                db.execute(text("""
                    INSERT INTO notificacoes_palpite
                        (id_palpite, id_usuario, acertos, canal, mensagem)
                    VALUES
                        (:pid, :uid, :acertos, :canal, :msg)
                """), {
                    "pid": palpite.id,
                    "uid": palpite.id_usuario,
                    "acertos": acertos,
                    "canal": canal,
                    "msg": msg
                })

            except Exception as e:
                # erro isolado NÃO quebra o lote
                st.error(f"Erro no palpite {palpite.id}: {e}")

        db.commit()
        st.success(f"✅ {enviados} notificações enviadas com sucesso!")

    except Exception as e:
        db.rollback()
        st.error(f"Erro geral ao processar notificações: {e}")

    finally:
        db.close()


def enviar_email(destinatario, assunto, corpo):
    """Função simples para envio de e-mail (pode trocar por SendGrid, SMTP etc.)."""
    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login("faixaricaa@gmail.com", "senha_app")
        mensagem = f"Subject: {assunto}\n\n{corpo}"
        servidor.sendmail("faixaricaa@gmail.com", destinatario, mensagem)
        servidor.quit()
    except Exception as e:
        print(f"Erro ao enviar e-mail para {destinatario}: {e}")
