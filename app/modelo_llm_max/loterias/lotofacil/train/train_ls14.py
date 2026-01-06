"""
train_ls14.py — Modelo LS14 (Plano FREE)
----------------------------------------
Modelo simples LSTM baseado no histórico binário (rows_25bin).
Produz: models/ls14/ls14_base.keras
Grava sumário em summaries/lf_train_summary.txt
"""

import os, time
from datetime import datetime
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

# ============================================================
# Paths
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS = os.path.join(ROOT, "models", "ls14")
SUMMARIES = os.path.join(ROOT, "summaries")

os.makedirs(MODELS, exist_ok=True)
os.makedirs(SUMMARIES, exist_ok=True)

ROWS = os.path.join(DADOS, "rows_25bin.npy")

# ============================================================
# Main
# ============================================================
def main():
    if not os.path.exists(ROWS):
        raise FileNotFoundError(f"rows_25bin.npy não encontrado: {ROWS}")

    t0 = time.time()

    rows = np.load(ROWS)
    print("[LOAD] rows_25bin:", rows.shape)

    WINDOW = 32

    X, y = [], []
    for i in range(WINDOW, len(rows)):
        X.append(rows[i-WINDOW:i])
        y.append(rows[i])
    X = np.array(X)
    y = np.array(y)

    model = models.Sequential([
        layers.Input((WINDOW, 25)),
        layers.LSTM(64, return_sequences=False),
        layers.Dense(25, activation="sigmoid")
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy")

    model.fit(X, y, epochs=40, batch_size=32, validation_split=0.1, verbose=2)

    out_path = os.path.join(MODELS, "ls14_base.keras")
    model.save(out_path)

    # ============================================================
    # Summary .txt
    # ============================================================
    elapsed = time.time() - t0
    size_mb = os.path.getsize(out_path) / (1024*1024)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(os.path.join(SUMMARIES, "lf_train_summary.txt"), "a", encoding="utf-8") as f:
        f.write(
            f"DATE={now} | MODEL=ls14 | PLAN=Free | PATH={out_path} | "
            f"TIME_SEC={elapsed:.2f} | SIZE_MB={size_mb:.2f}\n"
        )

    print("✔ Modelo LS14 salvo:", out_path)


if __name__ == "__main__":
    main()
