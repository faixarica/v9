"""
ensemble_ls18_platinum.py — Platinum B (Futuro) — Ensemble Neural Profundo
---------------------------------------------------------------------------
Ensemble mais sofisticado combinando:

    - LS15++  -> models/ls15pp/ls15pp_final.keras
    - LS17    -> models/ls17/ls17_v3.keras
    - LS18    -> models/ls18/ls18_v3.keras

Ideia:
    p_final = w15 * p15 + w17 * p17 + w18 * p18

Uso:
    python ensemble_ls18_platinum.py --n 10
"""

import os
import argparse
import numpy as np
import tensorflow as tf

BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS_ROOT = os.path.join(ROOT, "models")

ROWS_PATH = os.path.join(DADOS, "rows_25bin.npy")

MODEL_PATHS = {
    "ls15pp": os.path.join(MODELS_ROOT, "ls15pp", "ls15pp_final.keras"),
    "ls17"  : os.path.join(MODELS_ROOT, "ls17",   "ls17_v3.keras"),
    "ls18"  : os.path.join(MODELS_ROOT, "ls18",   "ls18_v3.keras"),
}

WEIGHTS = {
    "ls15pp": 0.3,
    "ls17"  : 0.3,
    "ls18"  : 0.4,
}

WINDOW = 64
DEZENAS_POR_JOGO = 15


def proba_to_dezenas(p: np.ndarray, k: int = DEZENAS_POR_JOGO):
    idx = np.argsort(p)[::-1][:k]
    dezenas = sorted((idx + 1).tolist())
    return dezenas


def carregar_modelos():
    modelos = {}
    for nome, caminho in MODEL_PATHS.items():
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"[ERRO] Modelo não encontrado: {caminho}")
        modelos[nome] = tf.keras.models.load_model(caminho)
        print(f"[LOAD] {nome} <- {caminho}")
    return modelos


def gerar_palpite(modelos, rows: np.ndarray):
    bloco = rows[-WINDOW:]
    X = bloco.reshape(1, WINDOW, 25)

    p15 = modelos["ls15pp"].predict(X, verbose=0)[0]
    p17 = modelos["ls17"].predict(X,   verbose=0)[0]
    p18 = modelos["ls18"].predict(X,   verbose=0)[0]

    p_final = (
        WEIGHTS["ls15pp"] * p15 +
        WEIGHTS["ls17"]   * p17 +
        WEIGHTS["ls18"]   * p18
    )

    return proba_to_dezenas(p_final)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5, help="Quantidade de palpites a gerar")
    args = parser.parse_args()

    if not os.path.exists(ROWS_PATH):
        raise FileNotFoundError(f"[ERRO] rows_25bin.npy não encontrado em: {ROWS_PATH}")

    rows = np.load(ROWS_PATH)
    print("[LOAD] rows_25bin.npy:", rows.shape)

    if rows.shape[0] < WINDOW:
        raise ValueError(f"[ERRO] rows_25bin tem apenas {rows.shape[0]} linhas; precisa de >= {WINDOW}")

    modelos = carregar_modelos()

    print(f"\n=== ENSEMBLE PLATINUM B (LS18) — {args.n} palpites ===")
    for i in range(args.n):
        dezenas = gerar_palpite(modelos, rows)
        print(f"Jogo {i+1:02d}: {dezenas}")


if __name__ == "__main__":
    main()
