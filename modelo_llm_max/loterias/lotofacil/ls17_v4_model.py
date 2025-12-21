"""
ls17_v4_model.py — Arquitetura Transformer LS17-v4
--------------------------------------------------

Versão: 4.0
Autor: fAIxaBet (2025)

Model:
    Entrada: (WINDOW, 275 features)
    Saída:   vetor (25,) com probabilidades da Lotofácil
"""

from tensorflow.keras import layers, models

def build_ls17_v4_model(window: int, feat_dim: int = 275):
    inp = layers.Input((window, feat_dim))
    x = layers.LayerNormalization()(inp)
    x = layers.MultiHeadAttention(num_heads=4, key_dim=128)(x, x)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(256, activation="relu")(x)
    out = layers.Dense(25, activation="sigmoid")(x)
    return models.Model(inp, out)
