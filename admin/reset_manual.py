import os
import secrets
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

APP_BASE_URL = os.getenv("APP_BASE_URL", "https://faixabet.com")


def gerar_token_reset() -> str:
    return secrets.token_urlsafe(32)


def salvar_token_reset(db, user_id: int, token: str, minutos_validade: int = 30):
    expira_em = datetime.utcnow() + timedelta(minutes=minutos_validade)

    sql = text("""
        UPDATE usuarios
        SET
            reset_token = :token,
            reset_token_expira = :expira_em,
            forcar_reset = true
        WHERE id = :user_id
    """)

    db.execute(sql, {
        "token": token,
        "expira_em": expira_em,
        "user_id": user_id
    })
    db.commit()


def gerar_link_reset(token: str) -> str:
    return f"{APP_BASE_URL}/?reset=1&token={token}"
