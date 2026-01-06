"""
ensemble_v4.py — fAIxaBet Platinum
----------------------------------
Combina LS14++ + LS15++ + LS16 + LS17-v4.
"""

import numpy as np
from tensorflow.keras.models import load_model

WEIGHTS = {
    "ls14": 0.1,
    "ls15": 0.1,
    "ls16": 0.2,
    "ls17_v4": 0.6,
}

def load_platinum(models_dir="models"):
    return {
        "ls14": load_model(f"{models_dir}/ls14/ls14pp_final.keras"),
        "ls15": load_model(f"{models_dir}/ls15/ls15pp_final.keras"),
        "ls16": load_model(f"{models_dir}/ls16/ls16_final.keras"),
        "ls17_v4": load_model(f"{models_dir}/ls17_v4/ls17_v4_transformer.keras"),
    }

def ensemble_platinum_predict(models, seq_input):
    """
    seq_input = (1, WINDOW, FEATS)
    """
    out = np.zeros((25,), float)
    for name, model in models.items():
        pred = model.predict(seq_input, verbose=0)[0]
        out += pred * WEIGHTS[name]
    return out / sum(WEIGHTS.values())
