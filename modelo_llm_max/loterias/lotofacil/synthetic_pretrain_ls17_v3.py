"""
Pré-treino sintético LS17-v3 — 150 features profissionais
Compatível com qualquer versão do NumPy
"""

import numpy as np
import os
import argparse

BASE = os.path.dirname(__file__)
DADOS = os.path.join(BASE, "dados")

def save(arr, name):
    np.save(os.path.join(DADOS, name), arr)
    print(f"[OK] {name} salvo. shape={arr.shape}")

# --------------------------------------
# Gerador sintético anti-broadcast-error
# --------------------------------------
def generate_synthetic_xy(n_samples, seq_len, n_features=150, n_labels=25):

    X = np.random.normal(0, 0.3, size=(n_samples, seq_len, n_features))
    y = np.zeros((n_samples, n_labels), dtype=np.float32)

    for i in range(n_samples):

        # dezenas “quentes” aleatórias
        k_hot = np.random.randint(5, 10)
        hot_idx = np.random.choice(n_labels, k_hot, replace=False)

        # tendência crescente / decrescente
        slope = np.random.uniform(0.4, 1.5)
        trend = np.linspace(0, slope, seq_len).reshape(seq_len, 1)

        # aplica tendência
        for h in hot_idx:
            X[i, :, h] += trend[:, 0]

        # gera rótulo sintético
        y[i, hot_idx] = 1.0

    return X.astype(np.float32), y.astype(np.float32)

# --------------------------------------
# Main
# --------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--seq_len", type=int, default=120)
    args = parser.parse_args()

    print("========================================")
    print(" Pré-treino sintético LS17-v3")
    print("========================================")

    print(f"[sintético] Gerando {args.samples} sequências...")

    X, y = generate_synthetic_xy(args.samples, args.seq_len)

    save(X, "synthetic_ls17_x.npy")
    save(y, "synthetic_ls17_y.npy")

    print("\nAgora execute:")
    print(" python train_ls17_v3.py --pretrain --window 120 --last_n 2500\n")


if __name__ == "__main__":
    main()
