# validate_ensembles.py — Validação S2 / G3 / V4
# -----------------------------------------------------
# Testa TODOS os ensembles:
#   ✔ S2  (Silver)
#   ✔ G3  (Gold)
#   ✔ V4  (Platinum)
#
# Calcula média de acertos de 11 a 15 dezenas.
#
# Autor: fAIxaBet — 2025-12

import numpy as np
from tensorflow.keras.models import load_model
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "..", "..", "dados")
MODELS = os.path.join(BASE, "..", "..", "..", "models")

# -------------------------------------------------------------------
# CONFIGURAÇÃO DOS CONJUNTOS DE MODELOS
# -------------------------------------------------------------------

ENSEMBLES = {
    "S2": {
        "pesos": {"ls14": 1.0, "ls15": 1.0},
        "paths": {
            "ls14": os.path.join(MODELS, "ls14", "ls14pp_final.keras"),
            "ls15": os.path.join(MODELS, "ls15", "ls15pp_final.keras"),
        },
    },
    "G3": {
        "pesos": {"ls14": 1.0, "ls15": 1.0, "ls16": 1.5},
        "paths": {
            "ls14": os.path.join(MODELS, "ls14", "ls14pp_final.keras"),
            "ls15": os.path.join(MODELS, "ls15", "ls15pp_final.keras"),
            "ls16": os.path.join(MODELS, "ls16", "ls16_final.keras"),
        },
    },
    "V4": {
        "pesos": {"ls14": 1.0, "ls15": 1.0, "ls16": 1.0, "ls17_v4": 2.0},
        "paths": {
            "ls14": os.path.join(MODELS, "ls14", "ls14pp_final.keras"),
            "ls15": os.path.join(MODELS, "ls15", "ls15pp_final.keras"),
            "ls16": os.path.join(MODELS, "ls16", "ls16_final.keras"),
            "ls17_v4": os.path.join(MODELS, "ls17_v4", "ls17_v4_transformer.keras"),
        },
    },
}

# -------------------------------------------------------------------
# CARREGA MODELOS
# -------------------------------------------------------------------

def load_all(models_paths: dict):
    modelos = {}
    for name, path in models_paths.items():
        if not os.path.exists(path):
            raise FileNotFoundError(f"Modelo ausente: {path}")
        modelos[name] = load_model(path)
    return modelos


# -------------------------------------------------------------------
# LÓGICA DO ENSEMBLE (igual ao palpites.py)
# -------------------------------------------------------------------

def combine(models, pesos, X_seq, last_vec):
    total = np.zeros(25, dtype=float)
    soma = sum(pesos.values())

    for name, model in models.items():
        if name == "ls17_v4":
            prob = model.predict(X_seq, verbose=0)[0]
        else:
            prob = model.predict(last_vec, verbose=0)[0]

        total += prob * pesos.get(name, 1.0)

    return total / soma


# -------------------------------------------------------------------
# VALIDAÇÃO
# -------------------------------------------------------------------

def validar_ensemble(tipo: str):
    print(f"\n🔍 Validando ensemble: {tipo}")

    config = ENSEMBLES[tipo]
    modelos = load_all(config["paths"])
    pesos = config["pesos"]

    rows = np.load(os.path.join(DADOS, "rows_25bin.npy"))
    feats = np.load(os.path.join(DADOS, "ls17_features_v4.npy"))

    W = 32
    acertos = []

    for i in range(W, len(rows)):
        seq = feats[i-W:i][None, ...]     # (1,32,F)
        last = feats[i-1][None, ...]      # (1,F)
        real = np.where(rows[i] == 1)[0]

        prob = combine(modelos, pesos, seq, last)
        dezenas = prob.argsort()[-15:]

        hit = len(set(dezenas) & set(real))
        acertos.append(hit)

    media = np.mean(acertos)
    mx = np.max(acertos)

    print(f"📊 Média: {media:.2f} | Máximo: {mx}")
    return media, mx


if __name__ == "__main__":
    for ens in ["S2", "G3", "V4"]:
        validar_ensemble(ens)
