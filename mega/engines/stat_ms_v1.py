# mega/engines/stat_ms_v1.py
import random
import pandas as pd
import numpy as np

CSV_PATH = "loteriamega.csv"

def gerar(qtd_dezenas: int):
    """
    Estatístico v1:
    - Frequência histórica
    - Leve viés para concursos recentes
    """
    qtd = int(qtd_dezenas)
    if qtd < 6:
        qtd = 6
    if qtd > 20:
        qtd = 20

    df = pd.read_csv(CSV_PATH)

    bolas = [f"Bola{i}" for i in range(1, 7)]
    todos = df[bolas].values.flatten()

    freq_total = pd.Series(todos).value_counts()

    # peso de recência (últimos 50 concursos)
    recentes = df.tail(50)[bolas].values.flatten()
    freq_recente = pd.Series(recentes).value_counts()

    score = freq_total.add(freq_recente * 1.5, fill_value=0)
    score = score.sort_index()

    probs = score / score.sum()

    dezenas = np.random.choice(
        probs.index,
        size=qtd,
        replace=False,
        p=probs.values
    )

    return sorted(map(int, dezenas))
