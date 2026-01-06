"""
prepare_real_data_ls17_v4.py — Lotofácil LS17-v4
------------------------------------------------
Gera um feature set unificado LS17-v4 combinando versões anteriores.

Entrada (todos em modelo_llm_max/dados):
    - ls17_features.npy      -> features v2 (N, F2)
    - ls17_features_v3.npy   -> features v3 (N, F3)

Saída:
    - ls17_features_v4.npy   -> features unificadas (N, F2+F3)
"""

import os
import numpy as np

# === Paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Diretório global de dados: ...\modelo_llm_max\dados
DADOS_DIR = os.path.join(BASE_DIR, "..", "..", "..", "dados")
DADOS_DIR = os.path.abspath(DADOS_DIR)


def load_file(name: str) -> np.ndarray:
    """
    Carrega um .npy do diretório global de dados com log decente.
    """
    path = os.path.join(DADOS_DIR, name)
    path = os.path.abspath(path)
    print(f"[LOAD] {name}  ->  {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERRO] Arquivo não encontrado: {path}")

    arr = np.load(path)
    print(f"[OK] {name} shape={arr.shape}")
    return arr


def main():
    print("🔧 [LS17-v4] Gerando features unificadas LS17-v4...")
    print(f"[INFO] DADOS_DIR = {DADOS_DIR}")

    # Carrega versões anteriores
    # Ajuste os nomes aqui se na sua pasta /dados o naming for diferente
    feats_v2 = load_file("ls17_features.npy")       # (N, F2)
    feats_v3 = load_file("ls17_features_v3.npy")    # (N, F3)

    if feats_v2.shape[0] != feats_v3.shape[0]:
        raise ValueError(
            f"[ERRO] N diferentes entre v2 e v3: "
            f"v2={feats_v2.shape[0]}  v3={feats_v3.shape[0]}"
        )

    # Concatena feature sets ao longo do eixo das features
    feats_v4 = np.concatenate([feats_v2, feats_v3], axis=1)
    print(f"[OK] feats_v4 shape={feats_v4.shape}")

    # Salva no diretório global de dados
    out_name = "ls17_features_v4.npy"
    out_path = os.path.join(DADOS_DIR, out_name)
    out_path = os.path.abspath(out_path)

    np.save(out_path, feats_v4)
    print(f"✅ [DONE] {out_name} salvo em: {out_path}")


if __name__ == "__main__":
    main()
