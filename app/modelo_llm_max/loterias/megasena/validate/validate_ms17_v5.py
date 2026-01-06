# -*- coding: utf-8 -*-
"""
validate_ms17_v5.py
Validação comparativa:
- Baseline estatístico
- MS17-v5

Gera CSV único com métricas de HITS.
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf

from baseline_ms_mega import compute_baseline_scores, sample_k

# ============================================================
# Paths
# ============================================================
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(ROOT_DIR, "dados_m")
MODEL_PATH = os.path.join(ROOT_DIR, "models", "recent", "ms17_v5.keras")

ROWS_PATH = os.path.join(DATA_DIR, "rows_60bin.npy")
FEATS_PATH = os.path.join(DATA_DIR, "ms17_features_v4.npy")

# ============================================================
# Config validação
# ============================================================
K = 6
SEED = 123
VAL_START = 2000     # início da janela de validação
VAL_END = None       # None = até o final

# ============================================================
def hits(pred, true_row):
    return int(np.intersect1d(pred, true_row.nonzero()[0]).size)

def main():
    print("📥 Carregando dados...")
    rows = np.load(ROWS_PATH)          # (N,60)
    X = np.load(FEATS_PATH)            # (N,F)

    N = rows.shape[0]
    val_end = VAL_END or (N - 1)

    print("🧠 Carregando modelo MS17-v5...")
    model = tf.keras.models.load_model(MODEL_PATH)

    records = []

    for i in range(VAL_START, val_end):
        true = rows[i]

        # ---------------------------
        # Baseline
        # ---------------------------
        s_base = compute_baseline_scores(rows, i)
        pred_base = sample_k(s_base, k=K, seed=SEED + i)
        h_base = hits(pred_base, true)

        # ---------------------------
        # MS17-v5
        # ---------------------------
        logits = model.predict(X[i:i+1], verbose=0)[0]
        probs = 1 / (1 + np.exp(-logits))
        probs = probs / probs.sum()

        pred_nn = sample_k(probs, k=K, seed=SEED + i)
        h_nn = hits(pred_nn, true)

        records.append({
            "idx": i,
            "baseline_hits": h_base,
            "ms17_v5_hits": h_nn,
        })

    df = pd.DataFrame(records)

    # métricas agregadas
    summary = []
    for col in ["baseline_hits", "ms17_v5_hits"]:
        s = df[col]
        summary.append({
            "modelo": col.replace("_hits", ""),
            "media_hits": s.mean(),
            "p50": s.quantile(0.50),
            "p75": s.quantile(0.75),
            "p90": s.quantile(0.90),
            ">=3": int((s >= 3).sum()),
            ">=4": int((s >= 4).sum()),
            ">=5": int((s >= 5).sum()),
            "6": int((s >= 6).sum()),
        })

    df_sum = pd.DataFrame(summary)

    out_csv = os.path.join(ROOT_DIR, "models", "ms17_validate_summary.csv")
    df_sum.to_csv(out_csv, index=False)

    print("\n📊 RESULTADO FINAL")
    print(df_sum)
    print("\n💾 CSV salvo em:", out_csv)

if __name__ == "__main__":
    main()
