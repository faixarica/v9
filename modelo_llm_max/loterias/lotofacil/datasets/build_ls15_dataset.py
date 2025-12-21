"""
build_ls15_dataset.py — fAIxaBet Lotofácil
------------------------------------------
Usa features v2 (100 features) para gerar dataset do LS15++.

Entrada:
    dados/ls17_features.npy (100 features)
    dados/rows_25bin.npy

Saída:
    dados/X_ls15.npy
    dados/y_ls15.npy
"""

import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "..", "..", "dados")

WINDOW = 32

def main():
    feats = np.load(os.path.join(DADOS, "ls17_features.npy"))
    labels = np.load(os.path.join(DADOS, "rows_25bin.npy"))

    X, y = [], []

    for i in range(WINDOW, len(feats)):
        X.append(feats[i-WINDOW:i])
        y.append(labels[i])

    X = np.array(X)
    y = np.array(y)

    np.save(os.path.join(DADOS, "X_ls15.npy"), X)
    np.save(os.path.join(DADOS, "y_ls15.npy"), y)

    print("[OK] X_ls15.npy", X.shape)
    print("[OK] y_ls15.npy", y.shape)

if __name__ == "__main__":
    main()
