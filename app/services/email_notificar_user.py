from datetime import datetime
from sqlalchemy import text
from db import Session
from app.services.email_service import enviar_email_brevo

TEMPLATE_RESUMO_MENSAL = 4  # <<< TROQUE PELO SEU ID REAL


def gerar_relatorio_mensal(db, user_id: int, mes: int, ano: int):
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


def enviar_email_usuario(user_id: int, mes: int, ano: int | None = None):
    """
    Envia e-mail REAL via Brevo com resumo mensal do usuário.
    """
    if ano is None:
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

    params = {
        "NOME_USUARIO": user.usuario,
        "MES_REFERENCIA": f"{mes:02d}/{ano}",
        "TOTAL_PALPITES": relatorio["total_palpites"],
        "PALPITES_LOTOFACIL": relatorio["lotofacil"],
        "PALPITES_MEGASENA": relatorio["megasena"],
    }

    return enviar_email_brevo(
        destinatario_email=user.email,
        destinatario_nome=user.usuario,
        template_id=TEMPLATE_RESUMO_MENSAL,
        params=params
    )
