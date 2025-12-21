"""
build_ls17_features_v3_v2.py — FaixaBet LS17-v3/v4
---------------------------------------------------

Versão: 2.0
Data: 2025-11-25
Autor: fAIxaBet / Pipeline Oficial LS17

Objetivo:
    Gerar o arquivo ls17_features_v3.npy contendo
    features profissionais de 150 dimensões para 
    o modelo LS17 (Transformer / MLP / Híbrido).

Entradas (sempre alinhadas):
    • dados/rows_25bin.npy   → matriz 25-hot (N,25)
    • dados/rows.npy         → dezenas reais por concurso (N,15)

Saída:
    • dados/ls17_features_v3.npy → (N,150)

Resumo das features:
    - f_bin      = 25-hot do concurso atual
    - f_freq25   = frequência últimas 25 dezenas
    - f_freq50   = frequência últimas 50 dezenas
    - f_freq200  = frequência últimas 200 dezenas
    - f_trend    = f_freq25 - f_freq50 (tendência/derivada)
    - f_atraso   = atraso normalizado (0..1)
    - f_volat    = volatilidade local (janela 50)

Como usar:
    python build_ls17_features_v3_v2.py

Requisitos:
    - rows_25bin.npy e rows.npy devem estar no mesmo N
    - Executar APÓS gerar rows_25bin.npy
"""

import numpy as np
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# 🌎 Pasta global de dados: modelo_llm_max/dados
DADOS = os.path.abspath(os.path.join(BASE, "..", "..", "..", "dados"))

# ---------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------

def load_file(name: str):
    """Carrega arquivo .npy da pasta global modelo_llm_max/dados"""
    path = os.path.join(DADOS, name)
    print(f"[LOAD] {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERRO] Arquivo obrigatório não encontrado: {path}")
    return np.load(path)



def freq_window(real_arr, win):
    """
    Frequência normalizada da janela dos últimos 'win' concursos.
    real_arr -> matriz (N,15)
    Retorna matriz (N,25)
    """
    N = real_arr.shape[0]
    freq = np.zeros((N, 25), dtype=float)

    for i in range(N):
        ini = max(0, i - win)
        janela = real_arr[ini:i]

        if len(janela) == 0:
            continue

        for dez in janela.flatten():
            if 1 <= dez <= 25:
                freq[i, dez - 1] += 1

        # normaliza pela janela completa
        freq[i] /= win

    return freq


def atraso(real_arr):
    """
    Calcula atraso normalizado (0..1) das 25 dezenas.
    real_arr -> (N,15)
    Retorna matriz (N,25)
    """
    N = real_arr.shape[0]
    atrasos = np.zeros((N, 25), dtype=float)

    last_seen = np.full(25, -1)

    for i in range(N):
        for d in range(1, 26):
            if d in real_arr[i]:
                last_seen[d - 1] = i

        atrasos[i] = (i - last_seen) / N

    return atrasos


def volatilidade(real_arr, win=50):
    """
    Volatilidade local: desvio padrão da frequência
    numa janela de 'win' concursos.
    """
    N = real_arr.shape[0]
    vol = np.zeros((N, 25), dtype=float)

    freq = freq_window(real_arr, win)

    for i in range(N):
        ini = max(0, i - win)
        vol[i] = np.std(freq[ini:i+1], axis=0)

    return vol


# ---------------------------------------------------------
# Processamento principal
# ---------------------------------------------------------

def main():
    print("🔧 [LS17-v3/v4] Gerando ls17_features_v3.npy ...")

    # 1) Carregar entradas
    rows_bin = load_file("rows_25bin.npy")   # (N,25)
    rows_real = load_file("rows.npy")        # (N,15)

    if rows_bin.shape[0] != rows_real.shape[0]:
        raise ValueError(
            f"[ERRO] rows_25bin (N={rows_bin.shape[0]}) "
            f"≠ rows (N={rows_real.shape[0]}) — desalinhamento detectado!"
        )

    N = rows_bin.shape[0]

    print(f"   • rows_25bin = {rows_bin.shape}")
    print(f"   • rows       = {rows_real.shape}")

    # 2) Gerar features avançadas
    print("   • Calculando frequências (25/50/200)...")
    f_freq25  = freq_window(rows_real, 25)
    f_freq50  = freq_window(rows_real, 50)
    f_freq200 = freq_window(rows_real, 200)

    print("   • Calculando tendência (trend)...")
    f_trend = f_freq25 - f_freq50

    print("   • Calculando atraso...")
    f_atraso = atraso(rows_real)

    print("   • Calculando volatilidade...")
    f_volat = volatilidade(rows_real, 50)

    # 3) Empilhar tudo
    print("   • Empilhando matriz final...")
    features = np.concatenate([
        rows_bin,     # 25
        f_freq25,     # 25
        f_freq50,     # 25
        f_freq200,    # 25
        f_trend,      # 25
        f_atraso,     # 25
        f_volat       # 25
    ], axis=1)

    # 150 features: 25 x 6 = 150
    print(f"   ✔ Features finais = {features.shape} (esperado: N,150)")

    # 4) Salvar
    out = os.path.join(DADOS, "ls17_features_v3.npy")
    np.save(out, features)

    print("-------------------------------------------------")
    print("✔ LS17-v3 features geradas com sucesso!")
    print(f"  Arquivo salvo: {out}")
    print(f"  Shape final: {features.shape}")
    print("-------------------------------------------------")


if __name__ == "__main__":
    main()
