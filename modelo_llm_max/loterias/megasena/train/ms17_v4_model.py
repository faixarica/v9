# train_ms17_v4.py — Treinamento do Modelo Mega-Sena MS17-v4
# ------------------------------------------------------------
# Gera o modelo ms17_v4_transformer.keras
#
# Autor: fAIxaBet — 2025-12

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

# ============================================================
# 📂 Paths
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

DADOS = os.path.join(ROOT, "dados")
MODEL_DIR = os.path.join(ROOT, "models", "megasena", "ms17_v4")
MODEL_PATH = os.path.join(MODEL_DIR, "ms17_v4_transformer.keras")

os.makedirs(MODEL_DIR, exist_ok=True)

# ============================================================
# ⚙️ Parâmetros
# ============================================================
W = 32            # janela temporal
D_MODEL = 128
N_HEADS = 4
FF_DIM = 256
DROPOUT = 0.15

EPOCHS = 40
BATCH_SIZE = 32
LR = 1e-3

# ============================================================
# 🔢 Transformer Encoder
# ============================================================
def transformer_block(x, d_model, num_heads, ff_dim, dropout=0.1):
    attn = layers.MultiHeadAttention(
        num_heads=num_heads,
        key_dim=d_model
    )(x, x)
    x = layers.Add()([x, attn])
    x = layers.LayerNormalization(epsilon=1e-6)(x)

    ffn = layers.Dense(ff_dim, activation="relu")(x)
    ffn = layers.Dense(d_model)(ffn)
    x = layers.Add()([x, ffn])
    x = layers.LayerNormalization(epsilon=1e-6)(x)

    return layers.Dropout(dropout)(x)

# ============================================================
# 🧠 Modelo
# ============================================================
def build_model(input_shape):
    inputs = layers.Input(shape=input_shape)

    x = layers.Dense(D_MODEL)(inputs)

    x = transformer_block(x, D_MODEL, N_HEADS, FF_DIM, DROPOUT)
    x = transformer_block(x, D_MODEL, N_HEADS, FF_DIM, DROPOUT)

    x = layers.GlobalAveragePooling1D()(x)

    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.2)(x)

    outputs = layers.Dense(60, activation="sigmoid")(x)

    model = models.Model(inputs, outputs)
    model.compile(
        optimizer=optimizers.Adam(LR),
        loss="binary_crossentropy",
        metrics=["binary_accuracy"]
    )
    return model

# ============================================================
# ▶ Treino
# ============================================================
def main():
    print("\n🚀 Treinando Modelo — Mega-Sena MS17-v4")

    print("[LOAD] Carregando dados...")
    rows60 = np.load(os.path.join(DADOS, "rows_60bin.npy"))          # (N, 60)
    feats  = np.load(os.path.join(DADOS, "ms17_features_v4.npy"))   # (N, F)

    X, Y = [], []
    for i in range(W, len(rows60)):
        X.append(feats[i - W:i])
        Y.append(rows60[i])

    X = np.array(X)
    Y = np.array(Y)

    print(f"[DATA] X={X.shape} | Y={Y.shape}")

    model = build_model(input_shape=X.shape[1:])
    model.summary()

    print("[TRAIN] Iniciando treinamento...")
    model.fit(
        X, Y,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=0.15,
        verbose=2
    )

    print(f"[SAVE] Salvando modelo em:\n  {MODEL_PATH}")
    model.save(MODEL_PATH)

    print("✅ Treinamento finalizado com sucesso.")

# ============================================================
# Execução
# ============================================================
if __name__ == "__main__":
    main()
