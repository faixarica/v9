# app/main.py
# autor: FFerreira
# descrição: Aplicação principal Streamlit da fAIxaBet V9
# Adicionar o path de FaixaBet no sys.path (antes de qualquer import)

import streamlit as st

st.set_page_config(
    page_title="FaixaBet",
    layout="wide"
)

st.write("🔄 Inicializando aplicação...")

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # C:\Faixabet\V9
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))



# Agora sim, importar as bibliotecas
import os
import secrets
import smtplib
import requests
import base64
import streamlit.components.v1 as components
import pandas as pds
import hashlib

from passlib.hash import pbkdf2_sha256
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import Session
from app.dashboard import mostrar_dashboard

from app.auth import verificar_senha, registrar_login, logout
from app.services.email_service import enviar_email_reset
from app.notificacoes.notifica import tela_notificacoes_acertos

st.write("BOOT OK - chegou no main")


MAX_LOGIN_ATTEMPTS = 5
LOGIN_BLOCK_MINUTES = 10


def login_bloqueado(usuario):
    bloqueio = st.session_state.get("login_block", {})
    info = bloqueio.get(usuario)

    if not info:
        return False

    until = info.get("until")
    if until and datetime.utcnow() < until:
        return True

    # desbloqueia automaticamente
    bloqueio.pop(usuario, None)
    st.session_state.login_block = bloqueio
    return False

def registrar_falha_login(usuario):
    tentativas = st.session_state.get("login_attempts", {})
    bloqueio = st.session_state.get("login_block", {})

    tentativas[usuario] = tentativas.get(usuario, 0) + 1

    if tentativas[usuario] >= MAX_LOGIN_ATTEMPTS:
        bloqueio[usuario] = {
            "until": datetime.utcnow() + timedelta(minutes=LOGIN_BLOCK_MINUTES)
        }
        tentativas[usuario] = 0  # reseta contador

    st.session_state.login_attempts = tentativas
    st.session_state.login_block = bloqueio

def limpar_falhas_login(usuario):
    st.session_state.get("login_attempts", {}).pop(usuario, None)
    st.session_state.get("login_block", {}).pop(usuario, None)

# ========= PALPITES (LEGACY) =========
from app.palpites_legacy import (
    gerar_palpite_ui,
    historico_palpites,
    validar_palpite
)


if "recover_step" not in st.session_state:
    st.session_state.recover_step = 0

if "recover_email" not in st.session_state:
    st.session_state.recover_email = None

from app.auth import logout
from app.perfil import editar_perfil
from app.financeiro import exibir_aba_financeiro
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qs

# -------------------- CONFIG (precisa ser o PRIMEIRO comando Streamlit) --------------------
st.set_page_config(
    page_title="fAIxaBet",
    page_icon="🍀",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ================== ROUTER DE RESET DE SENHA ==================
# =====================================================
# ROUTER: RESET VIA LINK (?reset=1&token=...)
# =====================================================
query = st.query_params
reset_flag = query.get("reset")
token = query.get("token")

if reset_flag == "1" and token:
    st.subheader("🔁 Redefinir senha")

    db = Session()
    try:
        row = db.execute(text("""
            SELECT user_id
            FROM password_resets
            WHERE token = :token
              AND expira_em >= NOW()
            LIMIT 1
        """), {"token": token}).fetchone()

        if not row:
            st.error("❌ Link inválido ou expirado. Solicite novamente.")
            st.stop()

        user_id = row[0]

        with st.form("reset_form"):
            senha1 = st.text_input("Nova senha", type="password")
            senha2 = st.text_input("Confirmar nova senha", type="password")
            ok = st.form_submit_button("✅ Salvar nova senha")

        if ok:
            if not senha1 or senha1 != senha2 or len(senha1) < 8:
                st.error("❌ Senha inválida (mín. 8) ou confirmação diferente.")
                st.stop()

            nova_hash = pbkdf2_sha256.hash(senha1)

            db.execute(text("""
                UPDATE usuarios
                SET senha = :h, forcar_reset = false
                WHERE id = :uid
            """), {"h": nova_hash, "uid": user_id})

            # invalida token (one-time)
            db.execute(text("DELETE FROM password_resets WHERE user_id = :uid"), {"uid": user_id})

            db.commit()

            st.success("✅ Senha redefinida com sucesso. Faça login.")
            st.query_params.clear()
            st.stop()

    finally:
        db.close()


# -------------------- CONTROLE DE SESSÃO --------------------

# -------------------------------
# Inicialização de estado global
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "recover_step" not in st.session_state:
    st.session_state.recover_step = 0  # 0=login | 1=recuperar | 2=redefinir

if "last_recover_message" not in st.session_state:
    st.session_state.last_recover_message = None

if "last_recover_ts" not in st.session_state:
    st.session_state.last_recover_ts = None


# Detecta token na URL (reset de senha)
query_params = st.query_params

if "token" in query_params:
    token = query_params["token"]
    st.session_state.token_reset = token
    st.session_state.recover_step = 2
    st.query_params.clear()  # remove o token da URL (importante)
    st.rerun()  # força redesenho já no modo "redefinir senha"


if "recover_step" not in st.session_state:
   st.session_state.recover_step = 0

st.markdown("""
<style>
.stSpinner, .st-emotion-cache-1wq8k6j, .st-emotion-cache-16uqh1j {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------- [2] CABEÇALHO FIXO E VARIÁVEIS GLOBAIS --------------------

# Cabeçalho fixo
st.markdown("""
    <div style='
        width: 100%; 
        text-align: center; 
        padding: 6px 0; 
        font-size: 44px; 
        font-weight: bold; 
        color: green;
        border-bottom: 1px solid #DDD;
    '>Bem-vindo à fAIxaBet®
        <hr style="margin: 0; border: 0; border-top: 1px solid #DDD;">
        <div style='text-align:center; font-size:19px; color:black; margin-top:4px;'>
            O Futuro da Loteria é Prever
        </div>
    </div>
""", unsafe_allow_html=True)

#  "🔹 Sorte é Aleatória. Aqui é Inteligência.",
#  "Previsões baseadas em dados reais.",
#  "O Futuro da Loteria é Prever.",
#  "Gere seus palpites com o poder da IA.",
#  "FaixaBet — Onde os Números Pensam.",
#  "Inteligência. Não sorte."


# ✅ Backend API rodando externamente (email_api.py)
API_BASE ="https://faixabet-email-api.onrender.com"

# -------------------- [3] DEFINIÇÃO DE FUNÇÕES --------------------

def css_global():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        font-size: 18px;
    }
        
        @import url('https://fonts.googleapis.com/css2?family=Poppins&display=swap');
        html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        font-size: 18px;
    }
        /* Centraliza o título */
        .main > div > div > div > div {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Título FaixaBet */
        .login-title {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            color: #008000;
            margin-bottom: 24px;
        }

        /* Estilo dos inputs e botões */
        input, .stButton button {
            width: 50ch !important;
            max-width: 60%;
            margin-top: 8px;
            padding: 8px;
            border-radius: 8px;
        }

        /* Botões */
        .stButton button {
            background-color: #008000;
            color: white;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }
        .stButton button:hover {
            background-color: #005e00;
        }

        /* Radio Buttons - horizontal e colorido */
        div[role="radiogroup"] > label[data-baseweb="radio"] div[aria-checked="true"] {
            background-color: #00C853;
            border-color: #00C853;
            color: white;
        }
        /* Texto do radio */
        label[data-baseweb="radio"] {
        font-size: 40px !important;
        color: #0d730d !important;
        font-weight: 500;
        }
        /* Cards simulados */
        .login-card {
            padding: 16px;
            background-color: #f9f9f9;
            border-radius: 12px;
            box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.1);
            margin-top: 16px;
        }

        <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
        font-size: 18px;
    }

    .login-card {
        background-color: #f9f9f9;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-top: 30px;
    }
    .stButton button {
        font-size: 18px !important;
        padding: 10px 24px !important;
        transform: scale(1.1);
    }
    </style>
</style>
    """, unsafe_allow_html=True)

# tava aqui a def q fazia download do database do sqlite
def registrar_login(id_usuario): 
    try:
        resposta = requests.get("https://ipinfo.io/json", timeout=5)
        dados = resposta.json()
    except:
        dados = {}

    db = Session()    
    try:
        db.execute(text("""
            INSERT INTO log_user (
                id_cliente, data_hora, ip, hostname, city, region, country, loc, org, postal, timezone
            ) VALUES (
                :id_client, now(), :ip, :hostname, :city, :region, :country, :loc, :org, :postal, :timezone
            )
        """), {
            "id_client": id_usuario,
            "ip": dados.get("ip", "desconhecido"),
            "hostname": dados.get("hostname", ""),
            "city": dados.get("city", ""),
            "region": dados.get("region", ""),
            "country": dados.get("country", ""),
            "loc": dados.get("loc", ""),
            "org": dados.get("org", ""),
            "postal": dados.get("postal", ""),
            "timezone": dados.get("timezone", "")
        })
        db.commit()
    finally:
        db.close()

def calcular_palpites_periodo(id_usuario):
    db = Session()
    try:
        dia_result = db.execute(text("""
            SELECT COUNT(*) FROM palpites WHERE id_usuario = :id AND DATE(data) = CURRENT_DATE
        """), {"id": id_usuario})
        dia = dia_result.scalar()

        semana_result = db.execute(text("""
            SELECT COUNT(*) FROM palpites 
            WHERE id_usuario = :id AND DATE_PART('week', data) = DATE_PART('week', CURRENT_DATE)
              AND DATE_PART('year', data) = DATE_PART('year', CURRENT_DATE)
        """), {"id": id_usuario})
        semana = semana_result.scalar()

        mes_result = db.execute(text("""
            SELECT COUNT(*) FROM palpites 
            WHERE id_usuario = :id AND DATE_PART('month', data) = DATE_PART('month', CURRENT_DATE)
              AND DATE_PART('year', data) = DATE_PART('year', CURRENT_DATE)
        """), {"id": id_usuario})
        mes = mes_result.scalar()

        return dia or 0, semana or 0, mes or 0
    finally:
        db.close()

# -------------------- [4] APLICAÇÃO STREAMLIT --------------------
# =========================================================
# Controle de visibilidade do "modal" (container)
# =========================================================
if "show_recover_modal" not in st.session_state:
    st.session_state.show_recover_modal = False
    
# =========================================================
# Função para gerar token de recuperação
# =========================================================
def gerar_token_recuperacao(user_id, db):
    token = secrets.token_urlsafe(32)
    validade = datetime.utcnow() + timedelta(hours=1)
    try:
        db.execute(text("""
            INSERT INTO password_resets (user_id, token, expira_em)
            VALUES (:user_id, :token, :expira_em)
            ON CONFLICT (user_id) DO UPDATE
            SET token = EXCLUDED.token, expira_em = EXCLUDED.expira_em
        """), {"user_id": user_id, "token": token, "expira_em": validade})
        db.commit()
        return token
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao gerar token de recuperação: {e}")
        return None

#def enviar_email_reset(destinatario: str, link: str):
#    """
#    Stub temporário de envio de e-mail de recuperação.
#    Em produção, integrar SMTP / Brevo / SES / etc.
#    """
#    print("==== RESET DE SENHA ====")
#    print("Para:", destinatario)
#    print("Link:", link)
#    print("========================")

# =========================================================
# LOGIN + RECUPERAÇÃO DE SENHA (V9)
# =========================================================

from sqlalchemy import text
from datetime import datetime


def registrar_tentativa_falha(usuario_input):
    """
    Registra tentativa de login inválida.
    Pode ser expandido futuramente para:
    - rate-limit
    - bloqueio temporário
    - alerta por e-mail
    """

    with Session() as db:
        db.execute(
            text("""
                UPDATE usuarios
                   SET tentativas_falha = COALESCE(tentativas_falha, 0) + 1,
                       dt_ultima_tentativa = :dt
                 WHERE usuario = :usuario
            """),
            {
                "usuario": usuario_input,
                "dt": datetime.utcnow()
            }
        )
        db.commit()


# -------------------------------
# Inicialização de estado
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "recover_step" not in st.session_state:
    st.session_state.recover_step = 0  # 0=login | 1=recuperar

if "last_recover_message" not in st.session_state:
    st.session_state.last_recover_message = None

if "last_recover_ts" not in st.session_state:
    st.session_state.last_recover_ts = None
# -------------------------------
# FLUXO NÃO LOGADO
# -------------------------------
if not st.session_state.logged_in:

    # 🔒 Esconde sidebar
    st.sidebar.empty()
    st.markdown(
        "<style>[data-testid='stSidebar']{display:none}</style>",
        unsafe_allow_html=True
    )

    # -------------------------------
    # Mensagem pós recuperação (20s)
    # -------------------------------
    if st.session_state.last_recover_message:
        elapsed = time.time() - st.session_state.last_recover_ts

        if elapsed < 20:
            col_msg, col_btn = st.columns([5, 1])
            with col_msg:
                st.success(st.session_state.last_recover_message)
            with col_btn:
                if st.button("✖", help="Fechar mensagem"):
                    st.session_state.last_recover_message = None
                    st.session_state.last_recover_ts = None
                    st.rerun()
        else:
            st.session_state.last_recover_message = None
            st.session_state.last_recover_ts = None
            st.rerun()

    # =====================================================
    # PASSO 0 → LOGIN
    # =====================================================
    if st.session_state.recover_step == 0:

        st.markdown("## 🔐 Login")

        with st.form("login_form", clear_on_submit=False):
            usuario_input = st.text_input("Usuário", key="login_usuario")
            senha_input = st.text_input("Senha", type="password", key="login_senha")
            submitted_login = st.form_submit_button(
                "🔐 Conectar",
                use_container_width=True
            )

        submitted_recover = st.button(
            "🔁 Esqueci minha senha",
            use_container_width=True
        )

        if submitted_recover:
            st.session_state.recover_step = 1
            st.rerun()

        if submitted_login:

            if login_bloqueado(usuario_input):
                st.error("🔒 Muitas tentativas. Tente novamente em alguns minutos.")
                st.stop()

            db = Session()
            try:
                row = db.execute(text("""
                    SELECT
                        id,
                        nome_completo,
                        email,
                        tipo,
                        id_plano,
                        senha
                    FROM usuarios
                    WHERE usuario = :usuario
                      AND ativo = true
                    LIMIT 1
                """), {"usuario": usuario_input}).fetchone()

                if not row:
                    registrar_tentativa_falha(usuario_input)
                    st.error("❌ Usuário ou senha inválidos.")
                    st.stop()

                (
                    user_id,
                    nome_completo,
                    email,
                    tipo,
                    id_plano,
                    senha_hash
                ) = row

                if not verificar_senha(
                    senha_digitada=senha_input,
                    senha_hash=senha_hash,
                    db=db,
                    user_id=user_id
                ):
                    registrar_tentativa_falha(usuario_input)
                    st.error("❌ Usuário ou senha inválidos.")
                    st.stop()

                # Reset de tentativas (tolerante à ausência de colunas)
                try:
                    db.execute(
                        text("""
                            UPDATE usuarios
                               SET tentativas_falha = 0,
                                   dt_ultima_tentativa = NULL
                             WHERE id = :uid
                        """),
                        {"uid": user_id}
                    )
                    db.commit()
                except Exception:
                    pass

                st.session_state.logged_in = True
                st.session_state.usuario = {
                    "id": user_id,
                    "nome": nome_completo,
                    "email": email,
                    "tipo": tipo,
                    "id_plano": id_plano
                }

                st.rerun()

            finally:
                db.close()

    # =====================================================
    # PASSO 1 → RECUPERAR SENHA
    # =====================================================
    elif st.session_state.recover_step == 1:

        st.markdown("## 🔑 Recuperar senha")

        with st.form("recover_form"):
            email = st.text_input("Informe seu e-mail cadastrado")
            submitted_recover_email = st.form_submit_button("📩 Enviar link")

        if submitted_recover_email:
            db = Session()
            try:
                row = db.execute(text("""
                    SELECT id, email
                    FROM usuarios
                    WHERE email = :email
                      AND ativo = true
                    LIMIT 1
                """), {"email": email}).fetchone()

                st.session_state.last_recover_message = (
                    "📬 Se esse e-mail existir, enviaremos um link de recuperação."
                )
                st.session_state.last_recover_ts = time.time()
                st.session_state.recover_step = 0

                if row:
                    user_id, user_email = row
                    token = gerar_token_recuperacao(user_id, db)
                    if token:
                        base_url = os.getenv("APP_BASE_URL", "http://localhost:8501")
                        link = f"{base_url}/?reset=1&token={token}"
                        enviar_email_reset(user_email, link)

                st.rerun()

            finally:
                db.close()


# ==========================================================
# LOGIN /  com suporte a múltiplas loterias
# ==========================================================
if st.session_state.get("logged_in", False):

    # --- Cabeçalho lateral ---
    usuario = st.session_state.get("usuario", {})
    nome_usuario = usuario.get("nome", "Usuário")
    tipo_user = usuario.get("tipo", "").upper()

    st.sidebar.title(f"Bem-vindo(a), {nome_usuario}")
    st.sidebar.markdown("""
        <div style='text-align:center; padding:8px 0; font-size:26px;
        font-weight:bold; color:green; border-bottom:1px solid #DDD;'>
            fAIxaBet®
        </div>
    """, unsafe_allow_html=True)

    # --- Loteria selecionada ---
    st.sidebar.markdown("### Escolha a Loteria")
    loteria_escolhida = st.sidebar.selectbox(
        "Loteria:",
        ["Lotofácil", "Mega-Sena"],
        index=0,
    )
    st.session_state["loteria"] = loteria_escolhida

    # =======================================================
    # MENU PRINCIPAL
    # =======================================================
    if tipo_user in ["A", "ADM", "ADMIN"]:
        st.sidebar.markdown("### Seu Menu")
        menu_itens = [
            "Painel Estatístico",
            "Gerar Novas Bets",
            "Histórico",
            "Validar Bets Gerada",
            "Assinatura ",
            "Editar Perfil",
            "Telemetria",
            "Usuários",
            "Notificar",
            "Resultados",
            "Evolução",
            "Sair",
        ]
    else:
        menu_itens = [
            "Painel Estatístico",
            "Gerar Novas Bets",
            "Histórico",
            "Validar Bets Gerada",
            "Assinatura ",
            "Editar Perfil",
            "Sair",
        ]

    opcao_selecionada = st.sidebar.radio(" ", menu_itens)
    st.session_state["opcao_selecionada"] = opcao_selecionada

    # =======================================================
    # ROTEAMENTO DAS OPÇÕES
    # =======================================================

    # ---------- Painel Estatístico ----------
    if opcao_selecionada == "Painel Estatístico":
        mostrar_dashboard()
        dia, semana, mes = calcular_palpites_periodo(usuario["id"])
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Palpites Hoje", dia)
        col2.metric("Palpites na Semana", semana)
        col3.metric("Palpites no Mês", mes)

    # ---------- Palpites (Lotofácil / Mega-Sena) ----------
    elif opcao_selecionada in ["Gerar Novas Bets", "Histórico", "Validar Bets Gerada"]:

        # 🔸 Importa módulo correto conforme a loteria escolhida
        if loteria_escolhida == "Mega-Sena":
            from mega.palpites_m import (
                gerar_palpite_ui,
                historico_palpites,
                validar_palpite,
            )
        else:
            from palpites_legacy import (
                gerar_palpite_ui,
                historico_palpites,
                validar_palpite,
            )

        if opcao_selecionada == "Gerar Novas Bets":
            gerar_palpite_ui()
        elif opcao_selecionada == "Histórico":
            historico_palpites()
        elif opcao_selecionada == "Validar Bets Gerada":
            validar_palpite()

    # ---------- Outros Menus ----------
    elif opcao_selecionada == "Assinatura ":
        exibir_aba_financeiro()

    elif opcao_selecionada == "Editar Perfil":
        user_id = st.session_state.usuario["id"]
        editar_perfil(user_id)


    elif opcao_selecionada == "Telemetria":
        from dashboard import mostrar_telemetria
        mostrar_telemetria()

    elif opcao_selecionada == "Usuários":
        from admin.usuarios import listar_usuarios
        listar_usuarios()

    elif opcao_selecionada == "Notificar":
        from app.notificacoes.notifica import tela_notificacoes_acertos
        tela_notificacoes_acertos(loteria_escolhida)



    elif opcao_selecionada == "Resultados":
        import resultados
        resultados.importar_resultado()

    elif opcao_selecionada == "Evolução":
        import verificar_palpites
        verificar_palpites.executar_verificacao()

    elif opcao_selecionada == "Sair":
        logout()

# ==========================================================
# Se não estiver logado, mostra apenas o formulário de login
# ==========================================================


# --- FIM DO BLOCO DE LOGIN / CADASTRO ---
    st.sidebar.markdown("<div style='text-align:left; color:green; font-size:16px;'>fAIxaBet v9.1</div>", unsafe_allow_html=True)
