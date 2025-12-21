"""
train_ls15pp.py — Modelo LS15++ (Plano GOLD)
--------------------------------------------
Baseado em janela de 50 concursos.
"""

import os, time
from datetime import datetime
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS = os.path.join(ROOT, "models", "ls15pp")
SUMMARIES = os.path.join(ROOT, "summaries")

os.makedirs(MODELS, exist_ok=True)
os.makedirs(SUMMARIES, exist_ok=True)

ROWS = os.path.join(DADOS, "rows_25bin.npy")

def main():
    if not os.path.exists(ROWS):
        raise FileNotFoundError("rows_25bin não encontrado.")

    t0 = time.time()
    rows = np.load(ROWS)
    WINDOW = 50

    X, y = [], []
    for i in range(WINDOW, len(rows)):
        X.append(rows[i-WINDOW:i])
        y.append(rows[i])
    X, y = np.array(X), np.array(y)

    model = models.Sequential([
        layers.Input((WINDOW, 25)),
        layers.LSTM(128, return_sequences=False),
        layers.Dense(128, activation="relu"),
        layers.Dense(25, activation="sigmoid")
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy")

    model.fit(X, y, epochs=40, batch_size=32, validation_split=0.1, verbose=2)

    out_path = os.path.join(MODELS, "ls15pp_final.keras")
    model.save(out_path)

    elapsed = time.time() - t0
    size_mb = os.path.getsize(out_path)/(1024*1024)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(os.path.join(SUMMARIES, "lf_train_summary.txt"), "a", encoding="utf-8") as f:
        f.write(
            f"DATE={now} | MODEL=ls15pp | PLAN=Gold | PATH={out_path} | "
            f"TIME_SEC={elapsed:.2f} | SIZE_MB={size_mb:.2f}\n"
        )

    print("✔ Modelo LS15++ salvo:", out_path)


if __name__ == "__main__":
    main()
