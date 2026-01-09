# resultados.py - importa todos os ultimos sorteios pra a tabela resultados_oficiais.
# db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 🔹 Caminho absoluto do projeto V9
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# 🔹 Carrega explicitamente o .env
load_dotenv(ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"❌ DATABASE_URL não definida. Arquivo .env esperado em: {ENV_PATH}"
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

Session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)



def to_int(value: str):
    if value is None or value == "":
        return 0
    return int(float(value.replace(",", ".")))


def to_float(value: str):
    if value is None or value == "":
        return 0.0
    return float(value.replace(",", "."))


def importar_dados_debug():
    print("Iniciando função Importar_dados_debug()")
    try:
        # 1️⃣ Abrir conexão com banco
        print("Abrindo conexão com banco...")
        with Session() as db:
            print("Conexão aberta com sucesso!")

            # 2️⃣ Ler CSV
            csv_file = "loteria.csv"
            print(f"Tentando ler CSV: {csv_file}")

            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = list(csv.DictReader(f))
                total_linhas = len(reader)
                print(f"CSV carregado. Total de linhas: {total_linhas}")
            except FileNotFoundError:
                print(f"Arquivo CSV não encontrado: {csv_file}")
                return
            except Exception as e:
                print(f"Erro ao ler CSV: {e}")
                return

            if not reader:
                print("CSV vazio. Nada a importar.")
                return

            # 3️⃣ Loop de inserção
            inicio = time.time()
            total_ok = 0
            total_err = 0
            contador = 0
            step = max(1, total_linhas // 20)

            for idx, ln in enumerate(reader, start=1):
                try:
                    dados = {
                        "concurso": int(ln["Concurso"]),
                        "data": ln["Data Sorteio"],

                        # dezenas
                        "n1": int(ln["Bola1"]), "n2": int(ln["Bola2"]), "n3": int(ln["Bola3"]),
                        "n4": int(ln["Bola4"]), "n5": int(ln["Bola5"]), "n6": int(ln["Bola6"]),
                        "n7": int(ln["Bola7"]), "n8": int(ln["Bola8"]), "n9": int(ln["Bola9"]),
                        "n10": int(ln["Bola10"]), "n11": int(ln["Bola11"]), "n12": int(ln["Bola12"]),
                        "n13": int(ln["Bola13"]), "n14": int(ln["Bola14"]), "n15": int(ln["Bola15"]),

                        # ganhadores
                        "g15": to_int(ln["Ganhadores 15 acertos"]),
                        "g14": to_int(ln["Ganhadores 14 acertos"]),
                        "g13": to_int(ln["Ganhadores 13 acertos"]),
                        "g12": to_int(ln["Ganhadores 12 acertos"]),
                        "g11": to_int(ln["Ganhadores 11 acertos"]),

                        # rateios — NOVOS!
                        "r15": to_float(ln["Rateio 15 acertos"]),
                        "r14": to_float(ln["Rateio 14 acertos"]),
                        "r13": to_float(ln["Rateio 13 acertos"]),
                        "r12": to_float(ln["Rateio 12 acertos"]),
                        "r11": to_float(ln["Rateio 11 acertos"]),
                    }

                    db.execute(text("""
                        INSERT INTO resultados_oficiais (
                            concurso, data,
                            n1,n2,n3,n4,n5,
                            n6,n7,n8,n9,n10,
                            n11,n12,n13,n14,n15,
                            ganhadores_15, ganhadores_14, ganhadores_13,
                            ganhadores_12, ganhadores_11,
                            rateio15, rateio14, rateio13, rateio12, rateio11
                        )
                        VALUES (
                            :concurso, :data,
                            :n1,:n2,:n3,:n4,:n5,
                            :n6,:n7,:n8,:n9,:n10,
                            :n11,:n12,:n13,:n14,:n15,
                            :g15, :g14, :g13, :g12, :g11,
                            :r15, :r14, :r13, :r12, :r11
                        )
                        ON CONFLICT (concurso) DO UPDATE SET
                            data = EXCLUDED.data,
                            n1 = EXCLUDED.n1, n2 = EXCLUDED.n2, n3 = EXCLUDED.n3,
                            n4 = EXCLUDED.n4, n5 = EXCLUDED.n5, n6 = EXCLUDED.n6,
                            n7 = EXCLUDED.n7, n8 = EXCLUDED.n8, n9 = EXCLUDED.n9,
                            n10 = EXCLUDED.n10, n11 = EXCLUDED.n11, n12 = EXCLUDED.n12,
                            n13 = EXCLUDED.n13, n14 = EXCLUDED.n14, n15 = EXCLUDED.n15,
                            ganhadores_15 = EXCLUDED.ganhadores_15,
                            ganhadores_14 = EXCLUDED.ganhadores_14,
                            ganhadores_13 = EXCLUDED.ganhadores_13,
                            ganhadores_12 = EXCLUDED.ganhadores_12,
                            ganhadores_11 = EXCLUDED.ganhadores_11,
                            rateio15 = EXCLUDED.rateio15,
                            rateio14 = EXCLUDED.rateio14,
                            rateio13 = EXCLUDED.rateio13,
                            rateio12 = EXCLUDED.rateio12,
                            rateio11 = EXCLUDED.rateio11
                    """), dados)

                    total_ok += 1
                except Exception as e:
                    print(f"Erro na linha {idx}: {e}")
                    total_err += 1

                contador += 1
                if contador % step == 0 or contador == total_linhas:
                    print(f"Processadas {contador}/{total_linhas} linhas...")

            db.commit()
            duracao = time.time() - inicio
            print(f"\nImportação finalizada. Sucesso: {total_ok}, erros: {total_err}, tempo: {duracao:.2f}s")

    except Exception as e_outer:
        print("Erro crítico durante a importação:", e_outer)


# ⚡ Chamada direta
if __name__ == "__main__":
    importar_dados_debug()
