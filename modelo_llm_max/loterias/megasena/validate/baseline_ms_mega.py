# -*- coding: utf-8 -*-
"""
baseline_ms_mega.py
Baseline estatístico para Mega-Sena:
- frequência por janela
- penalidade de recência (delay)
- sampling k=6
"""

import numpy as np

def compute_baseline_scores(rows, idx, w=100, alpha=0.7, beta=0.3):
    """
    rows: (N,60) binário
    idx: índice do concurso alvo (usa histórico até idx-1)
    """
    if idx <= 0:
        return np.ones(60, dtype=np.float32) / 60.0

    hist = rows[:idx]

    # frequência curta
    h = hist[-w:] if hist.shape[0] >= w else hist
    freq = h.mean(axis=0)  # (60,)

    # frequência global
    freq_g = hist.mean(axis=0)

    # atraso (delay)
    last_seen = np.full(60, -1, dtype=np.int32)
    for i in range(hist.shape[0]):
        hit = hist[i].nonzero()[0]
        for d in hit:
            last_seen[d] = i

    delay = np.zeros(60, dtype=np.float32)
    for d in range(60):
        if last_seen[d] < 0:
            delay[d] = float(hist.shape[0])
        else:
            delay[d] = float(hist.shape[0] - last_seen[d])

    delay_penalty = np.exp(-delay / 50.0)  # quanto mais recente, maior

    score = alpha * freq + (1 - alpha) * freq_g
    score = score * (beta * delay_penalty + (1 - beta))

    score = score + 1e-8
    score = score / score.sum()

    return score

def sample_k(scores, k=6, seed=None):
    rng = np.random.default_rng(seed)
    return rng.choice(60, size=k, replace=False, p=scores)
