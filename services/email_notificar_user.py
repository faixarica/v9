import os
from datetime import datetime
from sqlalchemy import text
from db import Session

# Serviço REAL de e-mail (Brevo)
from services.email_service import enviar_email_brevo


# ============================================================
# CONFIG
# ============================================================

DEBUG_EMAIL_RELATORIO = True

# ⚠️ CONFIRME ESSE ID NO PAINEL BREVO
TEMPLATE_RESUMO_MENSAL = 5


# ============================================================
# RELATÓRIO MENSAL
# ============================================================

def gerar_relatorio_mensal(db, user_id: int, mes: int, ano: int) -> dict:
    """
    Gera resumo mensal de palpites do usuário.
    (sem acertos por enquanto)
    """

    total_lf = db.execute(text("""
        SELECT COUNT(*)
        FROM palpites
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {
        "uid": user_id,
        "mes": mes,
        "ano": ano
    }).scalar() or 0

    total_ms = db.execute(text("""
        SELECT COUNT(*)
        FROM palpites_m
        WHERE id_usuario = :uid
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {
        "uid": user_id,
        "mes": mes,
        "ano": ano
    }).scalar() or 0

    return {
        "total_palpites": total_lf + total_ms,
        "lotofacil": total_lf,
        "megasena": total_ms
    }


# ============================================================
# ENVIO DE E-MAIL (BREVO)
# ============================================================

def enviar_email_usuario(user_id: int, mes: int, ano: int):
    """
    Envia e-mail REAL via Brevo com resumo mensal do usuário.
    Retorna a resposta da Brevo ou levanta exceção.
    """
    if ano < 2000 or ano > datetime.now().year:
        raise ValueError("Ano inválido para envio de relatório")

    if not mes or mes < 1 or mes > 12:
        raise ValueError("Mês inválido para envio de e-mail")


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

    # --------------------------------------------------------
    # PARAMS PARA TEMPLATE BREVO
    # --------------------------------------------------------
    params = {
        "NOME_USUARIO": user.usuario,
        "MES_REFERENCIA": f"{mes:02d}/{ano}",
        "TOTAL_PALPITES": relatorio["total_palpites"],
        "PALPITES_LOTOFACIL": relatorio["lotofacil"],
        "PALPITES_MEGASENA": relatorio["megasena"],
        "APP_URL": os.getenv("APP_BASE_URL")
    }


    if DEBUG_EMAIL_RELATORIO:
        print("\n📧 ================= EMAIL RESUMO MENSAL =================")
        print("📧 Usuário:", user.usuario)
        print("📧 Email:", user.email)
        print("📧 Template ID:", TEMPLATE_RESUMO_MENSAL)
        print("📧 Mês/Ano:", f"{mes:02d}/{ano}")
        print("📧 Params enviados:", params)
        print("📧 ======================================================")

    # --------------------------------------------------------
    # ENVIO REAL (COM DEBUG DE RETORNO)
    # --------------------------------------------------------
    try:
        resp = enviar_email_brevo(
            destinatario_email=user.email,
            destinatario_nome=user.usuario,
            template_id=TEMPLATE_RESUMO_MENSAL,
            params=params
        )

        if DEBUG_EMAIL_RELATORIO:
            print("📧 [DEBUG] Resposta da Brevo:", resp)
            print("📧 [DEBUG] Envio concluído com sucesso\n")

        return resp

    except Exception as e:
        print("\n❌ [EMAIL ERRO] Falha ao enviar resumo mensal")
        print("❌ Usuário:", user.usuario)
        print("❌ Email:", user.email)
        print("❌ Template ID:", TEMPLATE_RESUMO_MENSAL)
        print("❌ Params:", params)
        print("❌ Erro:", str(e), "\n")
        raise
