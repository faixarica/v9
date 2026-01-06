"""
SCRIPT DE RASPAGEM INCREMENTAL DAS LOTERIAS CAIXA
-------------------------------------------------

Este script lê o arquivo CSV da loteria selecionada, identifica o último
concurso registrado e procura somente os concursos seguintes.

Se a Caixa ainda não publicou o próximo resultado (ex: antes das 20h),
o script encerra corretamente sem erro.

Caso tenham ocorrido sorteios recentes não registrados (ex: script ficou dias sem rodar),
ele preencherá todos os concursos faltantes até o mais recente disponível.

Funciona para:
  ✅ Lotofácil
  ✅ Mega-Sena

Pronto para expansão para:
  ➕ Lotomania
  ➕ Quina
  ➕ Dupla Sena

Autor: fAIxaBet® — Atualização incremental inteligente.
"""

import requests
import csv
import os
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}

API_BASE = {
    "lotofacil": "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil",
    "megasena":  "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
    "lotomania": "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotomania"
}
CSV_FILE = {
    "lotofacil": "loteria.csv",
    "megasena":  os.path.join("mega", "loteriamega.csv"),
    "lotomania": os.path.join("lotomania", "loteriamania.csv"),
}


# ----------------------------------------------------
# AUXILIAR → LÊ O ÚLTIMO CONCURSO DO CSV
# ----------------------------------------------------
def ultimo_csv(csv_path):
    if not os.path.exists(csv_path): 
        return 0
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0
    return max(int(r["Concurso"]) for r in rows)

# ----------------------------------------------------
# SALVAR MEGA-SENA
# -------------------------------------
def salvar_csv_megasena(csv_path, rec):
    fieldnames = [
    "Concurso","Data do Sorteio",

    "Bola1","Bola2","Bola3","Bola4","Bola5","Bola6",

    # SENA
    "Ganhadores 6 acertos","Cidade / UF","Rateio 6 acertos",

    # QUINA
    "Ganhadores 5 acertos","Cidade/UF 5 acertos","Rateio 5 acertos",

    # QUADRA
    "Ganhadores 4 acertos","Cidade/UF 4 acertos","Rateio 4 acertos",

    # Extras
    "Acumulado 6 acertos","Arrecadação Total","Estimativa prêmio",
    "Acumulado Sorteio Especial Mega da Virada","Observação"
]

    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        rows = []

    if any(str(r["Concurso"]) == str(rec["Concurso"]) for r in rows):
        print(f"⚠️ Concurso {rec['Concurso']} já existe. Pulando.")
        return False

    rows.append(rec)
    rows.sort(key=lambda x: int(x["Concurso"]))

    with open(csv_path, "w", newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Inserido concurso {rec['Concurso']} no CSV Mega-Sena.")
    return True

# ----------------------------------------------------
# PARSE MEGA-SENA (converte JSON → linha CSV)
# ----------------------------------------------------
def parse_megasena(d):
    dz = d.get("listaDezenas", []) or []
    faixas = d.get("listaRateioPremio", []) or []

    def fx(i, campo):
        if len(faixas) > i:
            return faixas[i].get(campo, "")
        return ""

    return {
        "Concurso": d.get("numero"),
        "Data do Sorteio": d.get("dataApuracao"),

        # dezenas
        "Bola1": dz[0], "Bola2": dz[1], "Bola3": dz[2],
        "Bola4": dz[3], "Bola5": dz[4], "Bola6": dz[5],

        # Sena
        "Ganhadores 6 acertos": fx(0, "numeroDeGanhadores"),
        "Cidade / UF": fx(0, "local"),
        "Rateio 6 acertos": fx(0, "valorPremio"),

        # Quina
        "Ganhadores 5 acertos": fx(1, "numeroDeGanhadores"),
        "Cidade/UF 5 acertos": fx(1, "local"),
        "Rateio 5 acertos": fx(1, "valorPremio"),

        # Quadra
        "Ganhadores 4 acertos": fx(2, "numeroDeGanhadores"),
        "Cidade/UF 4 acertos": fx(2, "local"),
        "Rateio 4 acertos": fx(2, "valorPremio"),

        # extras
        "Acumulado 6 acertos": d.get("valorAcumulado", ""),
        "Arrecadação Total": d.get("valorArrecadado", ""),
        "Estimativa prêmio": d.get("valorEstimadoProximoConcurso", ""),
        "Acumulado Sorteio Especial Mega da Virada": d.get("acumuladoEspecial", ""),
        "Observação": d.get("observacao", ""),
    }

def parse_lotomania(d):
    dz = d.get("listaDezenas", []) or []
    faixas = d.get("listaRateioPremio", []) or []

    # mapear faixas que nos interessam
    premio = {
        "20": {"ganh": "", "premio": ""},
        "19": {"ganh": "", "premio": ""},
        "18": {"ganh": "", "premio": ""},
        "17": {"ganh": "", "premio": ""},
        "0":  {"ganh": "", "premio": ""},
    }
    for f in faixas:
        desc = (f.get("descricaoFaixa") or "").lower()
        ganh = f.get("numeroDeGanhadores", "") or "0"
        val  = f.get("valorPremio", "") or "0"
        if "20 acertos" in desc: premio["20"].update({"ganh": ganh, "premio": val})
        elif "19 acertos" in desc: premio["19"].update({"ganh": ganh, "premio": val})
        elif "18 acertos" in desc: premio["18"].update({"ganh": ganh, "premio": val})
        elif "17 acertos" in desc: premio["17"].update({"ganh": ganh, "premio": val})
        elif "0 acertos"  in desc: premio["0"].update({"ganh": ganh, "premio": val})

    rec = {
        "Concurso": d.get("numero"),
        "Data do Sorteio": d.get("dataApuracao"),
    }
    # 20 bolas
    for i in range(20):
        rec[f"Bola{i+1}"] = dz[i] if i < len(dz) else ""

    rec.update({
        "Ganhadores 20 acertos": premio["20"]["ganh"], "Rateio 20 acertos": premio["20"]["premio"],
        "Ganhadores 19 acertos": premio["19"]["ganh"], "Rateio 19 acertos": premio["19"]["premio"],
        "Ganhadores 18 acertos": premio["18"]["ganh"], "Rateio 18 acertos": premio["18"]["premio"],
        "Ganhadores 17 acertos": premio["17"]["ganh"], "Rateio 17 acertos": premio["17"]["premio"],
        "Ganhadores 0 acertos":  premio["0"]["ganh"],  "Rateio 0 acertos":  premio["0"]["premio"],
        "Acumulado": d.get("valorAcumulado", ""),
        "Arrecadação Total": d.get("valorArrecadado", ""),
        "Estimativa prêmio": d.get("valorEstimadoProximoConcurso", ""),
        "Observação": d.get("observacao", "")
    })
    return rec

def salvar_csv_lotomania(csv_path, rec):
    fieldnames = [
    "Concurso", "Data do Sorteio",

    # 20 dezenas
    "Bola1","Bola2","Bola3","Bola4","Bola5",
    "Bola6","Bola7","Bola8","Bola9","Bola10",
    "Bola11","Bola12","Bola13","Bola14","Bola15",
    "Bola16","Bola17","Bola18","Bola19","Bola20",

    # Faixas oficiais
    "Ganhadores 20 acertos", "Rateio 20 acertos",
    "Ganhadores 19 acertos", "Rateio 19 acertos",
    "Ganhadores 18 acertos", "Rateio 18 acertos",
    "Ganhadores 17 acertos", "Rateio 17 acertos",
    "Ganhadores 0 acertos",  "Rateio 0 acertos",

    # Extras
    "Acumulado",
    "Arrecadação Total",
    "Estimativa prêmio",
    "Observação"
]


    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        rows = []

    if any(str(r["Concurso"]) == str(rec["Concurso"]) for r in rows):
        print(f"⚠️ Concurso {rec['Concurso']} já existe. Pulando.")
        return False

    rows.append(rec)
    rows.sort(key=lambda x: int(x["Concurso"]))

    with open(csv_path, "w", newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"✅ Inserido concurso {rec['Concurso']} no CSV Lotomania.")
    return True


# ----------------------------------------------------
# FETCH COM RETRY
# ----------------------------------------------------
def fetch_concurso(loteria, num, tentativas=5):
    url = f"{API_BASE[loteria]}/{num}"
    for t in range(1, tentativas+1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json(), 200
            return None, r.status_code
        except:
            print(f"⏳ Timeout ao buscar {num} (tentativa {t}/{tentativas})")
            time.sleep(t * 2)
    return None, None# ================= INTERFACE BONITA ===================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def titulo():
    print("\n" + "="*65)
    print("           💠 fAIxaBet® — Atualizador Oficial de Loterias")
    print("="*65 + "\n")

def menu():
    print("Escolha a loteria para atualizar:\n")
    print("  1️⃣  Lotofácil")
    print("  2️⃣  Mega-Sena")
    print("  3️⃣  Lotomania")
    print("  4️⃣  Atualizar todas (recomendado diariamente às 20h)")
    print("  0️⃣  Sair")
    return input("\nDigite sua opção: ").strip()

# ---------- LOTOFÁCIL: parse (JSON -> dict p/ CSV) ----------

def parse_lotofacil(data):
    dezenas = data.get("listaDezenas", []) or []
    concurso = data.get("numero")
    data_sorteio = data.get("dataApuracao")

    # mapear ganhadores e rateios por faixa
    ganh = {"15": 0, "14": 0, "13": 0, "12": 0, "11": 0}
    premio = {"15": "", "14": "", "13": "", "12": "", "11": ""}

    for f in data.get("listaRateioPremio", []) or []:
        desc = f.get("descricaoFaixa", "") or ""
        qtd = int(f.get("numeroDeGanhadores", 0) or 0)
        val = f.get("valorPremio", "")

        # extrai "15", "14", "13", etc
        k = "".join(c for c in desc if c.isdigit())
        if k in ganh:
            ganh[k] = qtd
            premio[k] = val

    rec = {
        "Concurso": concurso,
        "Data Sorteio": data_sorteio,
    }

    # 15 bolas
    for i in range(15):
        rec[f"Bola{i+1}"] = dezenas[i] if i < len(dezenas) else ""

    # ganhadores + valores pagos
    rec["Ganhadores 15 acertos"] = ganh["15"]
    rec["Rateio 15 acertos"] = premio["15"]

    rec["Ganhadores 14 acertos"] = ganh["14"]
    rec["Rateio 14 acertos"] = premio["14"]

    rec["Ganhadores 13 acertos"] = ganh["13"]
    rec["Rateio 13 acertos"] = premio["13"]

    rec["Ganhadores 12 acertos"] = ganh["12"]
    rec["Rateio 12 acertos"] = premio["12"]

    rec["Ganhadores 11 acertos"] = ganh["11"]
    rec["Rateio 11 acertos"] = premio["11"]

    return rec

# ---------- LOTOFÁCIL: salvar (append ordenado, header fixo) ----------
def salvar_csv_lotofacil(csv_path, rec):
    # NOVO HEADER COMPLETO
    fieldnames = [
        "Concurso","Data Sorteio",
        "Bola1","Bola2","Bola3","Bola4","Bola5",
        "Bola6","Bola7","Bola8","Bola9","Bola10",
        "Bola11","Bola12","Bola13","Bola14","Bola15",
        "Ganhadores 15 acertos","Rateio 15 acertos",
        "Ganhadores 14 acertos","Rateio 14 acertos",
        "Ganhadores 13 acertos","Rateio 13 acertos",
        "Ganhadores 12 acertos","Rateio 12 acertos",
        "Ganhadores 11 acertos","Rateio 11 acertos"
    ]

    # tenta ler CSV existente
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        rows = []

    # ATUALIZAÇÃO AUTOMÁTICA DO HEADER
    # se o CSV antigo não tinha os campos novos, eles serão incluídos com ""
    for r in rows:
        for c in fieldnames:
            if c not in r:
                r[c] = ""
        # remove colunas velhas que não existem mais
        remove_cols = [k for k in r.keys() if k not in fieldnames]
        for k in remove_cols:
            r.pop(k, None)

    # evita duplicar concurso
    if any(str(r.get("Concurso")) == str(rec["Concurso"]) for r in rows):
        print(f"⚠️ Concurso {rec['Concurso']} já existe no CSV.")
        return False

    # garante campos no registro novo
    for c in fieldnames:
        if c not in rec:
            rec[c] = ""

    rows.append(rec)
    rows.sort(key=lambda x: int(x["Concurso"]))

    # salva com o header completo
    with open(csv_path, "w", newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"✅ CSV Lotofácil atualizado (Concurso {rec['Concurso']}).")
    return True


# ----------------------------------------------------
# EXECUÇÃO
# ----------------------------------------------------
if __name__ == "__main__":
    while True:
        clear()
        titulo()
        escolha = menu()

        if escolha == "0":
            print("\n👋 Saindo... até a próxima.")
            break

        loterias = {
            "1": "lotofacil",
            "2": "megasena",
            "3": "lotomania",
            "4": "all"
        }

        op = loterias.get(escolha)

        if op is None:
            print("\n❌ Opção inválida!")
            time.sleep(1.5)
            continue

        # rodar todas
        if op == "all":
            for loteria in ["lotofacil", "megasena", "lotomania"]:
                print(f"\n🟦 Atualizando: {loteria.upper()} ...\n")

                csv_path = CSV_FILE[loteria]
                dirpath = os.path.dirname(csv_path)

                # Só criar diretório se ele existir (Mega e Lotomania têm pastas, Lotofácil não)
                if dirpath:
                    os.makedirs(dirpath, exist_ok=True)


                ultimo = ultimo_csv(csv_path)
                atual = ultimo + 1

                print(f"📄 Último concurso registrado: {ultimo}")
                print(f"🔍 Buscando a partir do {atual}...\n")

                while True:
                    dados, status = fetch_concurso(loteria, atual)

                    if dados is None:
                        print("⛔ Sem novos concursos (ainda não publicado).")
                        break

                    if loteria == "lotofacil":
                        rec = parse_lotofacil(dados)
                        salvar_csv_lotofacil(csv_path, rec)

                    elif loteria == "megasena":
                        rec = parse_megasena(dados)
                        salvar_csv_megasena(csv_path, rec)

                    elif loteria == "lotomania":
                        rec = parse_lotomania(dados)
                        salvar_csv_lotomania(csv_path, rec)
                    elif loteria == "lotomania":
                        rec = parse_lotomania(dados)
                        salvar_csv_lotomania(csv_path, rec)


                    atual += 1
                    time.sleep(0.4)

            print("\n✅ Todas as loterias foram atualizadas!")
            input("\nPressione ENTER para voltar ao menu...")
            continue

        # rodar apenas uma loteria
        loteria = op
        csv_path = CSV_FILE[loteria]
        dirpath = os.path.dirname(csv_path)

        # Só criar diretório se ele existir (Mega e Lotomania têm pastas, Lotofácil não)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        clear()
        titulo()
        print(f"🟩 Atualizando somente {loteria.upper()}...\n")

        ultimo = ultimo_csv(csv_path)
        atual = ultimo + 1

        print(f"📄 Último concurso registrado: {ultimo}")
        print(f"🔍 Buscando a partir do concurso {atual}...\n")

        while True:
            dados, status = fetch_concurso(loteria, atual)

            if dados is None:
                print("⛔ Sem novos concursos publicados.")
                break

            if loteria == "lotofacil":
                rec = parse_lotofacil(dados)
                salvar_csv_lotofacil(csv_path, rec)

            elif loteria == "megasena":
                rec = parse_megasena(dados)
                salvar_csv_megasena(csv_path, rec)

            elif loteria == "lotomania":
                rec = parse_lotomania(dados)
                salvar_csv_lotomania(csv_path, rec)

            atual += 1
            time.sleep(0.4)

        print("\n✅ Atualização concluída!")
        input("\nPressione ENTER para voltar ao menu...")
