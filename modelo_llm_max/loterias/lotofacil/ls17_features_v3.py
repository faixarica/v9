# ============================================================
# FILE: ls17_features_v3.py
# Gera features LS17-v3 (150 features por concurso) + labels (25)
#
# Saída: dados/ls17_features_v3.npy  -> shape (N, 175)
#   [:150]  = features contínuas da Lotofácil
#   [150:]  = labels binárias (25 dezenas, 0/1)
#
# Uso:
#   cd C:\Faixabet\V8\modelo_llm_max
#   python ls17_features_v3.py
#
# Pré-requisitos (gerados por prepare_real_data_db.py):
#   dados/rows_25bin.npy  -> (N, 25)
# ============================================================

import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")

def rolling_mean(mat: np.ndarray, window: int) -> np.ndarray:
    """
    Média deslizante simples por coluna.
    mat: [N, F]
    retorna: [N, F]
    """
    N, F = mat.shape
    out = np.zeros((N, F), dtype=np.float32)
    for i in range(N):
        start = max(0, i - window + 1)
        out[i] = mat[start:i+1].mean(axis=0)
    return out.astype(np.float32)

def main():
    rows_path = os.path.join(DADOS_DIR, "rows_25bin.npy")
    if not os.path.exists(rows_path):
        raise FileNotFoundError(f"rows_25bin.npy não encontrado em {rows_path}")

    rows = np.load(rows_path).astype(np.float32)  # (N, 25)
    N, F = rows.shape
    if F != 25:
        raise ValueError(f"rows_25bin.npy deve ter 25 colunas, veio {F}")

    print(f"[LS17-v3] rows_25bin.npy -> shape={rows.shape}")

    # ---------- 1) Freq global acumulada ----------
    cum_hits = np.cumsum(rows, axis=0)           # [N,25]
    t_idx = np.arange(1, N + 1, dtype=np.float32)[:, None]  # [N,1]
    freq_global = cum_hits / t_idx               # [N,25]

    # ---------- 2) Freq 30 últimos concursos ----------
    freq_30 = rolling_mean(rows, window=30)      # [N,25]

    # ---------- 3) Freq 90 últimos concursos ----------
    freq_90 = rolling_mean(rows, window=90)      # [N,25]

    # ---------- 4) Gaps (concursos desde o último hit) ----------
    gaps = np.zeros_like(rows, dtype=np.float32)
    last_hit = np.full(F, -1, dtype=np.int32)

    for i in range(N):
        mask = rows[i].astype(bool)
        last_hit[mask] = i
        gaps[i] = i - last_hit   # se nunca saiu -> grande positivo

    gaps_norm = np.tanh(gaps / 30.0)             # normaliza em [-1,1]

    # ---------- 5) Indicador se saiu no concurso anterior ----------
    prev = np.zeros_like(rows, dtype=np.float32)
    prev[1:] = rows[:-1]

    # ---------- 6) Momentum: freq_10 - freq_40 ----------
    freq_10 = rolling_mean(rows, window=10)
    freq_40 = rolling_mean(rows, window=40)
    momentum = freq_10 - freq_40                 # [-1,1] aprox

    # Empilha: 6 blocos de 25 = 150 features
    features = np.concatenate(
        [freq_global, freq_30, freq_90, gaps_norm, prev, momentum],
        axis=1
    ).astype(np.float32)

    assert features.shape == (N, 150), f"Esperado (N,150), veio {features.shape}"

    # Labels = própria rows_25bin (último concurso como label)
    labels = rows.astype(np.float32)             # (N,25)

    data = np.concatenate([features, labels], axis=1)  # (N, 150+25=175)

    out_path = os.path.join(DADOS_DIR, "ls17_features_v3.npy")
    np.save(out_path, data)

    print("[LS17-v3] ls17_features_v3.npy gerado com sucesso!")
    print(f"          shape={data.shape}")
    print(f"          arquivo: {out_path}")

if __name__ == "__main__":
    main()


# ============================================================
# FILE: synthetic_pretrain_ls17_v3.py
# Gera dataset sintético para pré-treino do LS17-v3:
#
#   X_synth: (M, 150) -> synthetic_ls17_v3_x.npy
#   y_synth: (M, 25)  -> synthetic_ls17_v3_y.npy
#
# Ideia: X é ruído gaussian + estrutura; y são top-15 probabilidades
# artificiais derivadas de X (auto-supervisão barata).
#
# Uso:
#   cd C:\Faixabet\V8\modelo_llm_max
#   python synthetic_pretrain_ls17_v3.py --samples 20000
# ============================================================

import os
import argparse
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")

def generate_synthetic_xy(num_samples: int, input_dim: int = 150, num_classes: int = 25):
    """
    Gera (X, y) sintéticos estáveis, sem gambiarra de broadcasting.

    X: [M, 150]  (features contínuas)
    y: [M, 25]   (labels binárias com exatamente 15 '1' por linha)
    """
    # Ruído base
    X = np.random.normal(loc=0.0, scale=1.0, size=(num_samples, input_dim)).astype(np.float32)

    # Projeção linear + ruído para produzir logits por dezena
    W = np.random.normal(0, 0.4, size=(input_dim, num_classes)).astype(np.float32)
    b = np.random.normal(0, 0.1, size=(num_classes,)).astype(np.float32)

    logits = X @ W + b  # [M,25]
    probs = 1.0 / (1.0 + np.exp(-logits))  # sigmoid

    # Top-15 -> binariza
    y_bin = np.zeros_like(probs, dtype=np.float32)
    idx_topk = np.argpartition(probs, -15, axis=1)[:, -15:]
    rows_idx = np.arange(num_samples)[:, None]
    y_bin[rows_idx, idx_topk] = 1.0

    return X, y_bin

def main_synth():
    parser = argparse.ArgumentParser(description="Pré-treino sintético LS17-v3 (Lotofácil)")
    parser.add_argument("--samples", type=int, default=20000, help="Qtd de amostras sintéticas")
    args = parser.parse_args()

    print("========================================")
    print(" Pré-treino sintético LS17-v3 (setup)")
    print("========================================")
    print(f"[sintético] Gerando {args.samples} sequências estáticas...")

    X, y = generate_synthetic_xy(args.samples)

    os.makedirs(DADOS_DIR, exist_ok=True)
    x_path = os.path.join(DADOS_DIR, "synthetic_ls17_v3_x.npy")
    y_path = os.path.join(DADOS_DIR, "synthetic_ls17_v3_y.npy")

    np.save(x_path, X)
    np.save(y_path, y)

    print(f"[OK] synthetic_ls17_v3_x.npy -> {X.shape} salvo em {x_path}")
    print(f"[OK] synthetic_ls17_v3_y.npy -> {y.shape} salvo em {y_path}")

if __name__ == "__main__" and False:
    # Evita conflito de __main__ com outros arquivos deste bloco.
    main_synth()
