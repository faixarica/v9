"""
synthetic_pretrain_ls17.py — FaixaBet v2.7
Gera X sintético (100 features) e Y (25 bins) para pré-treino LS17-v2.

Evita broadcasting complexo para evitar erros.
"""

import os
import argparse
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
os.makedirs(DADOS_DIR, exist_ok=True)

# ------------------------------------------------------------
#  NOVA VERSÃO ULTRA SEGUDA DO GERADOR SINTÉTICO
# ------------------------------------------------------------
def generate_synthetic_xy(n_samples=20000, seq_len=120):
    """
    Gera dataset sintético robusto, SEM indexing complexo.
    X: (N, seq_len, 100)
    y: (N, 25)
    """

    print(f"[sintético] Gerando {n_samples} sequências sintéticas...")

    # X base totalmente randômico
    X = np.random.normal(0, 1, size=(n_samples, seq_len, 100)).astype(np.float32)

    # 🔥 criar "tendências simples", SEM broadcasting
    trend_up = np.linspace(0, 1.5, seq_len).astype(np.float32)
    trend_dn = np.linspace(1.0, 0.0, seq_len).astype(np.float32)

    for i in range(n_samples):

        # algumas features sobem, outras descem
        hot_cols = np.random.choice(100, size=8, replace=False)
        cold_cols = np.random.choice(100, size=8, replace=False)

        for col in hot_cols:
            X[i, :, col] += trend_up

        for col in cold_cols:
            X[i, :, col] -= trend_dn

    # 🔥 Agora o alvo Y: (N, 25) — one-hot
    probs = np.random.rand(n_samples, 25)
    probs /= probs.sum(axis=1, keepdims=True)

    y = np.zeros_like(probs, dtype=np.float32)
    idx = np.argmax(probs, axis=1)
    y[np.arange(n_samples), idx] = 1.0

    return X, y


# CLI
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=20000)
    p.add_argument("--seq_len", type=int, default=120)
    return p.parse_args()


def main():
    args = parse_args()

    print("========================================")
    print("   Pré-treino sintético LS17-v2")
    print("========================================")

    X, y = generate_synthetic_xy(args.samples, args.seq_len)

    np.save(os.path.join(DADOS_DIR, "synthetic_ls17_x.npy"), X)
    np.save(os.path.join(DADOS_DIR, "synthetic_ls17_y.npy"), y)

    print("\n✔ synthetic_ls17_x.npy salvo!")
    print("✔ synthetic_ls17_y.npy salvo!")
    print("\nAgora execute:")
    print("   python train_ls17_v2.py --pretrain --window 120 --last_n 2500")


if __name__ == "__main__":
    main()
