"""
train_ls16.py — FaixaBet Platinum LS16 (modelo hibrido)
-------------------------------------------------------
Treina o modelo LS16 usando janelas mais longas (64 concursos) e
arquitetura hibrida:

    - Conv1D  (captura padroes locais)
    - LSTM    (captura padroes de sequencia)
    - Dropout
    - Dense   (saida binaria 25 dezenas)

Entrada:
    dados/X_ls16.npy (shape: [N, 64, 25])
    dados/y_ls16.npy (shape: [N, 25])

Saida:
    models/ls16/ls16_platinum.keras

Tambem escreve um resumo em:
    summaries/lf_train_summary.txt
    (uma linha por execucao de treino)
"""

import os
import time
from datetime import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

# ============================================================
# 1. PATHS
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))              # ...\train
ROOT  = os.path.abspath(os.path.join(BASE, "..", "..", ".."))   # ...\modelo_llm_max
DADOS = os.path.join(ROOT, "dados")
MODELS = os.path.join(ROOT, "models", "ls16")
SUMMARIES = os.path.join(ROOT, "summaries")

os.makedirs(MODELS, exist_ok=True)
os.makedirs(SUMMARIES, exist_ok=True)

X_PATH = os.path.join(DADOS, "X_ls16.npy")
Y_PATH = os.path.join(DADOS, "y_ls16.npy")

print("[DEBUG] DADOS:", DADOS)
print("[DEBUG] X_ls16 exists?", os.path.exists(X_PATH))
print("[DEBUG] y_ls16 exists?", os.path.exists(Y_PATH))

# ============================================================
# 2. TRAIN
# ============================================================

def main():
    if not os.path.exists(X_PATH) or not os.path.exists(Y_PATH):
        raise FileNotFoundError("X_ls16.npy / y_ls16.npy nao encontrados. Rode build_lf_datasets.py antes.")

    t0 = time.time()

    X = np.load(X_PATH)
    y = np.load(Y_PATH)

    print("[LOAD] X_ls16:", X.shape)
    print("[LOAD] y_ls16:", y.shape)

    # Modelo hibrido: Conv1D + LSTM
    model = models.Sequential([
        layers.Input(shape=(X.shape[1], X.shape[2])),
        layers.Conv1D(64, 3, activation="relu", padding="same"),
        layers.MaxPooling1D(2),
        layers.Conv1D(64, 3, activation="relu", padding="same"),
        layers.Dropout(0.3),
        layers.LSTM(128, return_sequences=False),
        layers.Dropout(0.3),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(25, activation="sigmoid"),
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy")
    model.summary()

    model.fit(
        X, y,
        epochs=40,
        batch_size=32,
        validation_split=0.1,
        verbose=2,
    )

    out_path = os.path.join(MODELS, "ls16_platinum.keras")
    model.save(out_path)

    elapsed = time.time() - t0
    size_mb = os.path.getsize(out_path) / (1024 * 1024)

    print(f"\n✔ Modelo LS16 salvo em: {out_path}")
    print(f"⏱ Tempo de treino: {elapsed:.2f} s  |  Tamanho: {size_mb:.2f} MB")

    # --------- SUMARIO TXT ---------
    summary_path = os.path.join(SUMMARIES, "lf_train_summary.txt")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{now} | MODEL=LS16 | PATH={out_path} | "
        f"TIME_SEC={elapsed:.2f} | SIZE_MB={size_mb:.2f}\n"
    )

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(line)

    print(f"[SUMMARY] Linha adicionada em: {summary_path}")


if __name__ == "__main__":
    main()
