"""
Treinador LS17-Mega-v3
- Pré-treino sintético
- Treino real
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import argparse, os

BASE = os.path.dirname(__file__)
DADOS = os.path.join(BASE, "dados")
MODELS = os.path.join(BASE, "models", "prod")
os.makedirs(MODELS, exist_ok=True)

def load(name):
    return np.load(os.path.join(DADOS, name))

def make_seq(data, win):
    out = []
    for i in range(len(data) - win):
        out.append(data[i:i+win])
    return np.array(out)

def build_model(window, n_feat=150, n_lab=60):

    inp = layers.Input(shape=(window, n_feat))

    x = layers.LayerNormalization()(inp)
    x = layers.MultiHeadAttention(num_heads=4, key_dim=32)(x, x)
    x = layers.Dropout(0.1)(x)
    x = layers.LayerNormalization()(x)

    ff = layers.Dense(256, activation="relu")(x)
    ff = layers.Dense(n_feat)(ff)
    x = layers.Add()([x, ff])
    x = layers.LayerNormalization()(x)

    x = layers.Flatten()(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(0.2)(x)

    out = layers.Dense(n_lab, activation="sigmoid")(x)

    m = models.Model(inp, out)
    m.compile(optimizer="adam", loss="binary_crossentropy")
    return m

def main():

    p = argparse.ArgumentParser()
    p.add_argument("--window", type=int, default=150)
    p.add_argument("--last_n", type=int, default=1800)
    p.add_argument("--epochs", type=int, default=200)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--pretrain", action="store_true")
    args = p.parse_args()

    print("========================================")
    print("🚀 Treino LS17-Mega-v3")
    print("========================================")

    if args.pretrain:
        print("[Pré-treino] Carregando sintético...")
        Xs = load("synthetic_ls17_mega_x.npy")
        ys = load("synthetic_ls17_mega_y.npy")
        model = build_model(args.window)
        model.fit(Xs, ys, epochs=8, batch_size=args.batch, verbose=2)
    else:
        model = build_model(args.window)

    # Treino real
    data = load("ls17_mega_features_v3.npy")

    if args.last_n < len(data):
        data = data[-args.last_n:]

    feats = data[:, :150]
    labs = data[:, -60:]

    X = make_seq(feats, args.window)
    y = labs[args.window:]

    print(f"[REAL] X={X.shape} y={y.shape}")

    model.fit(
        X, y,
        batch_size=args.batch,
        epochs=args.epochs,
        verbose=2
    )

    out = os.path.join(MODELS, "ls17_megasena_v3.keras")
    model.save(out)
    print(f"[OK] Salvo em {out}")

if __name__ == "__main__":
    main()
