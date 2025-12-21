# -*- coding: utf-8 -*-
"""
prepare_ms17_v4.py
Gera dataset MS17-v4 (Mega-Sena) no contrato do modelo:
X: (N, 32, 66)
Y: (N, 60)

- Entrada: rows_60bin.npy (N,60) em dados/
- Saídas:
  - X_ms17_v4.npy        (N-32, 32, 66)
  - Y_ms17_v4.npy        (N-32, 60)
  - X_ms17_v4_flat.npy   (N-32, 2112)  [opcional]
"""

import os
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "dados")

ROWS_FILE = "rows_60bin.npy"

WINDOW = 32          # timesteps
F_BASE = 60          # dezenas
F_EXTRA = 6          # extras simples
F_TOTAL = F_BASE + F_EXTRA  # 66

SAVE_FLAT = True     # salva também versão flatten (N,2112)

def die(msg: str):
    raise RuntimeError(msg)

def load_npy(path: str):
    print(f"[LOAD] {path}")
    return np.load(path)

def step_features(row60: np.ndarray) -> np.ndarray:
    """
    row60: (60,) binário
    retorna: (66,) = 60 bin + 6 extras
    Extras (simples e estáveis):
      - qtd_ones (normalizado)
      - soma_indices (normalizado)
      - media_indice (normalizado)
      - std_indice (normalizado)
      - qtd_pares (normalizado)
      - qtd_impares (normalizado)
    """
    row = row60.astype(np.float32)

    idx = np.where(row > 0.5)[0].astype(np.float32)  # 0..59
    if idx.size == 0:
        # caso extremo (não esperado): evita NaN
        qtd = 0.0
        s = 0.0
        m = 0.0
        sd = 0.0
        pares = 0.0
        imp = 0.0
    else:
        qtd = float(idx.size)                  # tipicamente 6
        s = float(idx.sum())                   # soma índices
        m = float(idx.mean())
        sd = float(idx.std())
        # pares/ímpares considerando "dezenas" = idx+1
        dezenas = idx + 1.0
        pares = float((dezenas % 2 == 0).sum())
        imp = float((dezenas % 2 != 0).sum())

    # normalizações simples (mantém números em escala ~0..1)
    qtd_n = qtd / 6.0
    s_n   = s / (60.0 * 6.0)       # soma máx aprox 60*6
    m_n   = m / 59.0
    sd_n  = sd / 30.0              # escala razoável (não precisa perfeito)
    pares_n = pares / 6.0
    imp_n   = imp / 6.0

    extras = np.array([qtd_n, s_n, m_n, sd_n, pares_n, imp_n], dtype=np.float32)
    return np.concatenate([row, extras], axis=0).astype(np.float32)  # (66,)

def main():
    if not os.path.isdir(DADOS):
        die(f"❌ Pasta dados/ não encontrada: {DADOS}")

    rows_path = os.path.join(DADOS, ROWS_FILE)
    if not os.path.exists(rows_path):
        die(
            "❌ rows_60bin.npy não encontrado em dados/.\n"
            f"Esperado em: {rows_path}\n"
            "➡️ Rode a raspagem/prepare anterior que gera rows_60bin.npy."
        )

    rows = load_npy(rows_path)  # (N,60)
    if rows.ndim != 2 or rows.shape[1] != 60:
        die(f"❌ rows_60bin inválido: shape={rows.shape} (esperado (N,60))")

    N = rows.shape[0]
    if N <= WINDOW:
        die(f"❌ Poucos concursos ({N}) para WINDOW={WINDOW}. Precisa N > {WINDOW}.")

    print(f"[OK] rows carregado: {rows.shape}")

    # Construção do dataset
    X_list = []
    Y_list = []

    # Para prever o concurso t, usa os 32 anteriores: [t-WINDOW, ..., t-1]
    # Então t começa em WINDOW e vai até N-1
    for t in range(WINDOW, N):
        window_rows = rows[t-WINDOW:t]  # (32,60)
        x_steps = np.stack([step_features(window_rows[i]) for i in range(WINDOW)], axis=0)  # (32,66)
        y = rows[t].astype(np.float32)  # (60,)
        X_list.append(x_steps)
        Y_list.append(y)

    X = np.stack(X_list, axis=0).astype(np.float32)  # (N-WINDOW, 32, 66)
    Y = np.stack(Y_list, axis=0).astype(np.float32)  # (N-WINDOW, 60)

    print(f"[OK] X gerado: {X.shape} (esperado (N,32,66))")
    print(f"[OK] Y gerado: {Y.shape} (esperado (N,60))")

    # Salvar
    x_out = os.path.join(DADOS, "X_ms17_v4.npy")
    y_out = os.path.join(DADOS, "Y_ms17_v4.npy")
    np.save(x_out, X)
    np.save(y_out, Y)
    print(f"[SAVE] {x_out}")
    print(f"[SAVE] {y_out}")

    if SAVE_FLAT:
        X_flat = X.reshape((X.shape[0], -1))  # (N-WINDOW, 2112)
        xflat_out = os.path.join(DADOS, "X_ms17_v4_flat.npy")
        np.save(xflat_out, X_flat.astype(np.float32))
        print(f"[SAVE] {xflat_out}  shape={X_flat.shape}")

    print("\n✅ PREPARE MS17-v4 FINALIZADO COM SUCESSO.")
    print("➡️ Agora a validação deve apontar para X_ms17_v4.npy e Y_ms17_v4.npy.")

if __name__ == "__main__":
    main()
