# reset_senhas_pbkdf2.py
# 🔒 Restaura as senhas da tabela 'usuarios' com hash pbkdf2_sha256
# Usa DATABASE_URL do .env
# trocamos de nome em 18/12 pq elepoderia esta gerando bug nas senhas

import os
from dotenv import load_dotenv
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine, text

# Carrega variáveis do .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não encontrado no arquivo .env")

# Conecta ao banco
engine = create_engine(DATABASE_URL)

# Defina a nova senha padrão
NOVA_SENHA = "faixab123"

print("🔄 Resetando senhas para todos os usuários...")
with engine.begin() as conn:
    result = conn.execute(text("SELECT id, usuario FROM usuarios"))
    usuarios = result.fetchall()
    for (uid, usuario) in usuarios:
        senha_hash = pbkdf2_sha256.hash(NOVA_SENHA)
        conn.execute(
            text("UPDATE usuarios SET senha = :senha WHERE id = :id"),
            {"senha": senha_hash, "id": uid}
        )
        print(f"✅ Usuário {usuario} (ID={uid}) atualizado.")

print(f"\n🚀 Todas as senhas foram redefinidas com sucesso!")
print(f"Nova senha padrão: {NOVA_SENHA}")
print("Obs: os hashes foram gerados com pbkdf2_sha256 (compatível com o app).")
