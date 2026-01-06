"""
prepare_real_data_db.py — FaixaBet v2.7
---------------------------------------
Gera os artefatos de dados usados pelos modelos LS14/LS15/LS16
para as loterias:

  - Lotofácil      → resultados_oficiais
  - Mega-Sena      → resultados_oficiais_m

Saídas em ./dados:

  Lotofácil:
    - rows_struct.npy   → struct tipado (concurso, data, números, features, winners)
    - rows.npy          → legado: [concurso, 15 dezenas]
    - rep_map.npy       → mapa de paridade (ex: "8p_7i": 1234 ocorrências)
    - winners.npy       → [concurso, g11, g12, g13, g14, g15]
    - rows_25bin.npy    → matriz binária (N, 25) — base para LS14/LS15
    - meta.json         → metadados (contagem, datas, etc.)

  Mega-Sena:
    - rows_60bin.npy    → matriz binária (M, 60) — base para LS14/LS15 Mega

Dependências:
  - db.py (Session, DATABASE_URL)
  - Tabelas:
      resultados_oficiais   (Lotofácil)
      resultados_oficiais_m (Mega-Sena)

Uso:
  python prepare_real_data_db.py
"""

import os
import json
import numpy as np
from sqlalchemy import text
from db import Session

OUT_DIR = os.path.join(os.path.dirname(__file__), "dados")

# -------------------------------------------------------------------
# Estrutura tipada para LOTOFÁCIL
# -------------------------------------------------------------------
DTYPE_LOTO = np.dtype([
    ("concurso",  "i4"),
    ("data",      "M8[D]"),
    ("numeros",   "i1", (15,)),
    ("pares",     "i1"),
    ("soma",      "i2"),
    ("baixas",    "i1"),   # 1–13
    ("altas",     "i1"),   # 14–25
    ("g11",       "i4"),
    ("g12",       "i4"),
    ("g13",       "i4"),
    ("g14",       "i4"),
    ("g15",       "i4"),
])


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


# -------------------------------------------------------------------
# LOTOFÁCIL — leitura do banco
# -------------------------------------------------------------------
def _fetch_rows_lotofacil():
    """
    Busca colunas principais + winners da tabela resultados_oficiais.

    Esperado:
      - concurso (int)
      - data_norm (date) — preferencial
      - data (text)      — legado (DD/MM/YYYY ou YYYY-MM-DD)
      - n1..n15 (int)
      - ganhadores_11..ganhadores_15 (int)
    """
    db = Session()
    try:
        sql = text("""
            SELECT
                concurso,
                COALESCE(data_norm::date, NULL) AS data_norm,
                data,
                n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,
                n11,n12,n13,n14,n15,
                NULLIF(ganhadores_11, NULL) AS g11,
                NULLIF(ganhadores_12, NULL) AS g12,
                NULLIF(ganhadores_13, NULL) AS g13,
                NULLIF(ganhadores_14, NULL) AS g14,
                NULLIF(ganhadores_15, NULL) AS g15
            FROM resultados_oficiais
            WHERE n1 BETWEEN 1 AND 25 AND n15 BETWEEN 1 AND 25
            ORDER BY concurso ASC;
        """)
        return db.execute(sql).fetchall()
    finally:
        db.close()


def _coalesce_date(data_norm, data_txt):
    """
    Usa data_norm se existir; caso contrário, tenta parsear data_txt.

    Formatos aceitos em data_txt:
      - YYYY-MM-DD
      - DD/MM/YYYY
    """
    if data_norm:
        return np.datetime64(str(data_norm), "D")
    if not data_txt:
        return np.datetime64("NaT")
    s = str(data_txt).strip()
    try:
        if "-" in s:  # YYYY-MM-DD
            return np.datetime64(s[:10], "D")
        if "/" in s:  # DD/MM/YYYY
            d, m, y = s[:10].split("/")
            return np.datetime64(f"{y}-{m}-{d}", "D")
    except Exception:
        pass
    return np.datetime64("NaT")


def _validate_and_features(nums):
    """
    Valida e extrai features das 15 dezenas da Lotofácil.

    Regras:
      - 15 dezenas
      - valores 1..25
      - todos únicos

    Retorna:
      (nums_sorted, pares, soma, baixas, altas) ou None se inválido.
    """
    if nums is None or len(nums) != 15:
        return None
    nums = [int(x) for x in nums]
    if any((x < 1 or x > 25) for x in nums):
        return None
    if len(set(nums)) != 15:
        return None

    nums_sorted = np.array(sorted(nums), dtype=np.int8)
    pares = int(np.sum(nums_sorted % 2 == 0))
    soma = int(np.sum(nums_sorted))
    baixas = int(np.sum(nums_sorted <= 13))
    altas  = 15 - baixas
    return nums_sorted, pares, soma, baixas, altas


# -------------------------------------------------------------------
# Geração de artefatos da LOTOFÁCIL
# -------------------------------------------------------------------
def _build_lotofacil():
    """
    Extrai LOTOFÁCIL de resultados_oficiais e gera:

      - rows_struct.npy  (DTYPE_LOTO)
      - rows.npy         (legado: [concurso, 15 dezenas])
      - rep_map.npy      (mapa de paridade, ex: "8p_7i")
      - winners.npy      ([concurso, g11, g12, g13, g14, g15])
      - rows_25bin.npy   ([N,25] one-hot)  ← base para LS14/LS15
      - meta.json        (resumo da extração)
    """
    print("🔄 [Lotofácil] Iniciando extração...")
    _ensure_dir(OUT_DIR)

    rows_sql = _fetch_rows_lotofacil()
    total_lidos = len(rows_sql)

    rep_map: dict[str, int] = {}
    winners_list = []
    struct = np.zeros(total_lidos, dtype=DTYPE_LOTO)
    usados = 0
    invalidados = 0

    for row in rows_sql:
        (concurso, data_norm, data_txt, *nums_and_wins) = row

        nums = nums_and_wins[:15]
        g11, g12, g13, g14, g15 = (
            nums_and_wins[15:20] if len(nums_and_wins) >= 20 else (None,) * 5
        )

        vf = _validate_and_features(nums)
        if vf is None:
            invalidados += 1
            continue

        nums_sorted, pares, soma, baixas, altas = vf
        d = _coalesce_date(data_norm, data_txt)

        # Atualiza mapa de paridade (ex: "8p_7i"):
        chave = f"{pares}p_{15 - pares}i"
        rep_map[chave] = rep_map.get(chave, 0) + 1

        struct[usados]["concurso"] = int(concurso)
        struct[usados]["data"]     = d
        struct[usados]["numeros"]  = nums_sorted
        struct[usados]["pares"]    = pares
        struct[usados]["soma"]     = soma
        struct[usados]["baixas"]   = baixas
        struct[usados]["altas"]    = altas
        struct[usados]["g11"]      = int(g11) if g11 is not None else 0
        struct[usados]["g12"]      = int(g12) if g12 is not None else 0
        struct[usados]["g13"]      = int(g13) if g13 is not None else 0
        struct[usados]["g14"]      = int(g14) if g14 is not None else 0
        struct[usados]["g15"]      = int(g15) if g15 is not None else 0

        winners_list.append([
            int(concurso),
            struct[usados]["g11"],
            struct[usados]["g12"],
            struct[usados]["g13"],
            struct[usados]["g14"],
            struct[usados]["g15"],
        ])
        usados += 1

    # Compacta (remove slots não usados)
    struct = struct[:usados]
    winners = (
        np.array(winners_list, dtype=np.int32)
        if winners_list else np.zeros((0, 6), dtype=np.int32)
    )

    # ------------------------------------------------------------------
    # Salvar artefatos clássicos
    # ------------------------------------------------------------------
    np.save(os.path.join(OUT_DIR, "rows_struct.npy"), struct)

    # Legado: [concurso, 15 dezenas]
    if len(struct):
        legacy_rows = np.column_stack([
            struct["concurso"],
            struct["numeros"],
        ])
    else:
        legacy_rows = np.zeros((0, 16), dtype=np.int32)
    np.save(os.path.join(OUT_DIR, "rows.npy"), legacy_rows)

    # rep_map + winners
    np.save(os.path.join(OUT_DIR, "rep_map.npy"), rep_map)
    np.save(os.path.join(OUT_DIR, "winners.npy"), winners)

    # ------------------------------------------------------------------
    # NOVO: matriz binária (N,25) → rows_25bin.npy
    # Cada linha é um concurso; colunas 1..25 viram bits 0/1
    # ------------------------------------------------------------------
    n_valid = len(struct)
    bin25 = np.zeros((n_valid, 25), dtype=np.int8)
    for i, nums in enumerate(struct["numeros"]):
        for x in nums:
            if 1 <= x <= 25:
                bin25[i, x - 1] = 1
    np.save(os.path.join(OUT_DIR, "rows_25bin.npy"), bin25)

    # Meta
    meta = {
        "loteria": "lotofacil",
        "total_lidos": int(total_lidos),
        "validos": int(len(struct)),
        "invalidos": int(invalidados),
        "primeiro_concurso": int(struct["concurso"][0]) if len(struct) else None,
        "ultimo_concurso": int(struct["concurso"][-1]) if len(struct) else None,
        "datas": {
            "min": str(struct["data"].min()) if len(struct) else None,
            "max": str(struct["data"].max()) if len(struct) else None,
        },
        "artefatos": [
            "rows_struct.npy",
            "rows.npy",
            "rep_map.npy",
            "winners.npy",
            "rows_25bin.npy",
        ],
    }
    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("✅ [Lotofácil] Extração finalizada")
    print(f" • Lidos do SQL:  {total_lidos}")
    print(f" • Válidos:       {len(struct)}")
    print(f" • Inválidos:     {invalidados}")
    print(f" • Artefatos:     rows_struct.npy, rows.npy, rep_map.npy, winners.npy, rows_25bin.npy")
    print(f" • Meta:          meta.json")


# -------------------------------------------------------------------
# MEGA-SENA — geração de rows_60bin.npy
# -------------------------------------------------------------------
def _build_mega_rows():
    """
    Extrai resultados da MEGA-SENA e gera rows_60bin.npy.

    Tabela usada:
      - resultados_oficiais_m

    Colunas esperadas:
      - concurso (int)
      - data (text ou date)  ← não é usada para o binário
      - n1..n6 (int)
    """
    print("\n🔄 [Mega-Sena] Gerando rows_60bin.npy...")

    db = Session()
    try:
        sql = text("""
            SELECT
                concurso,
                data,
                n1,n2,n3,n4,n5,n6
            FROM resultados_oficiais_m
            WHERE n1 BETWEEN 1 AND 60 AND n6 BETWEEN 1 AND 60
            ORDER BY concurso ASC;
        """)
        rows = db.execute(sql).fetchall()
    finally:
        db.close()

    if not rows:
        print("⚠ [Mega-Sena] Nenhum resultado encontrado em resultados_oficiais_m.")
        print("   rows_60bin.npy NÃO será gerado.")
        return

    bin_rows = []
    inval = 0

    for row in rows:
        (concurso, data_txt, n1, n2, n3, n4, n5, n6) = row
        nums = [n1, n2, n3, n4, n5, n6]

        # validações básicas
        if any(x is None or x < 1 or x > 60 for x in nums):
            inval += 1
            continue

        vec = np.zeros(60, dtype=np.int8)
        for x in nums:
            idx = int(x) - 1
            if 0 <= idx < 60:
                vec[idx] = 1
        bin_rows.append(vec)

    if not bin_rows:
        print("⚠ [Mega-Sena] Todas as linhas foram invalidadas. rows_60bin.npy não gerado.")
        return

    arr = np.stack(bin_rows, axis=0)
    np.save(os.path.join(OUT_DIR, "rows_60bin.npy"), arr)

    print("✅ [Mega-Sena] rows_60bin.npy gerado com sucesso.")
    print(f" • Concursos válidos: {arr.shape[0]}")
    print(f" • Inválidos:         {inval}")
    print(f" • Arquivo:           {os.path.join(OUT_DIR, 'rows_60bin.npy')}")

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    _ensure_dir(OUT_DIR)

    # 1) Lotofácil (base principal)
    _build_lotofacil()

    # 2) Mega-Sena (não derruba o processo se der erro)
    try:
        _build_mega_rows()
    except Exception as e:
        print(f"⚠ [Mega-Sena] Erro ao gerar rows_60bin.npy: {e}")
        print("   → Ajuste a função _build_mega_rows() se o schema for diferente.")


if __name__ == "__main__":
    main()
