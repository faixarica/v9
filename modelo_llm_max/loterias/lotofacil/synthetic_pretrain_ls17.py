# ============================================================
# synthetic_pretrain_ls17.py — Versão FINAL (IMPOSSÍVEL DE FALHAR)
# ============================================================

import numpy as np
import argparse
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
os.makedirs(DADOS_DIR, exist_ok=True)

# ============================================================
#   Função robusta SEM indexação avançada, SEM broadcasting
# ============================================================
def generate_synthetic_xy(n_samples: int, seq_len: int):
    n_feats = 100
    n_labels = 25
    k_hot = 8

    # Matrizes finais
    X = np.zeros((n_samples, seq_len, n_feats), dtype=np.float32)
    Y = np.zeros((n_samples, n_labels), dtype=np.float32)

    for i in range(n_samples):

        # --------------------------------------------------
        # Escolhe features "quentes"
        # --------------------------------------------------
        hot_idx = np.random.choice(n_feats, size=k_hot, replace=False)

        # --------------------------------------------------
        # Gera tendência crescente
        # SEM broadcasting: shape explicitamente controlado
        # --------------------------------------------------
        trend = np.linspace(0, 1.5, seq_len, dtype=np.float32)  # (120,)
        
        # --------------------------------------------------
        # INSERIR tendência sem usar X[i,:,hot_idx]
        # Fazemos feature por feature (100% seguro)
        # --------------------------------------------------
        for h_i, feat in enumerate(hot_idx):
            # Cada feature recebe a tendência
            X[i, :, feat] = trend

        # --------------------------------------------------
        # Ruído estável
        # --------------------------------------------------
        noise = np.random.normal(0, 0.07, size=(seq_len, n_feats)).astype(np.float32)
        X[i] += noise

        # --------------------------------------------------
        # Gera labels sintéticas (15 marcadas)
        # --------------------------------------------------
        y_idx = np.random.choice(n_labels, size=15, replace=False)
        y = np.zeros(n_labels, dtype=np.float32)
        y[y_idx] = 1.0
        Y[i] = y

    return X, Y


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--seq_len", type=int, default=120)
    args = parser.parse_args()

    print("========================================")
    print(" Pré-treino sintético LS17-v2 (FINAL)")
    print("========================================")
    print(f"[sintético] Gerando {args.samples} sequências sintéticas...")

    X, Y = generate_synthetic_xy(args.samples, args.seq_len)

    np.save(os.path.join(DADOS_DIR, "synthetic_ls17_x.npy"), X)
    np.save(os.path.join(DADOS_DIR, "synthetic_ls17_y.npy"), Y)

    print("✔ synthetic_ls17_x.npy salvo")
    print("✔ synthetic_ls17_y.npy salvo")
    print("\nAgora execute:")
    print("   python train_ls17_v2.py --pretrain --window 120 --last_n 2500")


if __name__ == "__main__":
    main()
