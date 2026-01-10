"""
Relatório de Performance / Estatísticas – fAIxaBet

Autor: Francisco Ferreira Jr.
Criado em: 02/01/2026

Baseado na tabela oficial: palpites_hits
"""

import os
from datetime import datetime
from sqlalchemy import text
from db import Session

from app.services.email_service import enviar_email_brevo


# ============================================================
# CONFIG
# ============================================================

TEMPLATE_ESTATISTICAS = 13  # ID do template no Brevo


# ============================================================
# CÁLCULO DE ESTATÍSTICAS
# ============================================================

def gerar_estatisticas_usuario(db, user_id: int, mes: int, ano: int) -> dict:
    """
    Calcula estatísticas reais do usuário usando palpites_hits.
    """

    # -------------------------
    # Palpites gerados
    # -------------------------
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

    total_palpites = total_lf + total_ms

    # -------------------------
    # Acertos consolidados
    # -------------------------
    acertos_lf = db.execute(text("""
        SELECT COUNT(*) FROM palpites_hits
        WHERE id_usuario = :uid
          AND loteria = 'LF'
          AND acertos >= 11
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    acertos_ms = db.execute(text("""
        SELECT COUNT(*) FROM palpites_hits
        WHERE id_usuario = :uid
          AND loteria = 'MS'
          AND acertos >= 2
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(YEAR FROM data) = :ano
    """), {"uid": user_id, "mes": mes, "ano": ano}).scalar() or 0

    total_acertos = acertos_lf + acertos_ms

    # -------------------------
    # Eficiência (%)
    # -------------------------
    if total_palpites > 0:
        eficiencia = round((total_acertos / total_palpites) * 100)
    else:
        eficiencia = 0

    return {
        "total_palpites": total_palpites,
        "palpites_validos": total_palpites,
        "palpites_com_acerto": total_acertos,
        "acertos_lotofacil": acertos_lf,
        "acertos_megasena": acertos_ms,
        "percentual_eficiencia": eficiencia
    }


# ============================================================
# ENVIO DE E-MAIL
# ============================================================

def enviar_email_estatisticas_usuario(
    user_id: int,
    mes: int,
    ano: int
):
    """
    Envia e-mail via Brevo com estatísticas reais.
    """

    if mes < 1 or mes > 12:
        raise ValueError("Mês inválido")

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

        stats = gerar_estatisticas_usuario(db, user_id, mes, ano)

    params = {
        "NOME_USUARIO": user.usuario,
        "MES_REFERENCIA": f"{mes:02d}/{ano}",

        "TOTAL_PALPITES": stats["total_palpites"],
        "PALPITES_VALIDOS": stats["palpites_validos"],
        "PALPITES_COM_ACERTO": stats["palpites_com_acerto"],

        "ACERTOS_LOTOFACIL": stats["acertos_lotofacil"],
        "ACERTOS_MEGASENA": stats["acertos_megasena"],

        "PERCENTUAL_EFICIENCIA": stats["percentual_eficiencia"],

        "APP_URL": os.getenv(
            "APP_BASE_URL",
            "https://faixabet9.streamlit.app"
        ),
        "ANO_ATUAL": datetime.now().year
    }

    return enviar_email_brevo(
        destinatario_email=user.email,
        destinatario_nome=user.usuario,
        template_id=TEMPLATE_ESTATISTICAS,
        params=params
    )
