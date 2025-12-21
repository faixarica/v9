# -*- coding: utf-8 -*-
"""
ms17_ens_v1.py
Ensemble oficial MS17-ENS-v1 (Mega-Sena)

⚠️ ESTE ARQUIVO NÃO É EXECUTÁVEL DIRETAMENTE
Ele deve ser IMPORTADO por:
- validate_ms17_ens_v1.py
- palpites_m.py / palpites.py
"""

import os
import numpy as np
import tensorflow as tf

# ============================================================
# Import seguro do baseline (mesmo projeto)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEGA_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

VALIDATE_DIR = os.path.join(MEGA_DIR, "validate")
if VALIDATE_DIR not in os.sys.path:
    os.sys.path.append(VALIDATE_DIR)

from baseline_ms_mega import compute_baseline_scores

# ============================================================
# Config do ensemble
# ============================================================
W_NEURAL = 0.65
W_BASE   = 0.35
K = 6

# ============================================================
def sample_k(scores, k=6, seed=None):
    rng = np.random.default_rng(seed)
    return rng.choice(60, size=k, replace=False, p=scores)

# ============================================================
class MS17EnsembleV1:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        self.model = tf.keras.models.load_model(model_path)

    def predict_proba(self, rows_hist, X_feat, idx):
        """
        rows_hist : (N,60) histórico real
        X_feat    : (N,F) features
        idx       : índice do concurso alvo
        """

        # ---------------------------
        # Baseline
        # ---------------------------
        p_base = compute_baseline_scores(rows_hist, idx)

        # ---------------------------
        # MS17-v5 (neural)
        # ---------------------------
        logits = self.model.predict(
            X_feat[idx:idx+1],
            verbose=0
        )[0]

        p_nn = 1.0 / (1.0 + np.exp(-logits))
        p_nn = p_nn / (p_nn.sum() + 1e-12)

        # ---------------------------
        # Ensemble
        # ---------------------------
        p_ens = W_NEURAL * p_nn + W_BASE * p_base
        p_ens = p_ens / (p_ens.sum() + 1e-12)

        return p_ens

    def sample(self, rows_hist, X_feat, idx, seed=None):
        p = self.predict_proba(rows_hist, X_feat, idx)
        return sample_k(p, k=K, seed=seed), p
