from app.services.email_service import enviar_email_brevo

enviar_email_brevo(
    destinatario_email="afranciscof@gmail.com",
    destinatario_nome="Carlos",
    template_id=3,  # seu template
    params={
        "NOME": "Antonio Francisco",
        "DATA": "20/12/2025",
        "ACERTOS": 13,
        "LOTERIA": "Lotofácil"
    }
)
