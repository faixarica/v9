# -*- coding: utf-8 -*-
"""
Treino oficial MS17-v5 (Mega-Sena)
VERSÃO ROBUSTA – auto-detecção de datasets
"""

import os
import sys
import numpy as np
import tensorflow as tf

from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from ms17_v5_model import build_ms17_v5, compile_ms17_v5

# ============================================================
# 🔧 BASE DIR
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))

print("📂 BASE_DIR :", BASE_DIR)
print("📂 ROOT_DIR :", ROOT_DIR)

# ============================================================
# 🔍 AUTO-DETECÇÃO DOS DADOS
# ============================================================
CANDIDATE_DATA_DIRS = [
    os.path.join(ROOT_DIR, "dados_m"),
    os.path.join(ROOT_DIR, "loterias", "megasena", "prepare_real", "dados"),
    os.path.join(ROOT_DIR, "loterias", "megasena", "datasets"),
]

FEATURE_FILE = "ms17_features_v4.npy"
LABEL_FILE   = "rows_60bin.npy"

DATA_DIR = None

for d in CANDIDATE_DATA_DIRS:
    f_path = os.path.join(d, FEATURE_FILE)
    l_path = os.path.join(d, LABEL_FILE)
    print(f"🔎 Testando: {d}")
    if os.path.exists(f_path) and os.path.exists(l_path):
        DATA_DIR = d
        break

if DATA_DIR is None:
    print("\n❌ ERRO CRÍTICO: datasets não encontrados.")
    print("Arquivos esperados:")
    print(" -", FEATURE_FILE)
    print(" -", LABEL_FILE)
    print("\nDiretórios testados:")
    for d in CANDIDATE_DATA_DIRS:
        print(" -", d)
    sys.exit(1)

FEATURES_PATH = os.path.join(DATA_DIR, FEATURE_FILE)
LABELS_PATH   = os.path.join(DATA_DIR, LABEL_FILE)

print("\n✅ DATASETS ENCONTRADOS")
print("📂 DATA_DIR :", DATA_DIR)
print("📄 FEATURES :", FEATURES_PATH)
print("📄 LABELS   :", LABELS_PATH)

# ============================================================
# 🔧 OUTPUT DO MODELO
# ============================================================
MODELS_DIR = os.path.join(ROOT_DIR, "models", "recent")
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, "ms17_v5.keras")
print("💾 MODEL_OUT:", MODEL_OUT)

# ============================================================
# 🔧 CONFIG TREINO
# ============================================================
BATCH_SIZE = 64
EPOCHS = 200
VAL_SPLIT = 0.15
LR = 2e-3
SEED = 42

np.random.seed(SEED)
tf.random.set_seed(SEED)

# ============================================================
# 🚀 MAIN
# ============================================================
def main():
    print("\n🚀 Iniciando treino MS17-v5")

    # ---------------------------
    # Load data
    # ---------------------------
    print("📥 Carregando dados...")
    X = np.load(FEATURES_PATH)
    y = np.load(LABELS_PATH)

    print(f"✅ X shape: {X.shape}")
    print(f"✅ y shape: {y.shape}")

    if X.shape[0] != y.shape[0]:
        raise ValueError("X e y com número de amostras diferentes")

    input_dim = X.shape[1]

    # ---------------------------
    # Modelo
    # ---------------------------
    print("\n🧠 Construindo modelo MS17-v5")
    model = build_ms17_v5(input_dim=input_dim)
    model = compile_ms17_v5(model, lr=LR)

    model.summary()

    # ---------------------------
    # Callbacks
    # ---------------------------
    callbacks = [
        EarlyStopping(
            monitor="val_auc_pr",
            mode="max",
            patience=12,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_auc_pr",
            mode="max",
            factor=0.5,
            patience=5,
            min_lr=1e-5,
            verbose=1,
        ),
        ModelCheckpoint(
            MODEL_OUT,
            monitor="val_auc_pr",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
    ]

    # ---------------------------
    # Treino
    # ---------------------------
    print("\n🔥 Treinando...")
    model.fit(
        X,
        y,
        batch_size=BATCH_SIZE,
        epochs=EPOCHS,
        validation_split=VAL_SPLIT,
        shuffle=True,
        callbacks=callbacks,
        verbose=2,
    )

    print("\n✅ TREINO FINALIZADO")
    print("💾 Modelo salvo em:", MODEL_OUT)


if __name__ == "__main__":
    main()
