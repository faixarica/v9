"""
Geração das features profissionais LS17-v3 (150 features)
Autor: fAIxaBet / 2025

Entrada:
    - dados/rows_25bin.npy            (N, 25)
    - dados/rows.npy                  (N, 15)   ← dezenas reais historicas
    - meta.json                       (datas)

Saída:
    - dados/ls17_features_v3.npy      (N, 150)
"""

import numpy as np
import json
import os

BASE = os.path.dirname(__file__)
DADOS = os.path.join(BASE, "dados")

def load(name):
    return np.load(os.path.join(DADOS, name))

def salvar(arr, name):
    np.save(os.path.join(DADOS, name), arr)
    print(f"[OK] {name} salvo. Shape={arr.shape}")

# -----------------------------------------------------------
# 1) Carregando dados reais
# -----------------------------------------------------------

rows_bin = load("rows_25bin.npy")     # (N, 25)
rows_real = load("rows.npy")          # (N, 15)

N = rows_bin.shape[0]
print(f"[INFO] Carregadas rows_bin={rows_bin.shape}, rows_real={rows_real.shape}")

# -----------------------------------------------------------
# 2) Funções auxiliares
# -----------------------------------------------------------

def freq_window(real_arr, win):
    """
    Frequência normalizada dos últimos 'win' sorteios.
    Real_arr é uma matriz de (N, 15) com dezenas.
    """
    freq = np.zeros((real_arr.shape[0], 25), dtype=float)

    for i in range(real_arr.shape[0]):
        ini = max(0, i - win)
        janela = real_arr[ini:i]

        if len(janela) == 0:
            continue

        for dez in janela.flatten():
            if 1 <= dez <= 25:
                freq[i, dez-1] += 1

        freq[i] /= win

    return freq

def atraso(real_arr):
    """
    Atraso normalizado para cada dezena.
    """
    N = real_arr.shape[0]
    atraso_arr = np.zeros((N, 25))

    last_pos = np.full(25, -1)

    for i in range(N):
        for d in range(1, 26):
            if d in real_arr[i]:
                last_pos[d-1] = i

        atraso_arr[i] = (i - last_pos) / N

    return atraso_arr

def volatilidade(real_arr, win=50):
    """
    Volatilidade: std local da frequência.
    """
    vol = np.zeros((real_arr.shape[0], 25))

    freq = freq_window(real_arr, win)

    for i in range(real_arr.shape[0]):
        ini = max(0, i-win)
        vol[i] = np.std(freq[ini:i+1], axis=0)

    return vol

# -----------------------------------------------------------
# 3) Gerar features
# -----------------------------------------------------------

print("[LS17-v3] Gerando features profissionais...")

f_bin = rows_bin                                 # (N,25)
f_freq25  = freq_window(rows_real, 25)           # (N,25)
f_freq50  = freq_window(rows_real, 50)           # (N,25)
f_freq200 = freq_window(rows_real, 200)          # (N,25)

f_trend = f_freq25 - f_freq50                    # (N,25)

f_atraso = atraso(rows_real)                     # (N,25)
f_volat  = volatilidade(rows_real, 50)           # (N,25)

# -----------------------------------------------------------
# 4) Empilhar tudo
# -----------------------------------------------------------

features = np.concatenate([
    f_bin,
    f_freq25,
    f_freq50,
    f_freq200,
    f_trend,
    f_atraso,
    f_volat
], axis=1)

print(f"[LS17-v3] Features finais = {features.shape}")
salvar(features, "ls17_features_v3.npy")
