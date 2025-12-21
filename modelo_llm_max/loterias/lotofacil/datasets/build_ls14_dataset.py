"""
build_ls14_dataset.py — fAIxaBet Lotofácil
------------------------------------------
Gera dataset simples para LS14++ usando somente rows_25bin.
Ideal para modelos leves (Silver).

Saída:
    dados/X_ls14.npy
    dados/y_ls14.npy
"""

import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "..", "..", "dados")
WINDOW = 25

def main():
    rows = np.load(os.path.join(DADOS, "rows_25bin.npy"))
    X, y = [], []

    for i in range(WINDOW, len(rows)):
        X.append(rows[i-WINDOW:i])
        y.append(rows[i])

    X = np.array(X)
    y = np.array(y)

    np.save(os.path.join(DADOS, "X_ls14.npy"), X)
    np.save(os.path.join(DADOS, "y_ls14.npy"), y)

    print("[OK] X_ls14.npy", X.shape)
    print("[OK] y_ls14.npy", y.shape)

if __name__ == "__main__":
    main()
