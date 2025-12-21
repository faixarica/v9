"""
Exportação de modelos por plano
Free → LS14
Silver → LS14 + LS15
Gold → LS14 + LS15 + LS17-v3
Platinum → LS18-v3
"""

import shutil
import os

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "models", "prod")
DEST = os.path.join(BASE, "models", "planos")

os.makedirs(DEST, exist_ok=True)

planos = {
    "free": [
        "recent_ls14pp_final.keras"
    ],
    "silver": [
        "recent_ls14pp_final.keras",
        "recent_ls15pp_final.keras"
    ],
    "gold": [
        "recent_ls14pp_final.keras",
        "recent_ls15pp_final.keras",
        "ls17_lotofacil_v3.keras"
    ],
    "platinum": [
        "ls18_ensemble_v3.keras"
    ]
}

for plano, arquivos in planos.items():
    p_dir = os.path.join(DEST, plano)
    os.makedirs(p_dir, exist_ok=True)

    for arq in arquivos:
        src = os.path.join(SRC, arq)
        dst = os.path.join(p_dir, arq)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"[OK] Copiado para {plano}: {arq}")
