"""
train_ls17_v3.py — fAIxaBet LS17 (Janela Moderna)
-------------------------------------------------
Modelo moderno baseado em:
    - CNN 1D
    - LSTM bidimensional
    - Dense binário final

Este modelo é usado como ENGINE da próxima geração (LS18 e V3/V4 futuros).

Dataset:
    - X_ls17.npy
    - y_ls17.npy
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

# ============================================================
# 1. PATHS PADRONIZADOS
# ============================================================
BASE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
DADOS = os.path.join(ROOT, "dados")
MODELS = os.path.join(ROOT, "models", "ls17")

os.makedirs(MODELS, exist_ok=True)

print("[DEBUG] X_ls17 existe?", os.path.exists(os.path.join(DADOS, "X_ls17.npy")))
print("[DEBUG] y_ls17 existe?", os.path.exists(os.path.join(DADOS, "y_ls17.npy")))

# ============================================================
# 2. MAIN
# ============================================================

def main():

    X = np.load(os.path.join(DADOS, "X_ls17.npy"))
    y = np.load(os.path.join(DADOS, "y_ls17.npy"))

    print("[LOAD] X:", X.shape)
    print("[LOAD] y:", y.shape)

    model = models.Sequential([
        layers.Input(shape=(X.shape[1], X.shape[2])),

        layers.Conv1D(64, 3, activation="relu"),
        layers.MaxPooling1D(2),

        layers.LSTM(128, return_sequences=True),
        layers.Dropout(0.3),

        layers.LSTM(64),
        layers.Dropout(0.3),

        layers.Dense(25, activation="sigmoid"),
    ])

    model.compile(optimizer="adam", loss="binary_crossentropy")
    model.summary()

    model.fit(
        X, y,
        epochs=50,
        batch_size=32,
        validation_split=0.1,
        verbose=2
    )

    out_path = os.path.join(MODELS, "ls17_v3.keras")
    model.save(out_path)

    print("\n✔ Modelo LS17 v3 salvo em:", out_path)


if __name__ == "__main__":
    main()
