# -*- coding: utf-8 -*-
"""
MS17_V5 Engine - Pipeline Supervisionado Real
- Input: Últimos 32 concursos do CSV
- Features: 66 por passo (60 bin + 6 stats)
- Model: ls17_v3.keras (TensorFlow/Keras)
"""

import os
import random
import numpy as np
import pandas as pd

# Tentativa de import do Tensorflow/Loaders
try:
    import tensorflow as tf
    from modelo_llm_max.load_models import load_model, _models_dir
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    load_model = None

CSV_PATH = "loteriamega.csv"
MODEL_REL_PATH = os.path.join("ls17", "ls17_v3.keras") # Ajuste conforme estrutura real

# Configuração do Pipeline
WINDOW = 32
F_BASE = 60
F_EXTRA = 6

_cached_model = None

def _get_model():
    """Singleton para carregar modelo Keras"""
    global _cached_model
    if _cached_model:
        return _cached_model
    
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow nao instalado")

    # Monta caminho absoluto
    # modelo_llm_max/models/ls17/ls17_v3.keras
    base = _models_dir() # definido em load_models.py
    path = os.path.join(base, "ls17", "ls17_v3.keras")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Modelo nao encontrado em: {path}")
        
    print(f"[MS17_V5] Carregando modelo real: {path}")
    _cached_model = load_model(path)
    return _cached_model

def step_features(row_numeros: list) -> np.ndarray:
    """
    Transforma lista de numeros [1, 23, 60] em vetor (66,)
    Logica IDÊNTICA ao prepare_ms17_v4.py
    """
    # 1. One-Hot (60,)
    arr = np.zeros(60, dtype=np.float32)
    idx = [n-1 for n in row_numeros if 0 <= n-1 < 60]
    if idx:
        arr[idx] = 1.0
    
    # 2. Stats (6,)
    if not idx:
        stats = np.zeros(6, dtype=np.float32)
    else:
        # calculos baseados em indices 0..59
        n_idx = np.array(idx, dtype=np.float32)
        qtd = float(len(idx))
        s = float(n_idx.sum())
        m = float(n_idx.mean())
        sd = float(n_idx.std())
        
        # dezenas reais 1..60
        dezenas = n_idx + 1.0
        pares = float(((dezenas % 2) == 0).sum())
        imp = float(((dezenas % 2) != 0).sum())
        
        norm_extras = [
            qtd / 6.0,
            s / (60.0 * 6.0),
            m / 59.0,
            sd / 30.0,
            pares / 6.0,
            imp / 6.0
        ]
        stats = np.array(norm_extras, dtype=np.float32)

    return np.concatenate([arr, stats], axis=0)

def gerar_neural(qtd):
    """Pipeline Real"""
    model = _get_model()
    
    # 1. Carregar CSV e pegar ultimos 32
    df = pd.read_csv(CSV_PATH)
    cols_bola = [f"Bola{i}" for i in range(1, 7)]
    
    if len(df) < WINDOW:
        raise ValueError(f"Historico insuficiente. Precisa {WINDOW}, tem {len(df)}")
        
    last_window = df.tail(WINDOW)
    
    # 2. Montar Tensor (1, 32, 66)
    steps = []
    for _, row in last_window.iterrows():
        nums = row[cols_bola].values.astype(int)
        feats = step_features(nums)
        steps.append(feats)
        
    X = np.array([steps], dtype=np.float32) # (1, 32, 66)
    
    # 3. Predict
    # Saida (1, 60) - Sigmoid ou Softmax? 
    # V4 geralmente é Sigmoid (multilabel). 
    preds = model.predict(X, verbose=0)[0] # (60,)
    
    # 4. Selecionar Top K
    # preds é array 0..59. Indices + 1 = Dezenas
    indices = np.argsort(preds)[::-1] # decrescente
    
    top_indices = indices[:qtd]
    dezenas = sorted([int(i+1) for i in top_indices])
    return dezenas

def gerar_statistico_fallback(qtd_dezenas):
    """Fallback robusto (implementado anteriormente)"""
    # ... (mesma logica da versao anterior) ...
    try:
        df = pd.read_csv(CSV_PATH)
    except:
        return sorted(random.sample(range(1, 61), qtd_dezenas))
        
    bolas = [f"Bola{i}" for i in range(1, 7)]
    todos = df[bolas].values.flatten()
    freq = pd.Series(todos).value_counts().sort_index()
    freq = (freq - freq.min()) / (freq.max() - freq.min())
    recentes = df.tail(10)[bolas].values.flatten()
    freq_hot = pd.Series(recentes).value_counts().reindex(range(1,61), fill_value=0)
    scores = freq * 0.3 + freq_hot * 0.7
    noise = np.random.normal(0, 0.1, size=60)
    final = np.maximum(scores.values + noise, 0)
    probs = final / final.sum() if final.sum() > 0 else None
    
    dezenas = np.random.choice(range(1, 61), size=qtd_dezenas, replace=False, p=probs)
    return sorted(map(int, dezenas))

def gerar(qtd_dezenas: int):
    """Entrypoint principal"""
    qtd = max(6, min(20, int(qtd_dezenas)))
    
    if TF_AVAILABLE:
        try:
            return gerar_neural(qtd)
        except Exception as e:
            print(f"[MS17_V5] Erro no Neural: {e} -> Usando Fallback")
            return gerar_statistico_fallback(qtd)
    else:
        # Fallback silencioso (ou logado) se nao tiver TF
        return gerar_statistico_fallback(qtd)
