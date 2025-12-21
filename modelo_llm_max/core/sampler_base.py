import numpy as np
def normalize_scores(scores, k_needed=None):
    """
    Normaliza vetor de scores para probabilidades válidas.
    Se houver NaN, inf, soma zero, ou poucos valores >0 (menos que k),
    cai para distribuição uniforme.
    """
    scores = np.array(scores, dtype=float).flatten()

    # Corrige elementos inválidos
    if not np.all(np.isfinite(scores)):
        scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)

    # Conta quantas posições realmente têm chance (> 0)
    positive = np.sum(scores > 0)

    # Se precisar garantir k escolhas distintas:
    if k_needed is not None and positive < k_needed:
        return np.ones(25, dtype=float) / 25.0

    total = scores.sum()
    if total <= 0:
        return np.ones(25, dtype=float) / 25.0

    return scores / total

def sample_k_dezenas(scores, k=15, rng=None):
    if rng is None:
        rng = np.random.default_rng()

    probs = normalize_scores(scores, k_needed=k)

    dezenas = rng.choice(
        np.arange(1, 26),
        size=k,
        replace=False,
        p=probs
    )

    return sorted(int(x) for x in dezenas)
def sample_k_dezenas_intermediario(
    scores: np.ndarray,
    k: int = 15,
    temp: float = 1.0,
    entropy_boost: bool = False
):
    """
    Sampler intermediário com suavização por temperatura e boost de entropia.

    - Mantém compatibilidade total com sample_k_dezenas().
    - Temperatura > 1.0 => deixa mais aleatório
    - Temperatura < 1.0 => deixa mais determinístico
    - entropy_boost=True => distribui peso extra nas dezenas com menor score
                           útil quando scores estão 'travados' em poucas dezenas.

    Retorna: lista de k dezenas (1..25)
    """

    # 1) Proteções básicas
    if scores is None or len(scores) != 25:
        return list(np.random.choice(range(1, 26), size=k, replace=False))

    s = np.array(scores, dtype=float).copy()

    # 2) Normaliza prevenindo zeros
    s = np.maximum(s, 1e-9)
    s = s / s.sum()

    # 3) Aplica temperatura
    #    temp > 1 deixa distribuição mais plana (mais diversidade)
    #    temp < 1 deixa mais 'pico' (mais determinístico)
    if temp != 1.0:
        s = np.power(s, 1.0 / temp)
        s = s / s.sum()

    # 4) Entropy boost opcional
    if entropy_boost:
        # Cria um "peso inverso": dezenas que tinham score baixo ganham boost
        inv = (1.0 / (s + 1e-12))
        inv = inv / inv.sum()
        # mistura pequena — sem destruir o shape original
        s = 0.85 * s + 0.15 * inv
        s = s / s.sum()

    # 5) Amostragem final (sem repetição)
    dezenas = np.random.choice(
        np.arange(1, 26),
        size=k,
        replace=False,
        p=s
    )

    return sorted(int(x) for x in dezenas)
