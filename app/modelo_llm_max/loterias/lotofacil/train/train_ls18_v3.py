"""
train_ls18_v3.py — FaixaBet LS18 (meta-model / ensemble neural)
----------------------------------------------------------------
Treina o modelo LS18, pensado como meta-modelo sobre janelas
longas (64 concursos), com arquitetura mais profunda:

    - Conv1D (128 filtros)
    - MaxPooling1D
    - Bidirectional LSTM
    - Dense profunda
    - Saida binaria (25 unidades)

Entrada:
    dados/X_ls18.npy
    dados/y_ls18.npy

Saida:
    models/ls18/ls18_v3.keras

Tambem escreve resumo em:
    summaries/lf_train_summary.txt
"""

import os
import time
from datetime import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS = os.path.join(ROOT, "models", "ls18")
SUMMARIES = os.path.join(ROOT, "summaries")

os.makedirs(MODELS, exist_ok=True)
os.makedirs(SUMMARIES, exist_ok=True)

X_PATH = os.path.join(DADOS, "X_ls18.npy")
Y_PATH = os.path.join(DADOS, "y_ls18.npy")

print("[DEBUG] DADOS:", DADOS)
print("[DEBUG] X_ls18 exists?", os.path.exists(X_PATH))
print("[DEBUG] y_ls18 exists?", os.path.exists(Y_PATH))

def main():
    if not os.path.exists(X_PATH) or not os.path.exists(Y_PATH):
        raise FileNotFoundError("X_ls18.npy / y_ls18.npy nao encontrados. Rode build_lf_datasets.py antes.")

    t0 = time.time()

    X = np.load(X_PATH)
    y = np.load(Y_PATH)

    print("[LOAD] X_ls18:", X.shape)
    print("[LOAD] y_ls18:", y.shape)

    model = models.Sequential([
        layers.Input(shape=(X.shape[1], X.shape[2])),
        layers.Conv1D(128, 3, activation="relu", padding="same"),
        layers.MaxPooling1D(2),
        layers.Conv1D(128, 3, activation="relu", padding="same"),
        layers.MaxPooling1D(2),
        layers.Bidirectional(layers.LSTM(128, return_sequences=False)),
        layers.Dropout(0.3),
        layers.Dense(256, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(25, activation="sigmoid"),
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy")
    model.summary()

    model.fit(
        X, y,
        epochs=60,
        batch_size=32,
        validation_split=0.1,
        verbose=2,
    )

    out_path = os.path.join(MODELS, "ls18_v3.keras")
    model.save(out_path)

    elapsed = time.time() - t0
    size_mb = os.path.getsize(out_path) / (1024 * 1024)

    print(f"\n✔ Modelo LS18 v3 salvo em: {out_path}")
    print(f"⏱ Tempo de treino: {elapsed:.2f} s  |  Tamanho: {size_mb:.2f} MB")

    summary_path = os.path.join(SUMMARIES, "lf_train_summary.txt")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{now} | MODEL=LS18_v3 | PATH={out_path} | "
        f"TIME_SEC={elapsed:.2f} | SIZE_MB={size_mb:.2f}\n"
    )

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(line)

    print(f"[SUMMARY] Linha adicionada em: {summary_path}")


if __name__ == "__main__":
    main()
