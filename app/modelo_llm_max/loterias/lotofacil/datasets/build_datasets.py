"""
build_datasets.py  — construção de datasets para LS14++ / LS15++
Suporta:
 - Lotofácil (25 dezenas)
 - Mega-Sena (60 dezenas)

Arquivos esperados em ./dados:

Lotofácil:
 - rows_25bin.npy  -> shape (N, 25), histórico em one-hot por concurso

Mega-Sena:
 - rows_60bin.npy  -> shape (N, 60), histórico em one-hot por concurso

Se ainda não tiver o rows_60bin.npy da Mega:
 - Ajuste prepare_real_data_db.py para gerar
 - Ou rode temporariamente só para lotofacil (loteria="lotofacil")
"""

import os
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")


# ------------------------ helpers básicos ------------------------

def _load_rows_lotofacil():
    path = os.path.join(DATA_DIR, "rows_25bin.npy")
    if not os.path.exists(path):
        raise FileNotFoundError(f"rows_25bin.npy não encontrado em {DATA_DIR}")
    arr = np.load(path)
    if arr.ndim != 2 or arr.shape[1] != 25:
        raise ValueError(f"rows_25bin.npy com shape inesperado: {arr.shape}")
    print("[build_datasets] Lotofácil: usando rows_25bin.npy")
    return arr


def _load_rows_mega():
    path = os.path.join(DATA_DIR, "rows_60bin.npy")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"rows_60bin.npy não encontrado em {DATA_DIR}. "
            "Gere esse arquivo no prepare_real_data_db.py para Mega-Sena."
        )
    arr = np.load(path)
    if arr.ndim != 2 or arr.shape[1] != 60:
        raise ValueError(f"rows_60bin.npy com shape inesperado: {arr.shape}")
    print("[build_datasets] Mega-Sena: usando rows_60bin.npy")
    return arr


def _build_sequences(arr: np.ndarray, window: int, last_n: int | None):
    """
    Constrói janelas (X) e labels (y) a partir de uma matriz binária arr (N, D),
    onde cada linha é um concurso e cada coluna uma dezena (one-hot).
    """
    total = arr.shape[0]

    # Se last_n for informado, usamos apenas os últimos (last_n + window) registros
    if last_n is not None:
        tamanho_min = last_n + window
        if total < tamanho_min:
            raise ValueError(
                f"Não há dados suficientes: preciso de pelo menos {tamanho_min}, "
                f"mas só tenho {total} registros."
            )
        start = total - tamanho_min
    else:
        start = 0

    arr = arr[start:]
    print(f"[build_datasets] Base recortada: {arr.shape[0]} linhas após aplicar last_n/window.")

    X_list, y_list = [], []
    for i in range(len(arr) - window):
        bloco = arr[i:i + window]   # (window, D)
        alvo = arr[i + window]      # (D,)
        X_list.append(bloco)
        y_list.append(alvo)

    X = np.stack(X_list)
    y = np.stack(y_list)

    print(f"[build_datasets] OK → X={X.shape}, y={y.shape}")
    return X.astype("float32"), y.astype("float32")


# ------------------------ LOTOFÁCIL ------------------------

def build_dataset_ls14pp(last_n=None, window=150, loteria="lotofacil"):
    """
    Dataset para LS14++.
    Por enquanto, LS14 e LS15 usam a MESMA base (25-bin / 60-bin)
    — a diferença é só a arquitetura do modelo.

    Parâmetros:
        last_n (int|None): últimos N concursos para as labels.
        window (int): tamanho da janela temporal.
        loteria (str): "lotofacil" ou "mega".
    """
    if loteria == "lotofacil":
        arr = _load_rows_lotofacil()
    elif loteria == "mega":
        arr = _load_rows_mega()
    else:
        raise ValueError("loteria deve ser 'lotofacil' ou 'mega'")

    print(f"[LS14][{loteria}] Filtro last_n → {last_n} | janela={window}")
    return _build_sequences(arr, window=window, last_n=last_n)


def build_dataset_ls15pp(last_n=None, window=150, loteria="lotofacil"):
    """
    Dataset para LS15++ (Gold / núcleo do LS16).
    Mesmo padrão do LS14, apenas separando por modelagem.

    Parâmetros:
        last_n (int|None): últimos N concursos para as labels.
        window (int): tamanho da janela temporal.
        loteria (str): "lotofacil" ou "mega".
    """
    if loteria == "lotofacil":
        arr = _load_rows_lotofacil()
    elif loteria == "mega":
        arr = _load_rows_mega()
    else:
        raise ValueError("loteria deve ser 'lotofacil' ou 'mega'")

    print(f"[LS15][{loteria}] Filtro last_n → {last_n} | janela={window}")
    return _build_sequences(arr, window=window, last_n=last_n)

def build_dataset_ls17(last_n=None, window=150):
    """
    Dataset para LS17-Transformer (Lotofácil).

    Base:
        dados/rows_25bin.npy  -> matriz (N,25) de one-hot por concurso.

    Cada exemplo:
        X[i] -> rows[i-window : i]   (janela temporal)
        y[i] -> rows[i]              (próximo concurso)

    Parâmetros:
        last_n : usa apenas os últimos N concursos (opcional)
        window : tamanho da janela temporal (default=150)
    """
    print("[build_dataset_ls17] Usando dataset rows_25bin.npy")

    rows_path = os.path.join(DATA_DIR, "rows_25bin.npy")
    if not os.path.exists(rows_path):
        raise FileNotFoundError(f"rows_25bin.npy não encontrado em {rows_path}")

    rows = np.load(rows_path)

    # Filtro de concursos recentes
    if last_n is not None and last_n < len(rows):
        rows = rows[-last_n:]
        print(f"[LS17] Filtro last_n → {last_n} registros finais usados.")

    if len(rows) <= window:
        raise ValueError(
            f"[LS17] Quantidade de linhas ({len(rows)}) <= window ({window}). "
            f"Ajuste os parâmetros."
        )

    X, y = [], []
    for i in range(window, len(rows)):
        X.append(rows[i - window:i])
        y.append(rows[i])

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    print(f"[build_dataset_ls17] OK → X={X.shape}, y={y.shape}")
    return X, y

    
