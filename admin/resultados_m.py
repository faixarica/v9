import csv
import os
import json
import datetime
from sqlalchemy import text
from db import Session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print("DEBUG BASE_DIR:", BASE_DIR)
print("DEBUG PATH CSV:", os.path.join(BASE_DIR, "csv", "loteriamega.csv"))

# Dias oficiais da Mega-Sena
DIAS_OFICIAIS = {1, 3, 5}  # terça, quinta, sábado


# ============================================================
# 1. Carregar CSV oficial da Mega-Sena (SEU FORMATO REAL)
# ============================================================
def carregar_csv_megasena(caminho_csv):
    """
    Lê o arquivo loteriamega.csv no formato oficial da Caixa.
    """
    resultados = []

    with open(caminho_csv, "r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)

        for row in leitor:
            try:
                concurso = int(row["Concurso"])

                data = datetime.datetime.strptime(
                    row["Data do Sorteio"], "%d/%m/%Y"
                ).date()

                n1 = int(row["Bola1"])
                n2 = int(row["Bola2"])
                n3 = int(row["Bola3"])
                n4 = int(row["Bola4"])
                n5 = int(row["Bola5"])
                n6 = int(row["Bola6"])

                # Acumulou = True se "Ganhadores 6 acertos" == "0"
                acumulou = (row.get("Ganhadores 6 acertos", "0").strip() == "0")

                arrecadacao = float(row.get("Arrecadação Total", 0) or 0)

                # Tudo que não faz parte do básico vai para o JSONB
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
                    "n1": n1,
                    "n2": n2,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "n6": n6,
                    "acumulou": acumulou,
                    "arrecadacao_total": arrecadacao,
                    "premiacao_json": json.dumps(premiacao_json, ensure_ascii=False)
                })

            except Exception as e:
                print(f"[ERRO] Linha inválida no CSV: {row} - Motivo: {e}")

    return resultados


# ============================================================
# 2. Ler o último concurso do banco
# ============================================================
def obter_ultimo_concurso_db():
    db = Session()
    try:
        row = db.execute(text(
            "SELECT MAX(concurso) AS ultimo FROM resultados_oficiais_m"
        )).fetchone()
        return row.ultimo if row and row.ultimo else 0
    finally:
        db.close()


# ============================================================
# 3. Validar se é dia oficial de sorteio
# ============================================================
def dia_valido(data):
    return data.weekday() in DIAS_OFICIAIS


# ============================================================
# 4. Inserir no banco
# ============================================================
def inserir_resultado(db, r):
    sql = """
        INSERT INTO resultados_oficiais_m
        (concurso, data, n1, n2, n3, n4, n5, n6,
         acumulou, arrecadacao_total, premiacao_json)
        VALUES
        (:concurso, :data, :n1, :n2, :n3, :n4, :n5, :n6,
         :acumulou, :arrecadacao_total, :premiacao_json)
    """
    db.execute(text(sql), r)


# ============================================================
# 5. Função Principal
# ============================================================
def importar_megasena(caminho_csv=None):
    if caminho_csv is None:
       caminho_csv = os.path.join(BASE_DIR, "mega", "loteriamega.csv")

    print("🟩 Importando Mega-Sena...")
    print(f"📄 Usando CSV: {caminho_csv}")

    dados = carregar_csv_megasena(caminho_csv)

    if not dados:
        print("❌ Nenhum registro válido encontrado.")
        return

    dados.sort(key=lambda x: x["concurso"])

    ultimo_db = obter_ultimo_concurso_db()
    print(f"📌 Último concurso no banco: {ultimo_db}")

    novos = [d for d in dados if d["concurso"] > ultimo_db]

    if not novos:
        print("✔ Nenhum concurso novo encontrado.")
        return

    db = Session()
    inseridos = 0

    try:
        for r in novos:
            if not dia_valido(r["data"]):
                print(f"⚠ Ignorado (não é dia oficial): {r['concurso']} - {r['data']}")
                continue

            inserir_resultado(db, r)
            inseridos += 1
            print(f"✔ Inserido concurso {r['concurso']}")

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"❌ ERRO ao inserir: {e}")

    finally:
        db.close()

    print(f"🟩 Finalizado — {inseridos} concursos inseridos.")


# Execução direta
if __name__ == "__main__":
    importar_megasena()
