"""
build_lf_datasets.py — Builder oficial dos datasets Lotofacil (FaixaBet)
-------------------------------------------------------------------------
Gera TODOS os arquivos .npy necessarios para os modelos:

    - rows_25bin.npy   (ja deve existir, gerado por outro script)
    - X_ls14.npy / y_ls14.npy   (janela curta — Free / Silver)
    - X_ls15.npy / y_ls15.npy   (janela media — Gold)
    - X_ls16.npy / y_ls16.npy   (janela longa — Platinum LS16)
    - X_ls17.npy / y_ls17.npy   (janela moderna — LS17)
    - X_ls18.npy / y_ls18.npy   (janela para meta-modelo LS18)

Uso:
    python build_lf_datasets.py

Pre-requisito:
    - C:\Faixabet\V8\modelo_llm_max\dados\rows_25bin.npy
      (shape: [N, 25], com 0/1 indicando dezenas sorteadas)
"""

import os
import numpy as np

# ============================================================
# 1. PATHS
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))            # ...\lotofacil
ROOT  = os.path.abspath(os.path.join(BASE, "..", ".."))       # ...\modelo_llm_max
DADOS = os.path.join(ROOT, "dados")

print("[DEBUG] ROOT :", ROOT)
print("[DEBUG] DADOS:", DADOS)

ROWS_PATH = os.path.join(DADOS, "rows_25bin.npy")

# ============================================================
# 2. JANELAS POR MODELO
# ============================================================
LS14_WINDOW = 32   # LS14 (Free / Silver)
LS15_WINDOW = 50   # LS15 (Gold)
LS16_WINDOW = 64   # LS16 (Platinum)
LS17_WINDOW = 64   # LS17 (engine)
LS18_WINDOW = 64   # LS18 (meta-model) — por enquanto usa mesma base

def make_xy(rows: np.ndarray, window: int):
    """
    Gera X e y a partir de uma matriz rows (N, 25),
    usando janela deslizante de tamanho 'window'.

    X: (N-window, window, 25)
    y: (N-window, 25)
    """
    X, y = [], []
    for i in range(window, len(rows)):
        X.append(rows[i - window:i])
        y.append(rows[i])
    return np.array(X), np.array(y)


def build_all():
    if not os.path.exists(ROWS_PATH):
        raise FileNotFoundError(f"[ERRO] rows_25bin.npy nao encontrado em: {ROWS_PATH}")

    rows = np.load(ROWS_PATH)
    print("[LOAD] rows_25bin.npy:", rows.shape)

    # ---------- LS14 ----------
    X14, y14 = make_xy(rows, LS14_WINDOW)
    np.save(os.path.join(DADOS, "X_ls14.npy"), X14)
    np.save(os.path.join(DADOS, "y_ls14.npy"), y14)
    print("[OK] X_ls14 / y_ls14:", X14.shape, y14.shape)

    # ---------- LS15 ----------
    X15, y15 = make_xy(rows, LS15_WINDOW)
    np.save(os.path.join(DADOS, "X_ls15.npy"), X15)
    np.save(os.path.join(DADOS, "y_ls15.npy"), y15)
    print("[OK] X_ls15 / y_ls15:", X15.shape, y15.shape)

    # ---------- LS16 ----------
    X16, y16 = make_xy(rows, LS16_WINDOW)
    np.save(os.path.join(DADOS, "X_ls16.npy"), X16)
    np.save(os.path.join(DADOS, "y_ls16.npy"), y16)
    print("[OK] X_ls16 / y_ls16:", X16.shape, y16.shape)

    # ---------- LS17 ----------
    X17, y17 = make_xy(rows, LS17_WINDOW)
    np.save(os.path.join(DADOS, "X_ls17.npy"), X17)
    np.save(os.path.join(DADOS, "y_ls17.npy"), y17)
    print("[OK] X_ls17 / y_ls17:", X17.shape, y17.shape)

    # ---------- LS18 ----------
    X18, y18 = make_xy(rows, LS18_WINDOW)
    np.save(os.path.join(DADOS, "X_ls18.npy"), X18)
    np.save(os.path.join(DADOS, "y_ls18.npy"), y18)
    print("[OK] X_ls18 / y_ls18:", X18.shape, y18.shape)

    print("\n✔ Todos os datasets LS14/15/16/17/18 gerados com sucesso.")


if __name__ == "__main__":
    build_all()
