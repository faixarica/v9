"""
make_ms17_dataset_v4.py — FaixaBet Mega-Sena
--------------------------------------------
Gera dataset para MS17-v4.

Entrada:
    - dados/ms17_features_v4.npy  (N, 360)
    - dados/rows_60bin.npy        (N, 60)

Saída:
    - dados/X_ms17_v4.npy
    - dados/y_ms17_v4.npy
"""

import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "..", "..", "dados")

WINDOW = 32  # janela temporal

def load(name):
    p = os.path.join(DADOS, name)
    print("[LOAD]", p)
    return np.load(p)

def main():
    feats = load("ms17_features_v4.npy")
    labels = load("rows_60bin.npy")

    N = min(feats.shape[0], labels.shape[0])
    X, Y = [], []

    for i in range(WINDOW, N):
        X.append(feats[i-WINDOW:i])   # shape (WINDOW, F)
        Y.append(labels[i])           # shape (60,)


    X = np.array(X)
    Y = np.array(Y)

    np.save(os.path.join(DADOS, "X_ms17_v4.npy"), X)
    np.save(os.path.join(DADOS, "y_ms17_v4.npy"), Y)

    print("[OK] X_ms17_v4.npy", X.shape)
    print("[OK] y_ms17_v4.npy", Y.shape)

if __name__ == "__main__":
    main()
