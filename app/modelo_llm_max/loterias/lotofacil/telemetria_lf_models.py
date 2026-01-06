"""
telemetria_lf_models.py — Avaliação automática dos modelos Lotofácil
--------------------------------------------------------------------
Simula um backtest "walk-forward", em que:

    - Para cada dia i (a partir de WINDOW),
      o modelo recebe o histórico [i-WINDOW : i]
      e tenta prever o concurso i.

    - Compara a predição com o resultado real de i
      e conta quantos acertos (0 a 15).

Entrega:
    - Média de acertos
    - Distribuição de acertos (0 a 15)
    - Percentual de jogos com >= 11, 12, 13, 14

Uso:
    python telemetria_lf_models.py --model ls14pp --last_n 500

Modelos suportados:
    - ls14      -> models/ls14/ls14_base.keras
    - ls14pp    -> models/ls14pp/ls14pp_final.keras
    - ls15pp    -> models/ls15pp/ls15pp_final.keras
    - ls16      -> models/ls16/ls16_platinum.keras
    - ls17      -> models/ls17/ls17_v3.keras
    - ls18      -> models/ls18/ls18_v3.keras
"""

import os
import argparse
import numpy as np
import tensorflow as tf

try:
    from tabulate import tabulate
    USE_TABULATE = True
except ImportError:
    USE_TABULATE = False

# ============================================================
# 1. PATHS E CONFIG
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS_ROOT = os.path.join(ROOT, "models")

ROWS_PATH = os.path.join(DADOS, "rows_25bin.npy")

MODEL_CONFIG = {
    "ls14": {
        "path": os.path.join(MODELS_ROOT, "ls14",   "ls14_base.keras"),
        "window": 32,
    },
    "ls14pp": {
        "path": os.path.join(MODELS_ROOT, "ls14pp", "ls14pp_final.keras"),
        "window": 25,
    },
    "ls15pp": {
        "path": os.path.join(MODELS_ROOT, "ls15pp", "ls15pp_final.keras"),
        "window": 50,
    },
    "ls16": {
        "path": os.path.join(MODELS_ROOT, "ls16",   "ls16_platinum.keras"),
        "window": 64,
    },
    "ls17": {
        "path": os.path.join(MODELS_ROOT, "ls17",   "ls17_v3.keras"),
        "window": 64,
    },
    "ls18": {
        "path": os.path.join(MODELS_ROOT, "ls18",   "ls18_v3.keras"),
        "window": 64,
    },
}


def run_backtest(model_key: str, last_n: int | None = None):
    if model_key not in MODEL_CONFIG:
        raise ValueError(f"Modelo desconhecido: {model_key}")

    cfg = MODEL_CONFIG[model_key]
    path = cfg["path"]
    window = cfg["window"]

    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERRO] Modelo não encontrado em: {path}")
    if not os.path.exists(ROWS_PATH):
        raise FileNotFoundError(f"[ERRO] rows_25bin.npy não encontrado em: {ROWS_PATH}")

    rows = np.load(ROWS_PATH)
    print("[LOAD] rows_25bin:", rows.shape)

    if last_n is not None and last_n > 0:
        if last_n + window > len(rows):
            raise ValueError(f"last_n muito grande, rows tem só {len(rows)} linhas")
        rows = rows[-(last_n + window):]
        print(f"[INFO] Usando últimos {last_n} concursos para avaliação.")

    model = tf.keras.models.load_model(path)
    print(f"[LOAD] Modelo {model_key} <- {path}")
    print(f"[INFO] WINDOW={window}")

    hits_list = []

    # walk-forward: predizer concurso i a partir de [i-window:i]
    for i in range(window, len(rows)):
        hist = rows[i - window:i]
        true_next = rows[i]

        X = hist.reshape(1, window, 25)
        proba = model.predict(X, verbose=0)[0]
        pred_bin = (proba >= 0.5).astype(int)

        hits = int(np.sum((pred_bin == 1) & (true_next == 1)))
        hits_list.append(hits)

    hits_array = np.array(hits_list)
    mean_hits = hits_array.mean()

    # distribuição
    dist = {k: int(np.sum(hits_array == k)) for k in range(0, 16)}

    total = len(hits_array)
    def pct_ge(k):
        return 100.0 * np.sum(hits_array >= k) / total if total > 0 else 0.0

    stats = {
        "mean_hits": float(mean_hits),
        "pct_ge_11": pct_ge(11),
        "pct_ge_12": pct_ge(12),
        "pct_ge_13": pct_ge(13),
        "pct_ge_14": pct_ge(14),
        "total_jogos": total,
        "dist": dist,
    }
    return stats


def print_stats(model_key: str, stats: dict):
    print(f"\n=== TELEMETRIA {model_key.upper()} ===")
    print(f"Total de jogos simulados: {stats['total_jogos']}")
    print(f"Média de acertos       : {stats['mean_hits']:.2f}")
    print(f"Pct >= 11              : {stats['pct_ge_11']:.2f}%")
    print(f"Pct >= 12              : {stats['pct_ge_12']:.2f}%")
    print(f"Pct >= 13              : {stats['pct_ge_13']:.2f}%")
    print(f"Pct >= 14              : {stats['pct_ge_14']:.2f}%")

    rows_table = []
    for k in range(0, 16):
        rows_table.append([k, stats["dist"][k]])

    if USE_TABULATE:
        print("\nDistribuição de acertos:")
        print(tabulate(rows_table, headers=["Acertos", "Qtde"], tablefmt="github"))
    else:
        print("\nDistribuição de acertos:")
        for k, q in rows_table:
            print(f"{k:02d}: {q}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Modelo: ls14, ls14pp, ls15pp, ls16, ls17, ls18")
    parser.add_argument("--last_n", type=int, default=None, help="Quantidade de concursos recentes a usar (opcional)")
    args = parser.parse_args()

    stats = run_backtest(args.model, args.last_n)
    print_stats(args.model, stats)


if __name__ == "__main__":
    main()
