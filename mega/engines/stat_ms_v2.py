# mega/engines/stat_ms_v2.py
import random
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[3]  # ajusta conforme sua árvore
CSV_PATH = BASE_DIR / "data" / "mega" / "loteriamega.csv"


def gerar(qtd_dezenas: int):
    """
    Estatístico v2 (avançado):
    - Frequência em janelas
    - Balanceamento leve de pares/ímpares
    """
    qtd = int(qtd_dezenas)
    if qtd < 6:
        qtd = 6
    if qtd > 20:
        qtd = 20

    df = pd.read_csv(CSV_PATH)
    bolas = [f"Bola{i}" for i in range(1, 7)]

    # janelas
    w_curta = df.tail(30)[bolas].values.flatten()
    w_media = df.tail(120)[bolas].values.flatten()
    w_longa = df[bolas].values.flatten()

    s_curta = pd.Series(w_curta).value_counts() * 2.0
    s_media = pd.Series(w_media).value_counts() * 1.2
    s_longa = pd.Series(w_longa).value_counts() * 0.8

    score = s_longa.add(s_media, fill_value=0).add(s_curta, fill_value=0)
    score = score.sort_index()

    probs = score / score.sum()

    dezenas = np.random.choice(
        probs.index,
        size=qtd,
        replace=False,
        p=probs.values
    )

    dezenas = list(map(int, dezenas))

    # ajuste leve de paridade (não forçar demais)
    pares = [d for d in dezenas if d % 2 == 0]
    impares = [d for d in dezenas if d % 2 == 1]

    if abs(len(pares) - len(impares)) > 2:
        # rebalanceia se ficou muito desigual
        pool = list(set(range(1, 61)) - set(dezenas))
        random.shuffle(pool)
        while abs(len(pares) - len(impares)) > 2 and pool:
            x = pool.pop()
            if len(pares) > len(impares) and x % 2 == 1:
                dezenas[random.randrange(len(pares))] = x
                pares.pop()
                impares.append(x)
            elif len(impares) > len(pares) and x % 2 == 0:
                dezenas[random.randrange(len(impares))] = x
                impares.pop()
                pares.append(x)

    return sorted(dezenas)
