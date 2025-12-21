# update_senhas_except_ids.py
# 🔒 Atualiza senha de todos usuários, exceto IDs específicos
# Usa DATABASE_URL do .env

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Carrega variáveis do .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não encontrado no arquivo .env")

# Conecta ao banco
engine = create_engine(DATABASE_URL)

# Hash fornecido (pbkdf2_sha256 já gerado)
NOVO_HASH = "$pbkdf2-sha256$29000$SCklBMAYgzCmdC5FaM0Zgw$YAe818Fqwjk/vc/62iu1QWE24.VyCOaxr9yCIqs074c"

# IDs que devem ser ignorados
EXCLUIDOS = (5, 113, 81,25)

print("🔄 Atualizando senhas dos usuários...")

with engine.begin() as conn:
    result = conn.execute(text("""
        UPDATE usuarios
        SET senha = :hash
        WHERE id NOT IN :ids
    """), {"hash": NOVO_HASH, "ids": EXCLUIDOS})

print("✅ Senhas atualizadas com sucesso!")
print(f"Senha aplicada a todos, exceto IDs: {EXCLUIDOS}")
