# -*- coding: utf-8 -*-
"""
MS17_V5 Engine Adapter (V8 compatible)

- NÃO muda estrutura existente
- Usa modelo_llm_max
- Isola a Mega-Sena do app
"""

import os
import numpy as np

# reaproveita loaders existentes
from modelo_llm_max.load_models import load_model_safe

# =====================================================
# 🔧 Paths LEGACY (sem ENV obrigatório)
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODELS_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..", "modelo_llm_max", "models")
)

MODEL_NAME = "ms17_v5"   # quando existir
FALLBACK_MODEL = "ms17_v4"


_model = None


def _load():
    global _model
    if _model is not None:
        return

    try:
        _model = load_model_safe(
            model_name=MODEL_NAME,
            models_dir=MODELS_DIR
        )
        print("[MS17_V5_ENGINE] ms17_v5 carregado")
    except Exception as e:
        print("[MS17_V5_ENGINE] fallback ms17_v4:", e)
        _model = load_model_safe(
            model_name=FALLBACK_MODEL,
            models_dir=MODELS_DIR
        )


def predict(features: np.ndarray) -> np.ndarray:
    """
    features já prontas (pipeline existente)
    """
    _load()
    return _model.predict(features)
