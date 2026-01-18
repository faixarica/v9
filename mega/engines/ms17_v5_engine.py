# -*- coding: utf-8 -*-
"""
MS17_V5 Engine - Lightweight Production (No TensorFlow)
- Input: Artefato "ms17_v4_rank.npy" (Ranking estático gerado offline)
- Runtime: Pure Python + Numpy
- Performance: Instantânea (sem load de Keras)
"""

import os
import random
import numpy as np
from modelo_llm_max.load_models import MODELS_DIR

# Configuração
# O artefato é gerado pelo script export_ms17_inference.py
RANK_FILE = os.path.join(MODELS_DIR, "megasena", "ms17_v4_rank.npy")

_cached_rank = None

def _get_rank():
    """Carrega o ranking estático (probabilidades)"""
    global _cached_rank
    if _cached_rank is not None:
        return _cached_rank
    
    if not os.path.exists(RANK_FILE):
        print(f"[MS17_V5] ALERTA: Artefato nao encontrado: {RANK_FILE}")
        return None

    try:
        print(f"[MS17_V5] Carregando ranking (Light): {RANK_FILE}")
        rank = np.load(RANK_FILE)
        
        # Validar integridade básica
        if rank.shape != (60,):
             print(f"[MS17_V5] Shape invalido do rank: {rank.shape}")
             return None
             
        _cached_rank = rank
        return _cached_rank
    except Exception as e:
        print(f"[MS17_V5] Erro ao carregar rank: {e}")
        return None

def gerar(qtd_dezenas: int):
    """
    Gera palpites usando amostragem ponderada pelo Ranking V4.
    """
    qtd = max(6, min(20, int(qtd_dezenas)))
    
    # 1. Tentar carregar Ranking
    rank = _get_rank()
    
    if rank is not None:
        print("MS17_V5 ENGINE REAL ATIVA") # Auditoria solicitada
        try:
            # Normalizar (seguranca)
            p = rank / rank.sum()
            
            # Amostragem sem reposicao
            escolhidos = np.random.choice(
                range(1, 61),
                size=qtd,
                replace=False,
                p=p
            )
            return sorted(map(int, escolhidos))
        except Exception as e:
            print(f"[MS17_V5] Erro na amostragem: {e}. Usando Fallback.")
    else:
        print("[MS17_V5] Ranking nao disponivel. Usando Fallback Random.")
        
    # Fallback (Random Puro)
    # Motivo: Se o artefato nao existir, o usuario nao pode ficar sem palpite.
    return sorted(random.sample(range(1, 61), qtd))
