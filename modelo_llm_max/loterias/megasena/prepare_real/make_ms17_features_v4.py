# -*- coding: utf-8 -*-
"""
make_ms17_features_v4.py
Gera features v4 para Mega-Sena a partir do rows_60bin.npy.

Saída (em modelo_llm_max/dados_m/):
- ms17_features_v4.npy  (N, 310)

Regras importantes:
- SEM vazamento: features do índice i usam apenas histórico até i-1
- i=0 fica zerado
"""

import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(ROOT_DIR, "dados_m")

ROWS_PATH = os.path.join(DATA_DIR, "rows_60bin.npy")
OUT_PATH  = os.path.join(DATA_DIR, "ms17_features_v4.npy")

# janelas de frequência (por dezena)
WINS = [10, 25, 50, 100]  # 4 * 60 = 240

def main():
    if not os.path.exists(ROWS_PATH):
        raise FileNotFoundError(f"Não encontrei: {ROWS_PATH}. Rode primeiro prepare_real_ms17.py")

    rows = np.load(ROWS_PATH).astype(np.int8)   # (N,60)
    N = rows.shape[0]
    assert rows.shape[1] == 60

    # Features:
    #  - freq por janela: 4*60 = 240
    #  - atraso por dezena (delay): 60  => 300
    #  - stats globais: 10            => 310
    F = 310
    X = np.zeros((N, F), dtype=np.float32)

    # rastreio de atraso: last_seen[d] = último índice em que d apareceu
    last_seen = np.full(60, -1, dtype=np.int32)

    # somas cumulativas para frequências rápidas
    cumsum = np.cumsum(rows, axis=0).astype(np.int32)  # (N,60)

    def window_sum(i, w):
        # soma das ocorrências na janela [i-w, i-1]
        if i <= 0:
            return np.zeros(60, dtype=np.int32)
        a = max(0, i - w)
        b = i - 1
        if a == 0:
            return cumsum[b]
        return cumsum[b] - cumsum[a - 1]

    for i in range(N):
        if i == 0:
            # primeira linha sem histórico
            continue

        feats = []

        # 1) frequências normalizadas por janela (240)
        for w in WINS:
            ws = window_sum(i, w).astype(np.float32) / float(w)
            feats.append(ws)

        feats = np.concatenate(feats, axis=0)  # (240,)

        # 2) atraso (delay) por dezena (60)
        # delay = quantos concursos desde que a dezena apareceu pela última vez
        delay = np.zeros(60, dtype=np.float32)
        for d in range(60):
            if last_seen[d] < 0:
                delay[d] = float(i)  # nunca saiu: atraso = i
            else:
                delay[d] = float(i - last_seen[d])

        # normaliza delay pra ficar em escala “boa” (0..1 aprox)
        delay_norm = np.clip(delay / 200.0, 0.0, 2.0)

        # 3) stats globais (10)
        hist = rows[:i]  # até i-1
        freq_global = hist.mean(axis=0)  # (60,)
        # estatísticas agregadas
        stats = np.array([
            float(i) / 4000.0,                 # progresso (normalizado)
            float(hist.sum()) / float(i*6),    # sanity (deve ~1.0)
            float(freq_global.mean()),         # média das frequências
            float(freq_global.std()),          # desvio padrão das frequências
            float((delay < 20).mean()),        # % dezenas “recentes”
            float((delay > 80).mean()),        # % dezenas “atrasadas”
            float(delay.mean() / 200.0),       # delay médio norm
            float(delay.std() / 200.0),        # delay std norm
            float(hist[-10:].mean()),          # densidade últimos 10
            float(hist[-50:].mean()),          # densidade últimos 50
        ], dtype=np.float32)

        # monta vetor final (310)
        x = np.concatenate([feats, delay_norm, stats], axis=0)
        assert x.shape[0] == 310
        X[i] = x

        # atualiza last_seen com o concurso i (após extrair features)
        hit = rows[i].nonzero()[0]
        for d in hit:
            last_seen[d] = i

    np.save(OUT_PATH, X)
    print("✅ ms17_features_v4.npy gerado:", X.shape, "->", OUT_PATH)

if __name__ == "__main__":
    main()
