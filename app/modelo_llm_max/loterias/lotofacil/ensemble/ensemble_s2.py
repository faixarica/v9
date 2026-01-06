"""
ensemble_s2.py — fAIxaBet Silver
--------------------------------
Combina apenas LS14++ e LS15++.
"""

import numpy as np
from tensorflow.keras.models import load_model

def load_silver(models_dir="models"):
    m14 = load_model(f"{models_dir}/ls14/ls14pp_final.keras")
    m15 = load_model(f"{models_dir}/ls15/ls15pp_final.keras")
    return {"ls14": m14, "ls15": m15}

WEIGHTS = {"ls14": 0.4, "ls15": 0.6}

def ensemble_silver_pred(models, arr):
    out = np.zeros((25,), float)
    for name, model in models.items():
        out += model.predict(arr, verbose=0)[0] * WEIGHTS[name]
    return out / sum(WEIGHTS.values())
