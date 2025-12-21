# auth.py
# =========================================
# Autenticação e Segurança – FaixaBet V9
# =========================================

from sqlalchemy import text
from passlib.hash import pbkdf2_sha256
import bcrypt

import secrets
from datetime import datetime, timedelta
from sqlalchemy import text

def gerar_token_recuperacao(user_id, db):
    token = secrets.token_urlsafe(32)
    validade = datetime.utcnow() + timedelta(hours=1)

    db.execute(text("""
        INSERT INTO password_resets (user_id, token, expira_em)
        VALUES (:uid, :token, :exp)
        ON CONFLICT (user_id) DO UPDATE
        SET token = EXCLUDED.token,
            expira_em = EXCLUDED.expira_em
    """), {"uid": user_id, "token": token, "exp": validade})

    db.commit()
    return token


def validar_token_recuperacao(token, db):
    row = db.execute(text("""
        SELECT user_id
        FROM password_resets
        WHERE token = :token
          AND expira_em >= NOW()
    """), {"token": token}).fetchone()

    return row[0] if row else None


def consumir_token_recuperacao(user_id, db):
    db.execute(
        text("DELETE FROM password_resets WHERE user_id = :uid"),
        {"uid": user_id}
    )
    db.commit()


# -------------------------------------------------
# REGISTRA LOGIN (telemetria simples)
# -------------------------------------------------
def registrar_login(user_id, db=None):
    if db is None:
        return

    try:
        db.execute(
            text("""
                INSERT INTO logins (id_usuario)
                VALUES (:uid)
            """),
            {"uid": user_id}
        )
        db.commit()
    except Exception:
        db.rollback()


# -------------------------------------------------
# VERIFICA SENHA (bcrypt + PBKDF2 legado)
# -------------------------------------------------
def verificar_senha(senha_digitada, senha_hash, db=None, user_id=None):
    """
    - bcrypt (padrão novo)
    - PBKDF2-SHA256 (legado)
    - migração automática PBKDF2 -> bcrypt
    """

    if not senha_digitada or not senha_hash:
        return False

    senha_hash_clean = (
        senha_hash.strip()
        .replace("\n", "")
        .replace("\r", "")
    )

    # ===============================
    # PBKDF2 (LEGADO)
    # ===============================
    if senha_hash_clean.startswith("pbkdf2_sha256$") or senha_hash_clean.startswith("$pbkdf2-sha256$"):
        try:
            valido = pbkdf2_sha256.verify(
                senha_digitada,
                senha_hash_clean
            )

            # 🔁 Migração automática para bcrypt
            if valido and db is not None and user_id is not None:
                novo_hash = bcrypt.hashpw(
                    senha_digitada.encode(),
                    bcrypt.gensalt(12)
                ).decode()

                db.execute(
                    text("""
                        UPDATE usuarios
                        SET senha = :senha
                        WHERE id = :uid
                    """),
                    {
                        "senha": novo_hash,
                        "uid": user_id
                    }
                )
                db.commit()

            return valido

        except Exception:
            return False

    # ===============================
    # bcrypt (PADRÃO NOVO)
    # ===============================
    if senha_hash_clean.startswith("$2a$") or senha_hash_clean.startswith("$2b$"):
        try:
            return bcrypt.checkpw(
                senha_digitada.encode(),
                senha_hash_clean.encode()
            )
        except Exception:
            return False

    return False

# -------------------------------------------------
# LOGOUT (encerra sessão do Streamlit)
# -------------------------------------------------
def logout():
    """
    Limpa a sessão e força voltar ao login.
    Use em qualquer botão/menu: logout()
    """
    import streamlit as st

    # mantém consistência de chaves usadas no app
    for k in [
        "logged_in",
        "usuario",
        "admin",
        "recover_step",
        "token_reset",
        "last_recover_message",
    ]:
        if k in st.session_state:
            del st.session_state[k]

    st.session_state.logged_in = False
    st.rerun()

def registrar_tentativa_login(
    usuario,
    email=None,
    sucesso=False,
    motivo=None,
    ip_address=None,
    user_agent=None,
    db=None
):
    if db is None:
        return

    from sqlalchemy import text

    db.execute(
        text("""
            INSERT INTO login_attempts
            (usuario, email, ip_address, user_agent, sucesso, motivo)
            VALUES (:usuario, :email, :ip, :ua, :sucesso, :motivo)
        """),
        {
            "usuario": usuario,
            "email": email,
            "ip": ip_address,
            "ua": user_agent,
            "sucesso": sucesso,
            "motivo": motivo
        }
    )
    db.commit()

