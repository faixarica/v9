"""
make_ls17_dataset_v4.py — fAIxaBet
-----------------------------------
Gera o dataset (X, y) para treino do LS17-v4.

Entrada:
    - dados/ls17_features_v4.npy -> (N, 300)
    - dados/rows_25bin.npy       -> (N, 25)

Saída:
    - dados/X_ls17_v4.npy        -> (M, W, 300)
    - dados/y_ls17_v4.npy        -> (M, 25)

Uso:
    python make_ls17_dataset_v4.py
"""

import os
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))

# 🌎 Caminho correto para a pasta global de dados
DADOS = os.path.abspath(os.path.join(BASE, "..", "..", "..", "dados"))
print(f"[PATH] Pasta de dados: {DADOS}")


WINDOW = 32  # janela temporal

def load(name):
    path = os.path.join(DADOS, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERRO] não encontrado: {path}")
    arr = np.load(path)
    print(f"[LOAD] {name} -> {arr.shape}")
    return arr


def main():
    feats = load("ls17_features_v4.npy")   # (N,300)
    labels = load("rows_25bin.npy")        # (N,25)

    N, F = feats.shape
    if labels.shape[0] != N:
        raise ValueError("Features e labels têm N diferente.")

    X_list, y_list = [], []
    for t in range(WINDOW, N):
        X_list.append(feats[t-WINDOW:t])
        y_list.append(labels[t])

    X = np.array(X_list)
    y = np.array(y_list)

    np.save(os.path.join(DADOS, "X_ls17_v4.npy"), X)
    np.save(os.path.join(DADOS, "y_ls17_v4.npy"), y)

    print(f"[OK] X_ls17_v4.npy -> {X.shape}")
    print(f"[OK] y_ls17_v4.npy -> {y.shape}")

if __name__ == "__main__":
    main()
