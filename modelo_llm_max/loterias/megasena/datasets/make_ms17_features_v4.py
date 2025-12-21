# -*- coding: utf-8 -*-
"""
make_ms17_features_v4.py
Gera o DATASET FINAL do MS17-v4 como BUNDLE:
- X_ms17_v4.npy : (N, 32, 66)
- Y_ms17_v4.npy : (N, 60)

Regras:
✔ X e Y são gerados JUNTOS
✔ Mesmo N, mesmo loop
✔ Caminhos de dados detectados automaticamente
"""

import os
import numpy as np

# ============================================================
# CONFIGURAÇÃO DE PATHS
# ============================================================

BASE = os.path.dirname(os.path.abspath(__file__))

# Diretórios candidatos onde o rows_60bin.npy pode existir
ROWS_DIRS = [
    os.path.join(BASE, "..", "dados"),
    os.path.join(BASE, "..", "prepare_real", "dados"),
    os.path.join(BASE, "..", "..", "dados"),
]

# Onde salvar o dataset final (padrão do projeto)
OUT_DIR = os.path.abspath(os.path.join(BASE, "..", "..", "dados"))

WINDOW = 32          # timesteps
F_BASE = 60
F_EXTRA = 6
F_TOTAL = 66

# ============================================================
# UTILIDADES
# ============================================================

def die(msg):
    raise RuntimeError("\n❌ ERRO NO MAKE_MS17_FEATURES_V4\n" + msg)

def localizar_rows_60bin():
    """
    Localiza rows_60bin.npy nos diretórios conhecidos.
    Retorna o path completo ou falha com mensagem explicativa.
    """
    for d in ROWS_DIRS:
        path = os.path.abspath(os.path.join(d, "rows_60bin.npy"))
        if os.path.exists(path):
            print(f"[OK] rows_60bin encontrado em:\n     {path}")
            return path

    die(
        "rows_60bin.npy NÃO foi encontrado.\n\n"
        "Locais verificados:\n"
        + "\n".join(f" - {os.path.abspath(d)}" for d in ROWS_DIRS)
        + "\n\nAção esperada:\n"
        "➡️ Rode primeiro o prepare_real da Mega-Sena\n"
        "➡️ Ou verifique se o arquivo existe com esse nome exato."
    )

def step_features(row60):
    """
    Constrói o vetor de features (66) a partir de um row binário (60).
    """
    row = row60.astype(np.float32)

    idx = np.where(row > 0.5)[0].astype(np.float32)

    if idx.size == 0:
        extras = np.zeros(6, dtype=np.float32)
    else:
        dezenas = idx + 1.0
        extras = np.array([
            idx.size / 6.0,                 # quantidade de dezenas
            idx.sum() / (60 * 6),            # soma normalizada
            idx.mean() / 59.0,               # média normalizada
            idx.std() / 30.0,                # desvio normalizado
            (dezenas % 2 == 0).sum() / 6.0,  # pares
            (dezenas % 2 != 0).sum() / 6.0   # ímpares
        ], dtype=np.float32)

    return np.concatenate([row, extras], axis=0)  # (66,)

# ============================================================
# MAIN
# ============================================================

def main():

    # ---------- Localizar rows ----------
    rows_path = localizar_rows_60bin()
    rows = np.load(rows_path)

    # ---------- Validações básicas ----------
    if rows.ndim != 2 or rows.shape[1] != 60:
        die(
            f"rows_60bin inválido.\n"
            f"Shape recebido: {rows.shape}\n"
            "Esperado: (N, 60)"
        )

    N = rows.shape[0]
    if N <= WINDOW:
        die(
            f"Histórico insuficiente.\n"
            f"N={N}, WINDOW={WINDOW}\n"
            "É necessário ter mais concursos do que o tamanho da janela."
        )

    print(f"[OK] rows carregado: {rows.shape}")

    # ---------- Construção do dataset ----------
    X_list = []
    Y_list = []

    for t in range(WINDOW, N):
        window = rows[t-WINDOW:t]  # (32,60)
        x = np.stack([step_features(window[i]) for i in range(WINDOW)], axis=0)
        y = rows[t].astype(np.float32)

        X_list.append(x)
        Y_list.append(y)

    X = np.stack(X_list, axis=0)  # (N-WINDOW, 32, 66)
    Y = np.stack(Y_list, axis=0)  # (N-WINDOW, 60)

    print(f"[OK] X gerado: {X.shape}")
    print(f"[OK] Y gerado: {Y.shape}")

    # ---------- Salvar ----------
    os.makedirs(OUT_DIR, exist_ok=True)

    out_x = os.path.join(OUT_DIR, "X_ms17_v4.npy")
    out_y = os.path.join(OUT_DIR, "Y_ms17_v4.npy")

    np.save(out_x, X)
    np.save(out_y, Y)

    print(f"[SAVE] {out_x}")
    print(f"[SAVE] {out_y}")
    print("\n✅ DATASET MS17-v4 GERADO COM SUCESSO")

if __name__ == "__main__":
    main()
