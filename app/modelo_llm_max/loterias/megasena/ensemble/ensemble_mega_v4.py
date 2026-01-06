"""
Ensemble LS18-Mega-v3
"""

import numpy as np
import tensorflow as tf
import os
import argparse

BASE = os.path.dirname(__file__)
DADOS = os.path.join(BASE, "dados")
MODELS = os.path.join(BASE, "models", "prod")

def load(name):
    return np.load(os.path.join(DADOS, name))

def load_model(name):
    return tf.keras.models.load_model(os.path.join(MODELS, name))

def binarize(p):
    return (p >= 0.5).astype(int)

def main():

    p = argparse.ArgumentParser()
    p.add_argument("--window", type=int, default=150)
    p.add_argument("--limit", type=int, default=220)
    p.add_argument("--n_test", type=int, default=70)
    args = p.parse_args()

    print("===============================================")
    print(" Avaliação ENSEMBLE Mega-Sena LS18-v3")
    print("===============================================")

    rows = load("rows_60bin.npy")[-args.limit:]

    X = np.array([rows[i-args.window:i] for i in range(args.window, args.window+args.n_test)])
    y = rows[args.window:args.window+args.n_test]

    m14 = load_model("recent_ls14pp_mega_final.keras")
    m15 = load_model("recent_ls15pp_mega_final.keras")
    m17 = load_model("ls17_megasena_v3.keras")

    p14 = binarize(m14.predict(X, verbose=0))
    p15 = binarize(m15.predict(X, verbose=0))

    X17 = np.zeros((args.n_test, args.window, 150))
    X17[:, :, :60] = X
    p17 = binarize(m17.predict(X17, verbose=0))

    p_ens = (p14 + p15 + p17) >= 2

    hits = (p_ens * y).sum(axis=1)
    print(f"Media real: {hits.mean():.2f}")

    out = os.path.join(BASE, "admin", "tests_v3", "ranking_megasena_ls18_v3.csv")
    np.savetxt(out, hits, delimiter=",")
    print(f"[OK] Ranking salvo em {out}")

if __name__ == "__main__":
    main()
