# -*- coding: utf-8 -*-
"""
validate_ms17_ens_v1.py
Validação comparativa FINAL da Mega-Sena:

- Baseline estatístico
- MS17-v5 (neural)
- MS17-ENS-v1 (ensemble)

Decide produção.
"""

import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf

# ============================================================
# 🔧 PATH do projeto
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ============================================================
# Imports internos
# ============================================================
from loterias.megasena.validate.baseline_ms_mega import (
    compute_baseline_scores,
    sample_k,
)
from loterias.megasena.ensemble.ms17_ens_v1 import MS17EnsembleV1

# ============================================================
# Paths
# ============================================================
DATA_DIR = os.path.join(ROOT_DIR, "dados_m")
MODEL_V5 = os.path.join(ROOT_DIR, "models", "recent", "ms17_v5.keras")

ROWS_PATH  = os.path.join(DATA_DIR, "rows_60bin.npy")
FEATS_PATH = os.path.join(DATA_DIR, "ms17_features_v4.npy")

# ============================================================
# Config validação
# ============================================================
K = 6
SEED = 123
VAL_START = 2000        # janela walk-forward
VAL_END = None          # até o fim

# ============================================================
def hits(pred, true_row):
    return int(np.intersect1d(pred, true_row.nonzero()[0]).size)

# ============================================================
def main():
    print("📥 Carregando dados...")
    rows = np.load(ROWS_PATH)      # (N,60)
    X = np.load(FEATS_PATH)        # (N,F)

    N = rows.shape[0]
    val_end = VAL_END or (N - 1)

    print("🧠 Carregando MS17-v5...")
    model_v5 = tf.keras.models.load_model(MODEL_V5)

    print("🧠 Inicializando Ensemble MS17-ENS-v1...")
    ens = MS17EnsembleV1(MODEL_V5)

    records = []

    for i in range(VAL_START, val_end):
        true = rows[i]

        # ---------------------------
        # Baseline
        # ---------------------------
        p_base = compute_baseline_scores(rows, i)
        pred_base = sample_k(p_base, k=K, seed=SEED + i)
        h_base = hits(pred_base, true)

        # ---------------------------
        # MS17-v5
        # ---------------------------
        logits = model_v5.predict(X[i:i+1], verbose=0)[0]
        probs_v5 = 1.0 / (1.0 + np.exp(-logits))
        probs_v5 = probs_v5 / (probs_v5.sum() + 1e-12)

        pred_v5 = sample_k(probs_v5, k=K, seed=SEED + i)
        h_v5 = hits(pred_v5, true)

        # ---------------------------
        # Ensemble
        # ---------------------------
        pred_ens, _ = ens.sample(rows, X, i, seed=SEED + i)
        h_ens = hits(pred_ens, true)

        records.append({
            "idx": i,
            "baseline": h_base,
            "ms17_v5": h_v5,
            "ms17_ens_v1": h_ens,
        })

    df = pd.DataFrame(records)

    # ========================================================
    # Sumário
    # ========================================================
    summary = []
    for col in ["baseline", "ms17_v5", "ms17_ens_v1"]:
        s = df[col]
        summary.append({
            "modelo": col,
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

    out_csv = os.path.join(ROOT_DIR, "models", "ms17_validate_ens_v1.csv")
    df_sum.to_csv(out_csv, index=False)

    print("\n📊 RESULTADO FINAL (DECISÃO)")
    print(df_sum)
    print("\n💾 CSV salvo em:", out_csv)

# ============================================================
if __name__ == "__main__":
    main()
