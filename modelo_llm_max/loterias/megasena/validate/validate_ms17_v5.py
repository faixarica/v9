import sys
import argparse
from pathlib import Path

# -----------------------------
# CLI
# -----------------------------
parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode",
    choices=["strict", "flex"],
    default="flex",
    help="Modo de execução"
)
args = parser.parse_args()

MODE = args.mode.upper()

def exit_ok():
    sys.exit(0)

def exit_warn(msg, code=10):
    print(f"[WARN] {msg}")
    sys.exit(code)

def exit_block(msg, code=20):
    print(f"[BLOCK] {msg}")
    sys.exit(code)

def exit_fatal(msg):
    print(f"[FATAL] {msg}")
    sys.exit(1)

import sys
import os
sys.path.append(os.getcwd())
from paths import data_path

# -----------------------------
# LOGICA REAL
# -----------------------------
try:
    # Validate against the ACTUAL output of prepare_ms17_v4.py
    data_file = Path(data_path("X_ms17_v4.npy"))

    if not data_file.exists():
        if MODE == "STRICT":
            exit_fatal(f"Arquivo de dados não encontrado: {data_file}")
        else:
            exit_block(f"Dados ainda não preparados: {data_file}")

    # Exemplo de validação
    import numpy as np
    data = np.load(data_file)
    rows = data.shape[0]

    if rows < 1000:
        if MODE == "STRICT":
            exit_fatal("Dataset insuficiente")
        else:
            exit_warn(f"Dataset pequeno ({rows} linhas)")

    print("VALIDATE OK")
    exit_ok()

except Exception as e:
    exit_fatal(str(e))
