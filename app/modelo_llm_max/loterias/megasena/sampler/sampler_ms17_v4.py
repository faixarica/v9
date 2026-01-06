# -*- coding: utf-8 -*-
"""
sampler_ms17_v4.py
Sampler OFICIAL – Mega-Sena MS17-v4 (FaixaBet)

- Usa modelo treinado MS17-v4
- Entrada: último bloco (32,66)
- Saída: palpites Mega-Sena (6 dezenas)
"""

import os
import numpy as np
import tensorflow as tf

# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODEL_PATH = r"C:\Faixabet\V8\modelo_llm_max\models\megasena\ms17_v4\ms17_v4_transformer.keras"
DATASET_X = r"C:\Faixabet\V8\modelo_llm_max\loterias\dados\X_ms17_v4.npy"

NUM_DEZENAS = 6          # Mega-Sena
TOTAL_NUMS = 60

# ============================================================
# UTILIDADES
# ============================================================

def die(msg):
    raise RuntimeError("\n❌ ERRO NO SAMPLER MS17-v4\n" + msg)

def carregar_modelo():
    if not os.path.exists(MODEL_PATH):
        die(f"Modelo não encontrado:\n{MODEL_PATH}")
    print(f"[OK] Modelo carregado:\n     {MODEL_PATH}")
    return tf.keras.models.load_model(MODEL_PATH)

def carregar_ultimo_bloco():
    if not os.path.exists(DATASET_X):
        die(f"Dataset X não encontrado:\n{DATASET_X}")

    X = np.load(DATASET_X)

    if X.ndim != 3 or X.shape[1:] != (32, 66):
        die(
            f"X inválido.\n"
            f"Shape recebido: {X.shape}\n"
            "Esperado: (N, 32, 66)"
        )

    print(f"[OK] Dataset X carregado: {X.shape}")

    # último bloco temporal
    x_last = X[-1:]  # (1,32,66)
    return x_last

def gerar_scores(model, x_input):
    """
    Retorna vetor (60,) com scores do modelo
    """
    preds = model.predict(x_input, verbose=0)

    if preds.shape != (1, TOTAL_NUMS):
        die(
            f"Saída inesperada do modelo.\n"
            f"Shape recebido: {preds.shape}\n"
            f"Esperado: (1, {TOTAL_NUMS})"
        )

    return preds[0]

def topk(scores, k=6):
    """
    Seleção Top-K direta
    """
    idx = np.argsort(scores)[-k:]
    dezenas = sorted((idx + 1).tolist())
    return dezenas

def sample_probabilistico(scores, k=6, temperature=1.2):
    """
    Amostragem probabilística com temperatura
    """
    scores = np.asarray(scores, dtype=np.float64)

    # evita zeros
    scores = np.clip(scores, 1e-9, None)

    # temperatura
    probs = scores ** (1.0 / temperature)
    probs = probs / probs.sum()

    escolhidos = np.random.choice(
        TOTAL_NUMS,
        size=k,
        replace=False,
        p=probs
    )

    dezenas = sorted((escolhidos + 1).tolist())
    return dezenas

# ============================================================
# MAIN
# ============================================================

def main():

    print("\n🎯 Sampler Mega-Sena – MS17-v4\n")

    model = carregar_modelo()
    x_input = carregar_ultimo_bloco()

    print("[RUN] Gerando scores...")
    scores = gerar_scores(model, x_input)

    print("\n📊 Scores (top 10):")
    top10 = np.argsort(scores)[-10:][::-1]
    for i in top10:
        print(f"Dezena {i+1:02d}: score={scores[i]:.4f}")

    print("\n🎰 PALPITES GERADOS\n")

    # -------- Top-K puro --------
    palpite_topk = topk(scores, NUM_DEZENAS)
    print(f"Top-{NUM_DEZENAS}: {palpite_topk}")

    # -------- Probabilístico --------
    for t in [0.8, 1.0, 1.2, 1.5]:
        p = sample_probabilistico(scores, NUM_DEZENAS, temperature=t)
        print(f"Amostragem (temp={t}): {p}")

    print("\n✅ Sampler MS17-v4 finalizado com sucesso\n")

if __name__ == "__main__":
    main()
