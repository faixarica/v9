from datetime import datetime
from sqlalchemy import text
from db import Session
from service.email_brevo import enviar_email_brevo  # ajuste o import se necessário

# TEMPLATE DA BREVO (CONFIRMAR ID)
TEMPLATE_RESUMO_MENSAL = 12  # <<< TROQUE PELO SEU ID REAL


def gerar_relatorio_mensal(db, user_id: int, mes: int, ano: int):
    """
    Gera dados básicos do relatório mensal do usuário.
    (sem acertos por enquanto)
    """

    total_lf = db.execute(text("""
        SELECT COUNT(*) FROM palpites
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    total_ms = db.execute(text("""
        SELECT COUNT(*) FROM palpites_m
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    return {
        "total_palpites": total_lf + total_ms,
        "lotofacil": total_lf,
        "megasena": total_ms
    }


def enviar_email_usuario(user_id: int, mes: int):
    """
    Envia e-mail REAL via Brevo com resumo mensal do usuário.
    """

    ano = datetime.now().year

    with Session() as db:
        user = db.execute(text("""
            SELECT usuario, email
            FROM usuarios
            WHERE id = :uid
        """), {"uid": user_id}).fetchone()

        if not user:
            raise RuntimeError("Usuário não encontrado")

        if not user.email:
            raise RuntimeError("Usuário sem e-mail cadastrado")

        relatorio = gerar_relatorio_mensal(db, user_id, mes, ano)

    # -----------------------------
    # PARAMS PARA TEMPLATE BREVO
    # -----------------------------
    params = {
        "NOME_USUARIO": user.usuario,
        "MES_REFERENCIA": f"{mes:02d}/{ano}",
        "TOTAL_PALPITES": relatorio["total_palpites"],
        "PALPITES_LOTOFACIL": relatorio["lotofacil"],
        "PALPITES_MEGASENA": relatorio["megasena"],
    }

    # -----------------------------
    # ENVIO REAL
    # -----------------------------
    return enviar_email_brevo(
        destinatario_email=user.email,
        destinatario_nome=user.usuario,
        template_id=TEMPLATE_RESUMO_MENSAL,
        params=params
    )
