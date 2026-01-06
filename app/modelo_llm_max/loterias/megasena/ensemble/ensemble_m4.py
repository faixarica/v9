"""
ensemble_m4.py — Mega-Sena Platinum
-----------------------------------
Combina MS14/MS15/MS16 e MS17-v4.
"""

import numpy as np
from tensorflow.keras.models import load_model

WEIGHTS = {
    "ms14": 0.1,
    "ms15": 0.2,
    "ms16": 0.2,
    "ms17_v4": 0.5,
}

def load_megaplatinum(models_dir="models"):
    return {
        "ms14": load_model(f"{models_dir}/ms14/ms14pp_final.keras"),
        "ms15": load_model(f"{models_dir}/ms15/ms15pp_final.keras"),
        "ms16": load_model(f"{models_dir}/ms16/ms16_final.keras"),
        "ms17_v4": load_model(f"{models_dir}/ms17_v4/ms17_v4_transformer.keras"),
    }

def ensemble_ms_pred(models, seq):
    out = np.zeros((60,), float)
    for name, model in models.items():
        pred = model.predict(seq, verbose=0)[0]
        out += pred * WEIGHTS[name]
    return out / sum(WEIGHTS.values())
