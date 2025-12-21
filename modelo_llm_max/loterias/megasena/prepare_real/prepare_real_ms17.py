# -*- coding: utf-8 -*-
"""
prepare_real_ms17.py
Gera dados reais da Mega-Sena em formato binário (N,60) a partir de CSV (auto-detect).

Saídas (em modelo_llm_max/dados_m/):
- rows_60bin.npy  (N, 60)
- concursos.npy   (N,)
- datas.npy       (N,)  (strings)
"""

import os
import sys
import re
import numpy as np
import pandas as pd

# ============================================================
# 🔧 Diretórios base
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT_DIR, "dados_m")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 🔧 Utilidades
# ============================================================
def _find_first_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

def _to_int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return None

def _extract_dezenas_from_row(row_dict):
    """
    Extrai 6 dezenas usando heurísticas robustas.
    """
    keys = {k.lower(): k for k in row_dict.keys()}

    # 1) Coluna string com dezenas
    for cand in ["dezenas", "numeros", "números", "resultado", "bolas", "lista_dezenas"]:
        if cand in keys:
            raw = str(row_dict[keys[cand]])
            nums = [int(n) for n in re.findall(r"\d{1,2}", raw)]
            nums = [n for n in nums if 1 <= n <= 60]
            nums = sorted(set(nums))
            if len(nums) >= 6:
                return nums[:6]

    # 2) Colunas separadas
    possible_cols = []
    for base in ["bola", "bol", "dezena", "dez", "d"]:
        for i in range(1, 7):
            possible_cols.append(f"{base}{i}")

    nums = []
    for c in possible_cols:
        if c in keys:
            v = _to_int(row_dict[keys[c]])
            if v is not None and 1 <= v <= 60:
                nums.append(v)

    if len(nums) == 6:
        return sorted(nums)

    # 3) Fallback geral
    all_nums = []
    for v in row_dict.values():
        if v is None:
            continue
        found = [int(n) for n in re.findall(r"\d{1,2}", str(v))]
        for n in found:
            if 1 <= n <= 60:
                all_nums.append(n)

    all_nums = sorted(set(all_nums))
    if len(all_nums) >= 6:
        return all_nums[:6]

    return None

def _detect_concurso_col(df):
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ["concurso", "conc", "n_concurso", "numero", "número", "nr", "id"]:
            return c
        if "concurso" in cl:
            return c
    return None

def _detect_data_col(df):
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ["data", "dt", "data_sorteio", "datasorteio", "date"]:
            return c
        if "data" in cl:
            return c
    return None

# ============================================================
# 🚀 Main
# ============================================================
def main():
    print("📂 ROOT_DIR:", ROOT_DIR)
    print("📦 OUT_DIR :", OUT_DIR)

    # ========================================================
    # 🔎 AUTO-DETECÇÃO DO CSV (ALINHADO AO SEU PROJETO)
    # ========================================================
    candidate_csvs = [
        # LOCAL REAL (ADMIN)
        r"C:\Faixabet\V8\admin\mega\loteriamega",
        r"C:\Faixabet\V8\admin\mega\loteriamega.csv",

        # Fallbacks
        os.path.join(ROOT_DIR, "admin", "loteriamega"),
        os.path.join(ROOT_DIR, "admin", "loteriamega.csv"),
        os.path.join(ROOT_DIR, "dados_m", "loteriamega.csv"),
    ]

    csv_path = _find_first_existing(candidate_csvs)

    if not csv_path:
        print("\n❌ Não encontrei o CSV da Mega-Sena automaticamente.")
        print("Procurei nestes caminhos:")
        for p in candidate_csvs:
            print(" -", p)
        sys.exit(1)

    print("✅ CSV encontrado:", csv_path)

    # ========================================================
    # 📥 Leitura do CSV
    # ========================================================
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = [str(c).strip() for c in df.columns]

    col_conc = _detect_concurso_col(df)
    col_data = _detect_data_col(df)

    if not col_conc:
        print("\n❌ Não consegui detectar a coluna de concurso.")
        print("Colunas:", list(df.columns))
        sys.exit(1)

    print("🔑 Coluna concurso:", col_conc)
    print("🗓️ Coluna data   :", col_data if col_data else "(não detectada)")

    concursos, datas, rows_bin = [], [], []

    for _, row in df.iterrows():
        rd = row.to_dict()
        conc = _to_int(rd.get(col_conc))
        if conc is None:
            continue

        dezenas = _extract_dezenas_from_row(rd)
        if dezenas is None or len(dezenas) != 6:
            continue

        vec = np.zeros(60, dtype=np.int8)
        for d in dezenas:
            vec[d - 1] = 1

        concursos.append(conc)
        datas.append(str(rd.get(col_data)) if col_data else "")
        rows_bin.append(vec)

    if len(rows_bin) < 100:
        print("\n❌ Poucos concursos parseados.")
        print("Parseados:", len(rows_bin))
        sys.exit(1)

    # Ordena temporalmente
    order = np.argsort(np.array(concursos))
    concursos = np.array(concursos, dtype=np.int32)[order]
    datas = np.array(datas, dtype=object)[order]
    rows_bin = np.stack(rows_bin, axis=0)[order]

    # ========================================================
    # 💾 Salva outputs
    # ========================================================
    np.save(os.path.join(OUT_DIR, "rows_60bin.npy"), rows_bin)
    np.save(os.path.join(OUT_DIR, "concursos.npy"), concursos)
    np.save(os.path.join(OUT_DIR, "datas.npy"), datas)

    print("\n✅ GERADO COM SUCESSO")
    print("📄 rows_60bin.npy:", rows_bin.shape)
    print("📄 concursos.npy :", concursos.shape)
    print("📄 datas.npy     :", datas.shape)

if __name__ == "__main__":
    main()