# app/services/email_reset_manual.py
import os
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "fAIxaBet")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _saudacao(nome_usuario: str | None) -> str:
    nome = (nome_usuario or "").strip()
    return f"Olá, {nome}! 👋" if nome else "Olá! 👋"


def enviar_reset_manual(
    nome_usuario: str,
    email_usuario: str,
    link_reset: str,
    minutos_validade: int = 30
) -> bool:

    if not BREVO_API_KEY:
        raise RuntimeError("❌ BREVO_API_KEY não configurada")
    if not SENDER_EMAIL:
        raise RuntimeError("❌ BREVO_SENDER_EMAIL não configurada")

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": email_usuario, "name": nome_usuario}],
        "subject": "🔐 Redefinição de senha – fAIxaBet",
        "htmlContent": f"""
        <html>
        <body style="font-family:Arial;background:#f7f7f7;padding:20px;">
          <div style="max-width:600px;margin:auto;background:#fff;padding:24px;border-radius:10px;">
            <h2 style="color:#16a34a">{_saudacao(nome_usuario)}</h2>
            <p>Solicitação manual de redefinição de senha.</p>

            <p style="text-align:center;margin:24px 0;">
              <a href="{link_reset}"
                 style="background:#16a34a;color:#fff;padding:14px 22px;
                        text-decoration:none;border-radius:8px;font-weight:bold;">
                Redefinir minha senha
              </a>
            </p>

            <p>⏱ Link válido por {minutos_validade} minutos.</p>

            <hr>
            <p style="font-size:12px;color:#777;">
              fAIxaBet® — Envio manual pelo suporte
            </p>
          </div>
        </body>
        </html>
        """
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    r = requests.post(BREVO_URL, json=payload, headers=headers, timeout=15)

    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"❌ Erro Brevo {r.status_code}: {r.text}")

    return True
