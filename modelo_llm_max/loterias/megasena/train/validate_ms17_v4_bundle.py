# -*- coding: utf-8 -*-
"""
validate_ms17_v4_bundle.py
Validacao OFICIAL do MS17-v4 usando BUNDLE (X/Y prontos).

- Nao usa rows_60bin.npy
- Nao usa ms17_features_v4.npy (antigo)
- Nao faz shift manual
- Carrega:
  X_ms17_v4.npy (N,32,66)
  Y_ms17_v4.npy (N,60)
"""

import os
import numpy as np
import tensorflow as tf

# =========================
# PATHS (ajuste se quiser)
# =========================

MODEL_PATH = r"C:\Faixabet\V8\modelo_llm_max\models\megasena\ms17_v4\ms17_v4_transformer.keras"
BUNDLE_DIR = r"C:\Faixabet\V8\modelo_llm_max\loterias\dados"

X_FILE = "X_ms17_v4.npy"
Y_FILE = "Y_ms17_v4.npy"

TOPK_LIST = [6, 8, 10, 12]
CRITERIO_K = 6           # Mega-Sena = 6 dezenas
CRITERIO_MIN = 0.80      # meta inicial realista p/ TOP-6 (ajuste depois)

# =========================
# UTIL
# =========================

def _die(msg: str):
    raise RuntimeError("\n❌ VALIDATE MS17-v4 (BUNDLE)\n" + msg)

def avaliar_topk(y_true: np.ndarray, y_pred: np.ndarray, k: int) -> float:
    # y_true: (N,60) binario
    # y_pred: (N,60) scores
    hits = []
    for i in range(y_true.shape[0]):
        verdade = set(np.where(y_true[i] > 0.5)[0])
        topk = set(np.argsort(y_pred[i])[-k:])
        hits.append(len(verdade & topk))
    return float(np.mean(hits))

def baseline_random(y_true: np.ndarray, k: int = 6, trials: int = 200) -> float:
    # baseline aleatorio para comparar
    hits = []
    n = y_true.shape[0]
    for _ in range(trials):
        for i in range(n):
            verdade = set(np.where(y_true[i] > 0.5)[0])
            rand = set(np.random.choice(60, k, replace=False))
            hits.append(len(verdade & rand))
    return float(np.mean(hits))

def carregar_modelo():
    print(f"[PATH] Modelo: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        _die(
            "Modelo nao encontrado.\n"
            f"Esperado em:\n{MODEL_PATH}\n"
            "➡️ Rode o treino (opcao 4) ou confirme o caminho."
        )
    print("[LOAD] Carregando modelo...")
    model = tf.keras.models.load_model(MODEL_PATH)
    print("[OK] Modelo carregado")
    return model

def carregar_bundle(model):
    x_path = os.path.join(BUNDLE_DIR, X_FILE)
    y_path = os.path.join(BUNDLE_DIR, Y_FILE)

    print("\n[LOAD] Carregando BUNDLE (X/Y)...")
    print(f"[PATH] X: {x_path}")
    print(f"[PATH] Y: {y_path}")

    if not os.path.exists(x_path):
        _die(
            f"Arquivo X nao encontrado:\n{x_path}\n"
            "➡️ Rode a opcao 3 (make_ms17_features_v4.py) para gerar o bundle."
        )
    if not os.path.exists(y_path):
        _die(
            f"Arquivo Y nao encontrado:\n{y_path}\n"
            "➡️ Rode a opcao 3 (make_ms17_features_v4.py) para gerar o bundle."
        )

    X = np.load(x_path)
    Y = np.load(y_path)

    print(f"[INFO] X.shape = {X.shape}")
    print(f"[INFO] Y.shape = {Y.shape}")

    # Validacoes
    if X.ndim != 3:
        _die(f"X invalido: esperado 3D (N,32,66), recebido {X.shape}")
    if Y.ndim != 2 or Y.shape[1] != 60:
        _die(f"Y invalido: esperado 2D (N,60), recebido {Y.shape}")

    if X.shape[0] != Y.shape[0]:
        _die(
            "Bundle inconsistente: N diferente.\n"
            f"X={X.shape} | Y={Y.shape}\n"
            "➡️ Gere X e Y na MESMA execucao do make_ms17_features_v4.py."
        )

    # Confere compatibilidade com modelo
    expected = model.input_shape  # (None, 32, 66)
    if not (isinstance(expected, (list, tuple)) and len(expected) == 3):
        _die(f"Modelo com input_shape inesperado: {expected}")

    _, T, F = expected
    if (X.shape[1], X.shape[2]) != (T, F):
        _die(
            "Incompatibilidade de shape entre X e modelo.\n"
            f"Modelo espera (N,{T},{F}) e X esta (N,{X.shape[1]},{X.shape[2]})\n"
            "➡️ Verifique se o treino foi feito com este mesmo bundle."
        )

    print("[OK] Bundle validado e compativel com o modelo.")
    return X, Y

def main():
    print("\n🔎 Validando Modelo – Mega-Sena MS17-v4 (BUNDLE)\n")

    model = carregar_modelo()
    X, Y = carregar_bundle(model)

    print("\n[RUN] Gerando previsoes...")
    preds = model.predict(X, verbose=0)

    if preds.shape != Y.shape:
        _die(
            "Saida do modelo nao bate com Y.\n"
            f"preds={preds.shape} | Y={Y.shape}\n"
            "➡️ Treine novamente com o bundle correto."
        )

    print("\n📊 RESULTADOS (TOP-K)")
    resultados = {}
    for k in TOPK_LIST:
        m = avaliar_topk(Y, preds, k)
        resultados[k] = m
        print(f"Top-{k:<2} -> media acertos = {m:.3f}")

    base = baseline_random(Y, k=CRITERIO_K, trials=200)
    print(f"\n🎲 Baseline aleatorio Top-{CRITERIO_K}: {base:.3f}")

    print("\n📌 CRITERIO OPERACIONAL (ajustavel)")
    print(f"Top-{CRITERIO_K} >= {CRITERIO_MIN:.2f}")

    if resultados.get(CRITERIO_K, 0.0) >= CRITERIO_MIN:
        print("\nSTATUS: ✅ APROVADO (operacional)")
    else:
        print("\nSTATUS: ⚠️ REPROVADO (operacional)")
        print("Obs: Isso nao e erro de pipeline. E apenas qualidade do modelo.\n")

if __name__ == "__main__":
    main()
