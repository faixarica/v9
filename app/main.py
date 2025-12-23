# app/main.py
# autor: FFerreira
# descrição: Aplicação principal Streamlit da fAIxaBet V9
import streamlit as st


def main():
    # ✅ daqui pra baixo, TUDO acontece dentro do main()

    # --- imports (ok dentro do main) ---
    import os
    import time
    import secrets
    import requests
    import base64
    import hashlib
    import pandas as pds

    from datetime import datetime, timedelta
    from sqlalchemy import text
    from passlib.hash import pbkdf2_sha256

    from app.db import Session
    from app.dashboard import mostrar_dashboard
    from app.auth import verificar_senha, logout
    from app.services.email_service import enviar_email_reset
    from app.notificacoes.notifica import tela_notificacoes_acertos
    from app.perfil import editar_perfil
    from app.financeiro import exibir_aba_financeiro

    #st.write("🔄 Inicializando aplicação...")

    # -------------------------------
    # Estado global (sempre dentro do main)
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
    # CSS / UI helpers
    # -------------------------------
    st.markdown(
        """
        <style>
        .stSpinner, .st-emotion-cache-1wq8k6j, .st-emotion-cache-16uqh1j {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
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
        """,
        unsafe_allow_html=True
    )

    # -------------------------------
    # Router de reset: (?reset=1&token=...)
    # ✅ MANTER só esse (não duplicar com outro bloco)
    # -------------------------------
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
                if (not senha1) or (senha1 != senha2) or (len(senha1) < 8):
                    st.error("❌ Senha inválida (mín. 8) ou confirmação diferente.")
                    st.stop()

                nova_hash = pbkdf2_sha256.hash(senha1)

                db.execute(text("""
                    UPDATE usuarios
                    SET senha = :h, forcar_reset = false
                    WHERE id = :uid
                """), {"h": nova_hash, "uid": user_id})

                db.execute(text("DELETE FROM password_resets WHERE user_id = :uid"), {"uid": user_id})
                db.commit()

                st.success("✅ Senha redefinida com sucesso. Faça login.")
                st.query_params.clear()
                st.stop()
        finally:
            db.close()

    # -------------------------------
    # Funções que seu fluxo usa
    # (mantenha aqui dentro, para não “poluir” import-time)
    # -------------------------------
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
        bloqueio.pop(usuario, None)
        st.session_state.login_block = bloqueio
        return False

    def registrar_falha_login(usuario):
        tentativas = st.session_state.get("login_attempts", {})
        bloqueio = st.session_state.get("login_block", {})
        tentativas[usuario] = tentativas.get(usuario, 0) + 1
        if tentativas[usuario] >= MAX_LOGIN_ATTEMPTS:
            bloqueio[usuario] = {"until": datetime.utcnow() + timedelta(minutes=LOGIN_BLOCK_MINUTES)}
            tentativas[usuario] = 0
        st.session_state.login_attempts = tentativas
        st.session_state.login_block = bloqueio

    def registrar_tentativa_falha(usuario_input):
        with Session() as db:
            db.execute(
                text("""
                    UPDATE usuarios
                       SET tentativas_falha = COALESCE(tentativas_falha, 0) + 1,
                           dt_ultima_tentativa = :dt
                     WHERE usuario = :usuario
                """),
                {"usuario": usuario_input, "dt": datetime.utcnow()},
            )
            db.commit()

    def gerar_token_recuperacao(user_id, db):
        tok = secrets.token_urlsafe(32)
        validade = datetime.utcnow() + timedelta(hours=1)
        try:
            db.execute(text("""
                INSERT INTO password_resets (user_id, token, expira_em)
                VALUES (:user_id, :token, :expira_em)
                ON CONFLICT (user_id) DO UPDATE
                SET token = EXCLUDED.token, expira_em = EXCLUDED.expira_em
            """), {"user_id": user_id, "token": tok, "expira_em": validade})
            db.commit()
            return tok
        except Exception as e:
            db.rollback()
            st.error(f"Erro ao gerar token de recuperação: {e}")
            return None

    # -------------------------------
    # Fluxo NÃO LOGADO (login + recuperar)
    # -------------------------------
    if not st.session_state.logged_in:
        st.sidebar.empty()
        st.markdown("<style>[data-testid='stSidebar']{display:none}</style>", unsafe_allow_html=True)

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

        # PASSO 0: login
        if st.session_state.recover_step == 0:
            st.markdown("## 🔐 Login")

            with st.form("login_form", clear_on_submit=False):
                usuario_input = st.text_input("Usuário", key="login_usuario")
                senha_input = st.text_input("Senha", type="password", key="login_senha")
                submitted_login = st.form_submit_button("🔐 Conectar", use_container_width=True)

            submitted_recover = st.button("🔁 Esqueci minha senha", use_container_width=True)

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
                        SELECT id, nome_completo, email, tipo, id_plano, senha
                        FROM usuarios
                        WHERE usuario = :usuario
                          AND ativo = true
                        LIMIT 1
                    """), {"usuario": usuario_input}).fetchone()

                    if not row:
                        registrar_tentativa_falha(usuario_input)
                        registrar_falha_login(usuario_input)
                        st.error("❌ Usuário ou senha inválidos.")
                        st.stop()

                    user_id, nome_completo, email, tipo, id_plano, senha_hash = row

                    if not verificar_senha(
                        senha_digitada=senha_input,
                        senha_hash=senha_hash,
                        db=db,
                        user_id=user_id,
                    ):
                        registrar_tentativa_falha(usuario_input)
                        registrar_falha_login(usuario_input)
                        st.error("❌ Usuário ou senha inválidos.")
                        st.stop()

                    # zera tentativas se existir coluna
                    try:
                        db.execute(text("""
                            UPDATE usuarios
                               SET tentativas_falha = 0,
                                   dt_ultima_tentativa = NULL
                             WHERE id = :uid
                        """), {"uid": user_id})
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

        # PASSO 1: recuperar senha
        else:
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

                    st.session_state.last_recover_message = "📬 Se esse e-mail existir, enviaremos um link de recuperação."
                    st.session_state.last_recover_ts = time.time()
                    st.session_state.recover_step = 0

                    if row:
                        user_id, user_email = row
                        tok = gerar_token_recuperacao(user_id, db)
                        if tok:
                            base_url = os.getenv("APP_BASE_URL", "http://localhost:8501")
                            link = f"{base_url}/?reset=1&token={tok}"
                            enviar_email_reset(user_email, link)

                    st.rerun()
                finally:
                    db.close()

        return  # ✅ importante: não deixa continuar para menu logado

    # -------------------------------
    # Fluxo LOGADO (menu)
    # -------------------------------
    usuario = st.session_state.get("usuario", {})
    nome_usuario = usuario.get("nome", "Usuário")
    tipo_user = (usuario.get("tipo", "") or "").upper()

    st.sidebar.title(f"Bem-vindo(a), {nome_usuario}")
    st.sidebar.markdown(
        "<div style='text-align:center; padding:8px 0; font-size:26px; font-weight:bold; color:green; border-bottom:1px solid #DDD;'>fAIxaBet®</div>",
        unsafe_allow_html=True
    )

    st.sidebar.markdown("### Escolha a Loteria")
    loteria_escolhida = st.sidebar.selectbox("Loteria:", ["Lotofácil", "Mega-Sena"], index=0)
    st.session_state["loteria"] = loteria_escolhida

    if tipo_user in ["A", "ADM", "ADMIN"]:
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

    if opcao_selecionada == "Painel Estatístico":
        mostrar_dashboard()

    elif opcao_selecionada in ["Gerar Novas Bets", "Histórico", "Validar Bets Gerada"]:
        # ✅ ajuste de imports p/ estrutura V9
        if loteria_escolhida == "Mega-Sena":
            from mega.palpites_m import gerar_palpite_ui, historico_palpites, validar_palpite
        else:
            from palpites_legacy import gerar_palpite_ui, historico_palpites, validar_palpite

        if opcao_selecionada == "Gerar Novas Bets":
            gerar_palpite_ui()
        elif opcao_selecionada == "Histórico":
            historico_palpites()
        else:
            validar_palpite()

    elif opcao_selecionada == "Assinatura ":
        exibir_aba_financeiro()

    elif opcao_selecionada == "Editar Perfil":
        editar_perfil(usuario["id"])

    elif opcao_selecionada == "Telemetria":
        # ✅ ajuste p/ V9
        from app.dashboard import mostrar_telemetria
        mostrar_telemetria()

    elif opcao_selecionada == "Usuários":
        from app.admin.usuarios import listar_usuarios
        listar_usuarios()

    elif opcao_selecionada == "Notificar":
        tela_notificacoes_acertos(loteria_escolhida)

    elif opcao_selecionada == "Resultados":
        from app.admin import resultados
        resultados.importar_resultado()

    elif opcao_selecionada == "Evolução":
        from app.admin import verificar_palpites
        verificar_palpites.executar_verificacao()

    elif opcao_selecionada == "Sair":
        logout()

    st.sidebar.markdown("<div style='text-align:left; color:green; font-size:16px;'>fAIxaBet v9.11</div>", unsafe_allow_html=True)
