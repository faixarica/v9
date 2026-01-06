import os
from modelo_llm_max.load_models import (
    load_ls14pp,
    load_ls15pp,
    load_ls16,
    load_ls17,
    load_ls18
)

def carregar_modelo_ls(modelo: str, nome_plano=None, models_dir=None):
    """
    Adapta os loaders novos (load_ls14pp, load_ls15pp...) para o formato
    que o gerar_palpite_ls() espera: lista de METAS.
    """

    metas = []

    try:
        if modelo == "ls14":
            d = load_ls14pp()
            for nome, m in d.items():
                metas.append({
                    "model": m,
                    "path": f"ls14pp/{nome}",
                    "expected_seq_len": 1550  # ajuste se precisar
                })

        elif modelo == "ls15":
            d = load_ls15pp()
            for nome, m in d.items():
                metas.append({
                    "model": m,
                    "path": f"ls15pp/{nome}",
                    "expected_seq_len": 1550
                })

        elif modelo == "ls16":
            m = load_ls16()
            metas.append({
                "model": m,
                "path": "ls16/ls16_platinum",
                "expected_seq_len": 1550
            })

        elif modelo == "ls17":
            m = load_ls17()
            metas.append({
                "model": m,
                "path": "ls17/ls17_v3",
                "expected_seq_len": 1550
            })

        elif modelo == "ls18":
            m = load_ls18()
            metas.append({
                "model": m,
                "path": "ls18/ls18_mini",
                "expected_seq_len": 1550
            })

    except Exception as e:
        print("[carregar_modelo_ls] erro:", e)
        return []

    return metas
