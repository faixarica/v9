# -*- coding: utf-8 -*-
"""
validate_ms17_v4.py
Validação OFICIAL – Mega-Sena MS17-v4 (FaixaBet) — versão robusta

✅ Descobre input_shape esperado do modelo (T,F)
✅ Carrega X/Y com auto-detecção
✅ Reshape seguro (somente se colunas == T*F)
✅ Mensagens auto-explicativas para TODOS os erros
✅ Validação Top-K + baseline
✅ Smoke test antes do predict completo
"""

import os
import glob
import numpy as np
import tensorflow as tf
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = r"C:\Faixabet\V8\modelo_llm_max\models\megasena\ms17_v4\ms17_v4_transformer.keras"

DATA_DIRS = [
    r"C:\Faixabet\V8\modelo_llm_max\loterias\megasena\prepare_real\dados",
    r"C:\Faixabet\V8\modelo_llm_max\dados",
]

# Procuramos qualquer feature compatível com MS17
FEATURE_PATTERNS = [
    "ls17_mega_features*.npy",
    "ms17*_features*.npy",
    "X*.npy",
]

ROWS_FILE = "rows_60bin.npy"

TOPK_LIST = [6, 8, 10, 12, 15]
CRITERIO_K = 10
CRITERIO_MINIMO = 2.0

BASELINE_TRIALS = 200

# ============================================================
# UTILS
# ============================================================

def _fmt_dt(ts: float) -> str:
    return str(datetime.fromtimestamp(ts))

def _list_dir(d: str):
    try:
        files = sorted(os.listdir(d))
    except Exception:
        files = []
    return files

def _die(msg: str):
    raise RuntimeError(msg)

# ============================================================
# METRICS
# ============================================================

def avaliar_topk(y_true, y_pred, k):
    hits = []
    for i in range(len(y_true)):
        verdade = set(np.where(y_true[i] == 1)[0])
        topk = set(np.argsort(y_pred[i])[-k:])
        hits.append(len(verdade & topk))
    return float(np.mean(hits))

def baseline_random(y_true, k=10, trials=200):
    hits = []
    for _ in range(trials):
        for i in range(len(y_true)):
            verdade = set(np.where(y_true[i] == 1)[0])
            rand = set(np.random.choice(60, k, replace=False))
            hits.append(len(verdade & rand))
    return float(np.mean(hits))

# ============================================================
# LOCATE FILES
# ============================================================

def localizar_rows():
    for d in DATA_DIRS:
        path = os.path.join(d, ROWS_FILE)
        if os.path.exists(path):
            print(f"[OK] rows_60bin encontrado: {path}")
            return path
    _die(
        "\n❌ ERRO CRÍTICO: rows_60bin.npy não encontrado.\n"
        "Sem ele não é possível validar o modelo.\n"
        "Locais verificados:\n- " + "\n- ".join(DATA_DIRS)
    )

def localizar_features_candidatos():
    candidatos = []
    for d in DATA_DIRS:
        if not os.path.exists(d):
            print(f"[WARN] Diretório não encontrado: {d}")
            continue
        for pat in FEATURE_PATTERNS:
            candidatos += glob.glob(os.path.join(d, pat))
    # remove duplicados preservando ordem
    seen = set()
    uniq = []
    for c in candidatos:
        if c not in seen and os.path.isfile(c):
            seen.add(c)
            uniq.append(c)
    return uniq

def escolher_feature_por_mtime(candidatos):
    if not candidatos:
        _die(
            "\n❌ ERRO CRÍTICO: nenhum arquivo de features encontrado.\n"
            "Você precisa gerar um arquivo compatível com o MS17-v4.\n"
            "Padrões buscados:\n- " + "\n- ".join(FEATURE_PATTERNS) + "\n"
            "Locais verificados:\n- " + "\n- ".join(DATA_DIRS)
        )
    candidatos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return candidatos[0]

# ============================================================
# SHAPE HANDLING (a parte “profunda”)
# ============================================================

def get_model_TF(model):
    """
    Lê (T,F) do modelo.
    Esperado: model.input_shape == (None,T,F)
    """
    inp = model.input_shape
    if not isinstance(inp, (tuple, list)) or len(inp) != 3:
        _die(
            f"\n❌ ERRO: input_shape inesperado do modelo: {inp}\n"
            "Este validate assume um modelo sequence (None,T,F)."
        )
    _, T, F = inp
    if T is None or F is None:
        _die(
            f"\n❌ ERRO: modelo com dimensões indefinidas: input_shape={inp}\n"
            "Você provavelmente salvou o modelo sem shape fixo."
        )
    return int(T), int(F)

def ajustar_X_para_modelo(X, T, F, feature_path):
    """
    Converte X para (N,T,F) SOMENTE se for matematicamente compatível.
    - Se X já for (N,T,F): ok
    - Se X for (N,T*F): reshape
    - Caso contrário: ERRO explicativo (sem “gambiarra”)
    """
    esperado_flat = T * F

    if X.ndim == 3:
        if X.shape[1:] == (T, F):
            print("[OK] X já está no formato correto 3D.")
            return X
        _die(
            "\n❌ ERRO: X é 3D mas não bate com o modelo.\n"
            f"Arquivo: {feature_path}\n"
            f"X.shape={X.shape}\n"
            f"Modelo espera (N,{T},{F})\n"
            "➡️ Gere novamente as features com o mesmo layout do treino do MS17-v4."
        )

    if X.ndim == 2:
        n, cols = X.shape
        if cols == esperado_flat:
            print(f"[FIX] X 2D compatível (N,{cols}). Reformatando para (N,{T},{F})...")
            return X.reshape((n, T, F))

        # Aqui está o seu caso: cols=420 mas esperado_flat=2112
        _die(
            "\n❌ ERRO: FEATURES INCOMPATÍVEIS COM O MODELO.\n"
            f"Modelo espera input (N,{T},{F}) => flatten teria {esperado_flat} colunas.\n"
            f"Mas o arquivo de features tem X.shape={X.shape} => {cols} colunas.\n\n"
            f"Arquivo carregado: {feature_path}\n\n"
            "✅ Isso NÃO é erro do validate. É mismatch de pipeline:\n"
            "- Ou você está apontando para o arquivo errado;\n"
            "- Ou o prepare_real usado para gerar esse .npy não é o do MS17-v4;\n"
            "- Ou o treino usou outra matriz (ex.: (N,32,66)) e o prepare_real atual gera 420 features.\n\n"
            "➡️ Correção: gere/aponte para um arquivo de features com:\n"
            f"   - shape 3D: (N,{T},{F})\n"
            f"   - OU shape 2D: (N,{esperado_flat})\n"
        )

    _die(
        "\n❌ ERRO: X com dimensionalidade inválida.\n"
        f"X.ndim={X.ndim}, X.shape={X.shape}\n"
        "Esperado 2D (N,T*F) ou 3D (N,T,F)."
    )

# ============================================================
# DATA LOAD
# ============================================================

def carregar_dados(model):
    print("\n[LOAD] Localizando arquivos de dados...")

    candidatos = localizar_features_candidatos()
    escolhido = escolher_feature_por_mtime(candidatos)

    print("[OK] Feature file selecionado automaticamente:")
    print(f"     {escolhido}")
    print(f"     Data modificação: {_fmt_dt(os.path.getmtime(escolhido))}")

    rows_path = localizar_rows()

    print("\n[LOAD] Carregando arrays...")
    X = np.load(escolhido)
    rows = np.load(rows_path)

    print(f"[INFO] Shape bruto X: {X.shape}")
    print(f"[INFO] Shape bruto rows: {rows.shape}")

    # rows sanity
    if rows.ndim != 2 or rows.shape[1] != 60:
        _die(
            "\n❌ ERRO: rows_60bin inválido.\n"
            f"rows.shape={rows.shape}\n"
            "Esperado: (N,60)"
        )

    # alinhamento temporal (features t → sorteio t+1)
    X = X[:-1]
    Y = rows[1:]

    if X.shape[0] != Y.shape[0]:
        _die(
            "\n❌ ERRO: desalinhamento temporal após shift.\n"
            f"X={X.shape}, Y={Y.shape}\n"
            "➡️ Ajuste o prepare_real para gerar mesmo N."
        )

    print(f"[OK] Dados alinhados: X={X.shape}, Y={Y.shape}")

    # Ajuste de shape X conforme modelo
    T, F = get_model_TF(model)
    print(f"[INFO] Modelo espera input: (N, {T}, {F})")

    X = ajustar_X_para_modelo(X, T, F, escolhido)

    print(f"[OK] X final para predict: {X.shape}")

    return X, Y

# ============================================================
# MAIN
# ============================================================

def main():
    print("\n🔎 Validando Modelo – Mega-Sena MS17-v4\n")

    print(f"[PATH] Modelo: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        _die(
            "\n❌ ERRO: modelo não encontrado.\n"
            f"Path: {MODEL_PATH}\n"
            "➡️ Verifique se o treino gerou o .keras e se o caminho está correto."
        )

    print("[LOAD] Carregando modelo...")
    model = tf.keras.models.load_model(MODEL_PATH)
    print("[OK] Modelo carregado")

    # dados (já ajusta shape)
    X, Y = carregar_dados(model)

    # smoke test
    print("\n[SMOKE] Teste rápido com 2 amostras...")
    _ = model.predict(X[:2], verbose=0)
    print("[OK] Smoke test passou")

    # predict completo
    print("\n[RUN] Gerando previsões...")
    preds = model.predict(X, verbose=0)

    if preds.shape != Y.shape:
        _die(
            "\n❌ ERRO: shape de saída incompatível.\n"
            f"preds.shape={preds.shape}\n"
            f"Y.shape={Y.shape}\n"
            "➡️ Modelo/dados não estão compatíveis."
        )

    # resultados
    print("\n📊 RESULTADO FINAL (VALIDAÇÃO REAL – TOP-K)\n")
    for k in TOPK_LIST:
        media = avaliar_topk(Y, preds, k)
        print(f"Top-{k:<2}: média de acertos = {media:.3f}")

    base = baseline_random(Y, k=CRITERIO_K, trials=BASELINE_TRIALS)
    print(f"\n🎲 Baseline aleatório Top-{CRITERIO_K}: {base:.3f}")

    print("\n📌 CRITÉRIO DE APROVAÇÃO")
    print(f"Top-{CRITERIO_K} ≥ {CRITERIO_MINIMO:.1f}")

    aprovado = avaliar_topk(Y, preds, CRITERIO_K) >= CRITERIO_MINIMO
    print("\nSTATUS:", "✅ APROVADO" if aprovado else "❌ REPROVADO")

if __name__ == "__main__":
    main()
