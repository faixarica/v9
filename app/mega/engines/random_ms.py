# mega/engines/random_ms.py
import random

def gerar(qtd_dezenas: int):
    """
    Geração totalmente aleatória (baseline).
    Retorna uma lista ordenada de dezenas únicas entre 1 e 60.
    """
    qtd = int(qtd_dezenas)
    if qtd < 6:
        qtd = 6
    if qtd > 20:
        qtd = 20

    return sorted(random.sample(range(1, 61), qtd))
