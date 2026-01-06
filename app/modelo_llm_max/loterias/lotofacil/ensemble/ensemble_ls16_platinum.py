"""
ensemble_ls16_platinum.py — Platinum A (Ensemble LS14++ / LS15++ / LS16)
------------------------------------------------------------------------
Gera palpites usando um ensemble simples de 3 modelos:

    - LS14++  -> models/ls14pp/ls14pp_final.keras
    - LS15++  -> models/ls15pp/ls15pp_final.keras
    - LS16    -> models/ls16/ls16_platinum.keras

Combinação:
    p_final = w14 * p14 + w15 * p15 + w16 * p16

Saída:
    - Palpites impressos no console

Uso:
    python ensemble_ls16_platinum.py --n 10
        -> gera 10 palpites usando o último histórico disponível
"""

import os
import argparse
import numpy as np
import tensorflow as tf

# ============================================================
# 1. PATHS PADRONIZADOS
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS_ROOT = os.path.join(ROOT, "models")

ROWS_PATH = os.path.join(DADOS, "rows_25bin.npy")

MODEL_PATHS = {
    "ls14pp": os.path.join(MODELS_ROOT, "ls14pp", "ls14pp_final.keras"),
    "ls15pp": os.path.join(MODELS_ROOT, "ls15pp", "ls15pp_final.keras"),
    "ls16"  : os.path.join(MODELS_ROOT, "ls16",   "ls16_platinum.keras"),
}

WEIGHTS = {
    "ls14pp": 0.3,
    "ls15pp": 0.4,
    "ls16"  : 0.3,
}

WINDOW = 50     # janela usada pelo LS15++ (a maior do conjunto)
DEZENAS_POR_JOGO = 15


def proba_to_dezenas(p: np.ndarray, k: int = DEZENAS_POR_JOGO):
    """Converte vetor de probabilidades (25,) em lista de dezenas (1–25)."""
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
    """
    Usa as últimas 'WINDOW' linhas de rows para gerar 1 palpite
    via ensemble.
    """
    bloco = rows[-WINDOW:]
    X = bloco.reshape(1, WINDOW, 25)

    p14 = modelos["ls14pp"].predict(X, verbose=0)[0]
    p15 = modelos["ls15pp"].predict(X, verbose=0)[0]
    p16 = modelos["ls16"].predict(X,   verbose=0)[0]

    p_final = (
        WEIGHTS["ls14pp"] * p14 +
        WEIGHTS["ls15pp"] * p15 +
        WEIGHTS["ls16"]   * p16
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

    print(f"\n=== ENSEMBLE PLATINUM A (LS16) — {args.n} palpites ===")
    for i in range(args.n):
        dezenas = gerar_palpite(modelos, rows)
        print(f"Jogo {i+1:02d}: {dezenas}")


if __name__ == "__main__":
    main()
