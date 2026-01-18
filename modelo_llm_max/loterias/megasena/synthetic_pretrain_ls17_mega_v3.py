"""
Pré-treino sintético LS17-Mega-v3 — 150 feats → 60 labels
Anti-broadcast para qualquer NumPy
"""

import numpy as np
import argparse, os

BASE = os.path.dirname(__file__)
DADOS = os.path.join(os.path.dirname(__file__), "prepare_real", "dados")

def save(arr, name):
    os.makedirs(DADOS, exist_ok=True)   # <-- garante a pasta
    np.save(os.path.join(DADOS, name), arr)


def generate_synth(n_samples, seq_len, n_feat=150, n_lab=60):

    X = np.random.normal(0, 0.3, (n_samples, seq_len, n_feat))
    y = np.zeros((n_samples, n_lab), dtype=np.float32)

    for i in range(n_samples):

        k_hot = np.random.randint(3, 7)
        hot = np.random.choice(n_lab, k_hot, replace=False)

        slope = np.random.uniform(0.3, 1.5)
        trend = np.linspace(0, slope, seq_len).reshape(seq_len)

        for h in hot:
            X[i, :, h] += trend

        y[i, hot] = 1

    return X, y

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=20000)
    p.add_argument("--seq_len", type=int, default=150)
    args = p.parse_args()

    print("==============================")
    print(" Pré-treino sintético Mega v3 ")
    print("==============================")

    X, y = generate_synth(args.samples, args.seq_len)

    save(X, "synthetic_ls17_mega_x.npy")
    save(y, "synthetic_ls17_mega_y.npy")

    print("\nExecute agora:")
    print(" python train_ls17_mega_v3.py --pretrain\n")

if __name__ == "__main__":
    main()