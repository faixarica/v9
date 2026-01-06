import csv
import os
import json
import datetime
from sqlalchemy import text
from db import Session

# =========================================================
# CONFIG
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "loteriamega.csv")

# Dias oficiais (terça, quinta, sábado)
DIAS_OFICIAIS = {1, 3, 5}

print("📂 BASE_DIR:", BASE_DIR)
print("📄 CSV Mega-Sena:", CSV_PATH)

# =========================================================
# HELPERS
# =========================================================

def to_int(value):
    if not value:
        return 0
    try:
        return int(value)
    except Exception:
        return int(float(value.replace(".", "").replace(",", ".")))


def to_float(value):
    if not value:
        return 0.0
    try:
        return float(value)
    except Exception:
        return float(value.replace(".", "").replace(",", "."))


def dia_oficial(data: datetime.date) -> bool:
    return data.weekday() in DIAS_OFICIAIS


# =========================================================
# CSV
# =========================================================

def carregar_csv_megasena(caminho_csv):
    resultados = []

    with open(caminho_csv, "r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)

        for row in leitor:
            try:
                concurso = int(row["Concurso"])
                data = datetime.datetime.strptime(
                    row["Data do Sorteio"], "%d/%m/%Y"
                ).date()

                premiacao_json = {
                    "cidade_uf": row.get("Cidade / UF"),
                    "rateio_6": row.get("Rateio 6 acertos"),
                    "ganhadores_5": row.get("Ganhadores 5 acertos"),
                    "rateio_5": row.get("Rateio 5 acertos"),
                    "ganhadores_4": row.get("Ganhadores 4 acertos"),
                    "rateio_4": row.get("Rateio 4 acertos"),
                    "acumulado_6": row.get("Acumulado 6 acertos"),
                    "estimativa": row.get("Estimativa prêmio"),
                    "acumulado_especial": row.get("Acumulado Sorteio Especial Mega da Virada"),
                    "observacao": row.get("Observação"),
                }

                resultados.append({
                    "concurso": concurso,
                    "data": data,
                    "n1": int(row["Bola1"]),
                    "n2": int(row["Bola2"]),
                    "n3": int(row["Bola3"]),
                    "n4": int(row["Bola4"]),
                    "n5": int(row["Bola5"]),
                    "n6": int(row["Bola6"]),
                    "acumulou": to_int(row.get("Ganhadores 6 acertos")) == 0,
                    "arrecadacao_total": to_float(row.get("Arrecadação Total")),
                    "premiacao_json": premiacao_json
                })

            except Exception as e:
                print(f"❌ Linha inválida no CSV | Concurso={row.get('Concurso')} | Erro={e}")

    return resultados


# =========================================================
# DB
# =========================================================

def obter_ultimo_concurso_db(db):
    return db.execute(
        text("SELECT MAX(concurso) FROM resultados_oficiais_m")
    ).scalar() or 0


def inserir_resultado(db, r):
    sql = """
        INSERT INTO resultados_oficiais_m (
            concurso, data,
            n1, n2, n3, n4, n5, n6,
            acumulou, arrecadacao_total, premiacao_json
        )
        VALUES (
            :concurso, :data,
            :n1, :n2, :n3, :n4, :n5, :n6,
            :acumulou, :arrecadacao_total, :premiacao_json
        )
        ON CONFLICT (concurso) DO NOTHING
    """
    db.execute(text(sql), r)


# =========================================================
# MAIN
# =========================================================

def importar_megasena(caminho_csv=CSV_PATH):
    print("🚀 Importando resultados Mega-Sena")

    if not os.path.exists(caminho_csv):
        print("❌ CSV não encontrado:", caminho_csv)
        return

    dados = carregar_csv_megasena(caminho_csv)

    if not dados:
        print("⚠ Nenhum dado válido no CSV")
        return

    dados.sort(key=lambda x: x["concurso"])

    with Session() as db:
        ultimo_db = obter_ultimo_concurso_db(db)
        print(f"📌 Último concurso no banco: {ultimo_db}")

        novos = [d for d in dados if d["concurso"] > ultimo_db]

        if not novos:
            print("✅ Banco já atualizado")
            return

        inseridos = 0

        try:
            for r in novos:
                if not dia_oficial(r["data"]):
                    print(f"⚠ Concurso fora do dia padrão: {r['concurso']} ({r['data']})")

                inserir_resultado(db, r)
                inseridos += 1
                print(f"✔ Concurso {r['concurso']} inserido")

            db.commit()

        except Exception as e:
            db.rollback()
            print("🔥 Erro crítico ao inserir Mega-Sena:", e)
            return

    print(f"🏁 Importação finalizada — {inseridos} concursos inseridos")


# =========================================================
# EXEC
# =========================================================

if __name__ == "__main__":
    importar_megasena()
