import os
import requests
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -------------------------------
# Carregar .env explicitamente
# (seu .env está em /v9/app/.env)
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../app
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "fAIxaBet")



SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)


def _saudacao(nome_usuario: str | None) -> str:
    nome = (nome_usuario or "").strip()
    if nome:
        return f"Olá, {nome}! 👋"
    return "Olá! 👋"


def enviar_email_reset(
    destinatario: str,
    link: str,
    nome_usuario: str | None = None,
    minutos_validade: int = 30
):
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY não configurada")
    if not SENDER_EMAIL:
        raise RuntimeError("BREVO_SENDER_EMAIL não configurada")
    if not destinatario:
        raise RuntimeError("Destinatário vazio")
    if not link:
        raise RuntimeError("Link vazio")

    titulo = _saudacao(nome_usuario)

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": destinatario}],
        "subject": "🔐 Redefinição de senha – fAIxaBet",
        "htmlContent": f"""
        <html>
        <body style="font-family: Arial, Helvetica, sans-serif; background:#f7f7f7; padding:20px;">
          <div style="max-width:600px;margin:auto;background:#ffffff;padding:24px;border-radius:10px;">
            <h2 style="color:#16a34a;margin-top:0;">{titulo}</h2>

            <p>Recebemos uma solicitação para redefinir a senha da sua conta na <strong>fAIxaBet</strong>.</p>

            <p style="margin:24px 0; text-align:center;">
              <a href="{link}" style="background:#16a34a;color:#fff;padding:14px 22px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">
                Redefinir minha senha
              </a>
            </p>

            <p> Este link é válido por <strong>{minutos_validade} minutos</strong>. Após esse período, solicite novamente.</p>

            <hr style="margin:22px 0;">

            <p><strong>Passo a passo para você redefinir sua nova senha:</strong></p>
            <ol>
              <li>Ao clicar no botão verde acima.</li>
              <li>Você será redirecionado para a página da aplicação fAIxaBet.</li>
              <li>A pagina  Redefinir senha será carregada. </li>
              <li>Informe sua nova senha.</li>
              <li>Confirme sua nova senha e clique no salvar nova.senha.</li>
            </ol>
            <p style="color:#555;">
              🔒 Se você <strong>não solicitou</strong> esta redefinição, ignore este e-mail.
              Nenhuma alteração será feita sem a confirmação pelo link.
            </p>

            <hr style="margin:22px 0;">
            <p style="font-size:12px;color:#777;margin-bottom:0;">
              fAIxaBet® — Inteligência aplicada à loterias<br>
              Este é um e-mail automático. Não responda.
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

    r = requests.post(url, json=payload, headers=headers, timeout=10)

    if r.status_code not in (200, 201, 202):
        logging.error(f"Erro Brevo {r.status_code}: {r.text}")
        return False



def enviar_email(destinatario: str, assunto: str, corpo: str) -> None:
    """
    Envia e-mail padrão FaixaBet (usado em recuperação de senha,
    notificações de acertos, alertas etc.)
    """
    msg = MIMEMultipart()
    msg["From"] = f"FaixaBet <{EMAIL_FROM}>"
    msg["To"] = destinatario
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


BREVO_URL = "https://api.brevo.com/v3/smtp/email"

def enviar_email_brevo(
    destinatario_email: str,
    destinatario_nome: str | None,
    template_id: int,
    params: dict
):
    """
    Envio genérico via Brevo usando TEMPLATE (templateId + params).
    Serve para: acertos, alertas, campanhas transacionais, etc.
    """

    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY não configurada")
    if not SENDER_EMAIL:
        raise RuntimeError("BREVO_SENDER_EMAIL não configurada")
    if not template_id:
        raise RuntimeError("template_id inválido")
    if not destinatario_email:
        raise RuntimeError("destinatario_email vazio")

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{
            "email": destinatario_email,
            "name": (destinatario_nome or "").strip() or None
        }],
        "templateId": int(template_id),
        "params": params or {}
    }

    r = requests.post(BREVO_URL, json=payload, headers=headers, timeout=15)

    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"Erro Brevo {r.status_code}: {r.text}")

    # opcional: retornar json p/ log
    try:
        return r.json()
    except Exception:
        return {"status_code": r.status_code, "text": r.text}
