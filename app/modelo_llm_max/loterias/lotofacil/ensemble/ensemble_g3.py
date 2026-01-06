"""
ensemble_g3.py — fAIxaBet Gold
------------------------------
Combina LS14, LS15, LS16.
"""

import numpy as np
from tensorflow.keras.models import load_model

def load_gold(models_dir="models"):
    return {
        "ls14": load_model(f"{models_dir}/ls14/ls14pp_final.keras"),
        "ls15": load_model(f"{models_dir}/ls15/ls15pp_final.keras"),
        "ls16": load_model(f"{models_dir}/ls16/ls16_final.keras"),
    }

WEIGHTS = {"ls14": 0.2, "ls15": 0.3, "ls16": 0.5}

def ensemble_gold_pred(models, arr):
    out = np.zeros((25,), float)
    for name, model in models.items():
        out += model.predict(arr, verbose=0)[0] * WEIGHTS[name]
    return out / sum(WEIGHTS.values())
