import os
import tensorflow as tf

BASE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(BASE, "models")

_cached = {}

def load_model(path):
    if path not in _cached:
        print(f"[LOAD] {path}")
        _cached[path] = tf.keras.models.load_model(path, compile=False)
    return _cached[path]

def load_ls14pp():
    return {
        "recent": load_model(os.path.join(MODELS, "ls14pp", "recent_ls14pp_final.keras")),
        "mid": load_model(os.path.join(MODELS, "ls14pp", "mid_ls14pp_final.keras")),
        "global": load_model(os.path.join(MODELS, "ls14pp", "global_ls14pp_final.keras")),
    }

def load_ls15pp():
    return {
        "recent": load_model(os.path.join(MODELS, "ls15pp", "recent_ls15pp_final.keras")),
        "mid": load_model(os.path.join(MODELS, "ls15pp", "mid_ls15pp_final.keras")),
        "global": load_model(os.path.join(MODELS, "ls15pp", "global_ls15pp_final.keras")),
    }

def load_ls16():
    return load_model(os.path.join(MODELS, "ls16", "ls16_platinum.keras"))

def load_ls17():
    return load_model(os.path.join(MODELS, "ls17", "ls17_v3.keras"))

def load_ls18():
    return load_model(os.path.join(MODELS, "ls18", "ls18_mini.keras"))
    