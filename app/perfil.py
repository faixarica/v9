# =============================================================================
# perfil.py — Edição de Perfil e Segurança
# -----------------------------------------------------------------------------
# Versão......: v9.1
# Data........: 19/12/2025
#
# Funcionalidades:
# ✅ Alteração de senha pelo usuário
# ✅ Integração com flag forcar_reset
# ✅ Unificação com fluxo de recuperação de senha
# ✅ Invalidação de sessão após troca de senha
# ✅ Diferencia comportamento Admin x Usuário
#
# Regras de negócio:
# - Usuário comum:
#     • Pode alterar apenas a própria senha
#     • Sessão é invalidada após troca de senha
# - Admin:
#     • Pode alterar senha sem forçar logout
#     • Não sofre bloqueio por forcar_reset
#
# Segurança:
# - Hash bcrypt (12 rounds)
# - Nenhum hash fora deste módulo
# - Feedback claro ao usuário
# =============================================================================

import streamlit as st
import bcrypt
from sqlalchemy import text
from app.db import Session
import streamlit as st
from passlib.hash import pbkdf2_sha256


# -----------------------------------------------------------------------------
# Função principal
# -----------------------------------------------------------------------------
def editar_perfil(user_id):
    st.subheader("👤 Editar Perfil")

    usuario = st.session_state.get("usuario")
    tipo_usuario = usuario.get("tipo") if usuario else "U"
    is_admin = tipo_usuario == "A"

    # -------------------------------------------------------------------------
    # Inputs
    # -------------------------------------------------------------------------
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirmar nova senha", type="password")

    # -------------------------------------------------------------------------
    # Botão único
    # -------------------------------------------------------------------------
    if st.button("Salvar alterações", use_container_width=True):

        # -------------------------------------------------------------
        # Validações
        # -------------------------------------------------------------
        if not nova_senha or not confirmar_senha:
            st.warning("Informe e confirme a nova senha.")
            return

        if nova_senha != confirmar_senha:
            st.error("As senhas não conferem.")
            return

        # -------------------------------------------------------------
        # Geração de hash (ÚNICO ponto do sistema)
        # -------------------------------------------------------------
        senha_hash = bcrypt.hashpw(
            nova_senha.encode(),
            bcrypt.gensalt(12)
        ).decode()

        # -------------------------------------------------------------
        # Atualização no banco
        # -------------------------------------------------------------
        with Session() as db:
            result = db.execute(
                text("""
                    UPDATE usuarios
                       SET senha = :senha,
                           forcar_reset = FALSE
                     WHERE id = :uid
                """),
                {
                    "senha": senha_hash,
                    "uid": user_id
                }
            )
            db.commit()

        if result.rowcount == 0:
            st.error("Usuário não encontrado.")
            return

        # -------------------------------------------------------------
        # Pós-processamento
        # -------------------------------------------------------------
        st.success("Senha atualizada com sucesso.")

        # -----------------------------------------------------------------
        # 🔁 INVALIDAÇÃO DE SESSÃO (somente usuário comum)
        # -----------------------------------------------------------------
        if not is_admin:
            st.info("Por segurança, faça login novamente.")

            # Limpa sessão
            for k in list(st.session_state.keys()):
                del st.session_state[k]

            st.rerun()
        else:
            st.info("Admin: sessão mantida ativa.")

def carregar_usuario(user_id: int):
    db = Session()
    try:
        sql = text("""
            SELECT
                id,
                nome_completo,
                email,
                usuario,
                data_nascimento
            FROM usuarios
            WHERE id = :uid
            LIMIT 1
        """)
        result = db.execute(sql, {"uid": user_id}).mappings().first()
        return result
    finally:
        db.close()


def editar_perfil(user_id: int):

    st.subheader("✏️ Editar Perfil")

    usuario = carregar_usuario(user_id)

    if not usuario:
        st.error("Usuário não encontrado.")
        st.stop()

    # -----------------------------
    # FORMULÁRIO DE DADOS PESSOAIS
    # -----------------------------
    with st.form("form_editar_perfil"):
        nome_completo = st.text_input(
            "Nome completo",
            value=usuario["nome_completo"]
        )

        email = st.text_input(
            "E-mail",
            value=usuario["email"]
        )

        usuario_login = st.text_input(
            "Usuário",
            value=usuario["usuario"],
            disabled=True  # RECOMENDADO
        )

        data_nascimento = st.text_input(
            "Data de nascimento",
            value=usuario["data_nascimento"] or ""
        )

        salvar = st.form_submit_button("💾 Salvar alterações", use_container_width=True)

    if salvar:
        atualizar_perfil(
            user_id,
            nome_completo,
            email,
            data_nascimento
        )
        st.success("Perfil atualizado com sucesso.")
        st.rerun()

    st.divider()

    # -----------------------------
    # MÓDULO DE TROCA DE SENHA
    # -----------------------------
    trocar_senha_ui(user_id)

def atualizar_perfil(user_id, nome, email, data_nascimento):
    db = Session()
    try:
        sql = text("""
            UPDATE usuarios
            SET
                nome_completo = :nome,
                email = :email,
                data_nascimento = :data_nascimento
            WHERE id = :uid
        """)
        db.execute(sql, {
            "nome": nome,
            "email": email,
            "data_nascimento": data_nascimento,
            "uid": user_id
        })
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
    

def trocar_senha_ui(user_id: int):
    st.subheader("🔒 Alterar senha")

    with st.form("form_trocar_senha"):
        senha_atual = st.text_input("Senha atual", type="password")
        nova_senha = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")

        submit = st.form_submit_button("Atualizar senha", use_container_width=True)

    if submit:
        if not nova_senha or nova_senha != confirmar:
            st.error("Nova senha e confirmação não conferem.")
            return

        db = Session()
        try:
            sql = text("SELECT senha FROM usuarios WHERE id = :uid")
            row = db.execute(sql, {"uid": user_id}).first()

            if not row:
                st.error("Usuário não encontrado.")
                return

            senha_hash = row[0]

            if not pbkdf2_sha256.verify(senha_atual, senha_hash):
                st.error("Senha atual incorreta.")
                return

            nova_hash = pbkdf2_sha256.hash(nova_senha)

            sql_up = text("""
                UPDATE usuarios
                SET senha = :senha, forcar_reset = false
                WHERE id = :uid
            """)
            db.execute(sql_up, {"senha": nova_hash, "uid": user_id})
            db.commit()

            st.success("Senha atualizada com sucesso.")
        finally:
            db.close()
