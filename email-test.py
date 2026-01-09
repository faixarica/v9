from app.services.email_service import enviar_email_reset

# Caso 1: com nome
enviar_email_reset(
    destinatario="afranciscof@gmail.com",
    link="https://faixabet.streamlit.app/reset-password?token=TESTE_COM_NOME",
    nome_usuario="Antonio Francisco",
    minutos_validade=30
)

# Caso 2: sem nome
enviar_email_reset(
    destinatario="afranciscof@gmail.com",
    link="https://faixabet.streamlit.app/reset-password?token=TESTE_SEM_NOME",
    minutos_validade=30
)

print("✅ Disparos executados")
