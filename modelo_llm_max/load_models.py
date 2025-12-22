import os

# =========================================================
# Caminhos
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# nova estrutura: modelo_llm_max/models/...
MODELS_DIR = os.path.join(BASE_DIR, "models")


# cache em memória (igual V8)
_cached = {}


# =========================================================
# TensorFlow lazy-load (CRÍTICO)
# =========================================================

def _get_tf():
    """
    Importa TensorFlow apenas quando realmente necessário.
    Evita crash no boot do Streamlit (health-check).
    """
    import tensorflow as tf
    return tf


# =========================================================
# Loader genérico com cache
# =========================================================

def load_model(path):
    if path not in _cached:
        print(f"[LOAD MODEL] {path}")

        tf = _get_tf()  # 👈 lazy import aqui (não no topo)

        _cached[path] = tf.keras.models.load_model(
            path,
            compile=False
        )

    return _cached[path]


# =========================================================
# Loaders por família de modelo
# =========================================================


def load_ls14pp():
    return {
        "recent": load_model(
            os.path.join(MODELS_DIR, "ls14pp", "recent_ls14pp_final.keras")
        ),
        "mid": load_model(
            os.path.join(MODELS_DIR, "ls14pp", "mid_ls14pp_final.keras")
        ),
        "global": load_model(
            os.path.join(MODELS_DIR, "ls14pp", "global_ls14pp_final.keras")
        ),
    }

def load_ls15pp():
    return {
        "recent": load_model(
            os.path.join(MODELS_DIR, "ls15pp", "recent_ls15pp_final.keras")
        ),
        "mid": load_model(
            os.path.join(MODELS_DIR, "ls15pp", "mid_ls15pp_final.keras")
        ),
        "global": load_model(
            os.path.join(MODELS_DIR, "ls15pp", "global_ls15pp_final.keras")
        ),
    }


def load_ls16():
    return load_model(
        os.path.join(MODELS_DIR, "ls16", "ls16_platinum.keras")
    )


def load_ls17():
    return load_model(
        os.path.join(MODELS_DIR, "ls17", "ls17_v3.keras")
    )


def load_ls18():
    return load_model(
        os.path.join(MODELS_DIR, "ls18", "ls18_mini.keras")
    )
