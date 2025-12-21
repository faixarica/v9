# cron_envio_palpites.py  (v1.0)

import os
import psycopg2
import requests
from datetime import datetime, timedelta

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

DB_DSN = os.getenv("DB_DSN")  # ex: "postgresql://user:pass@host:port/dbname"

def get_conn():
    return psycopg2.connect(DB_DSN)

def gerar_palpites_lotofacil(qtd):
    # TODO: chame seu modelo LS14/15/16/17 ou endpoint interno
    # Aqui é só exemplo “fake”
    import random
    palpites = []
    for _ in range(qtd):
        dezenas = sorted(random.sample(range(1, 26), 15))
        palpites.append(" ".join(f"{d:02d}" for d in dezenas))
    return palpites

def gerar_palpites_megasena(qtd):
    import random
    palpites = []
    for _ in range(qtd):
        dezenas = sorted(random.sample(range(1, 61), 6))
        palpites.append(" ".join(f"{d:02d}" for d in dezenas))
    return palpites

def enviar_email_brevo(email, assunto, html):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    payload = {
        "sender": {"name": "fAIxaBet", "email": "nao-responder@faixabet.com"},
        "to": [{"email": email}],
        "subject": assunto,
        "htmlContent": html,
    }
    r = requests.post(url, json=payload, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

def main():
    now = datetime.now()
    hoje = now.date()
    hora_atual = now.time()
    dia_semana = now.isoweekday()  # 1=seg ...7=dom

    conn = get_conn()
    cur = conn.cursor()

    # Busca usuários com envio ativo e dia da semana batendo
    # Dica: filtrar horário no Python p/ simplificar
    cur.execute("""
        SELECT uap.id, uap.user_id, uap.qtd_lotofacil, uap.qtd_megasena,
               uap.dias_semana, uap.horario_envio, uap.canal,
               us.email
        FROM user_auto_palpites uap
        JOIN users us ON us.id = uap.user_id
        WHERE uap.ativo = 1
    """)
    rows = cur.fetchall()

    janela_min = 10  # minutos

    for row in rows:
        (uap_id, user_id, qtd_lf, qtd_ms,
         dias_str, horario_envio, canal, email) = row

        # Verifica se hoje é dia configurado
        dias_lista = [int(x) for x in dias_str.split(",") if x.strip().isdigit()]
        if dia_semana not in dias_lista:
            continue

        # Verifica se está dentro da janela de horário
        alvo_dt = datetime.combine(hoje, horario_envio)
        diff_min = abs((now - alvo_dt).total_seconds()) / 60.0
        if diff_min > janela_min:
            continue

        # Verifica se já enviou hoje para cada loteria
        def ja_enviou(loteria):
            cur.execute("""
                SELECT 1 FROM palpites_envios_log
                WHERE user_id = %s AND data_envio = %s AND loteria = %s
                LIMIT 1
            """, (user_id, hoje, loteria))
            return cur.fetchone() is not None

        # LOTOFÁCIL
        if qtd_lf > 0 and not ja_enviou('lotofacil'):
            palpites_lf = gerar_palpites_lotofacil(qtd_lf)
        else:
            palpites_lf = []

        # MEGA-SENA
        if qtd_ms > 0 and not ja_enviou('megasena'):
            palpites_ms = gerar_palpites_megasena(qtd_ms)
        else:
            palpites_ms = []

        if not palpites_lf and not palpites_ms:
            continue

        # Monta HTML
        html = "<h2>Seus palpites fAIxaBet de hoje</h2>"
        if palpites_lf:
            html += "<h3>Lotofácil</h3><ul>"
            for p in palpites_lf:
                html += f"<li><code>{p}</code></li>"
            html += "</ul>"
        if palpites_ms:
            html += "<h3>Mega-Sena</h3><ul>"
            for p in palpites_ms:
                html += f"<li><code>{p}</code></li>"
            html += "</ul>"

        # Custo zero de modelo; só email
        try:
            enviar_email_brevo(email, "Seus palpites de hoje - fAIxaBet", html)
            status = "sucesso"
            erro = None
        except Exception as e:
            status = "erro"
            erro = str(e)

        # Loga LOTOFÁCIL
        if palpites_lf:
            cur.execute("""
                INSERT INTO palpites_envios_log
                (user_id, data_envio, horario_envio, canal, loteria, qtd_palpites, status, detalhe_erro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, hoje, hora_atual, 'email', 'lotofacil', len(palpites_lf), status, erro))

        # Loga MEGA-SENA
        if palpites_ms:
            cur.execute("""
                INSERT INTO palpites_envios_log
                (user_id, data_envio, horario_envio, canal, loteria, qtd_palpites, status, detalhe_erro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, hoje, hora_atual, 'email', 'megasena', len(palpites_ms), status, erro))

        conn.commit()

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
