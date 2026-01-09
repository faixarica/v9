from sqlalchemy import text
from app.db import Session
from app.services.reset_manual import (
    gerar_token_reset,
    salvar_token_reset,
    gerar_link_reset
)
from app.services.email_reset_manual import enviar_reset_manual


def buscar_usuario(db, email: str):
    sql = text("""
        SELECT id, nome_completo, email
        FROM usuarios
        WHERE email = :email
          AND ativo = true
        LIMIT 1
    """)
    return db.execute(sql, {"email": email}).fetchone()


if __name__ == "__main__":

    print("\n🔐 RESET MANUAL DE SENHA – FAIXABET\n")

    email = input("📧 Email do usuário: ").strip()
    db = Session()

    try:
        usuario = buscar_usuario(db, email)

        if not usuario:
            print("❌ Usuário não encontrado ou inativo.")
            exit(1)

        print(f"\n👤 Usuário encontrado: {usuario.nome_completo}")
        confirmar = input("Confirma envio do reset? (s/N): ").lower()

        if confirmar != "s":
            print("🚫 Operação cancelada.")
            exit(0)

        token = gerar_token_reset()
        salvar_token_reset(db, usuario.id, token, minutos_validade=30)
        link_reset = gerar_link_reset(token)

        enviar_reset_manual(
            nome_usuario=usuario.nome_completo,
            email_usuario=usuario.email,
            link_reset=link_reset,
            minutos_validade=30
        )

        print("\n✅ Reset enviado com sucesso!")
        print(f"🔗 Link gerado: {link_reset}\n")

    finally:
        db.close()
