from app.main import enviar_email_reset

enviar_email_reset(
    "afranciscof@gmail.com",
    "https://faixabet.streamlit.app/reset-password?token=TESTE"
)

print("✅ Função chamada")
