"""
ensemble_v3.py — FaixaBet v2.7
Avalia LS14 / LS15 / LS17-v2 e gera ensemble LS18 (Lotofácil).
Avalia também modelos Mega-Sena se existirem.

Lotofácil:
  - Base rows_25bin.npy (25 dezenas binárias)
  - Modelos esperados em models/prod:
      recent_ls14pp_final.keras
      mid_ls14pp_final.keras
      global_ls14pp_final.keras
      recent_ls15pp_final.keras
      mid_ls15pp_final.keras
      global_ls15pp_final.keras
      ls17_lotofacil_v2.keras

  - Ensemble LS18 = combinação ponderada de:
      ls14pp-recent, ls15pp-recent, ls17-v2

Saídas:
  - Ranking em console
  - CSV em admin/tests_v3/
"""

import os
import argparse
from datetime import datetime

import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
MODELS_DIR = os.path.join(BASE_DIR, "models", "prod")
OUT_DIR = os.path.join(BASE_DIR, "admin", "tests_v3")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def make_sequences(rows: np.ndarray, window: int):
    if rows.ndim != 2:
        raise ValueError(f"rows deve ser [N, F]; veio {rows.shape}")
    n, f = rows.shape
    if n <= window:
        raise ValueError(f"N ({n}) <= window ({window})")

    X = []
    y = []
    for i in range(n - window):
        X.append(rows[i:i + window])
        y.append(rows[i + window])
    return np.asarray(X, np.float32), np.asarray(y, np.float32)


def binarize_topk(probs: np.ndarray, k: int):
    n, f = probs.shape
    out = np.zeros_like(probs, dtype=np.float32)
    idx = np.argpartition(probs, -k, axis=1)[:, -k:]
    rows_idx = np.arange(n)[:, None]
    out[rows_idx, idx] = 1.0
    return out


def compute_metrics(y_true: np.ndarray, y_pred_bin: np.ndarray):
    """
    y_true, y_pred_bin: [N, 25]
    """
    assert y_true.shape == y_pred_bin.shape
    hits = (y_true * y_pred_bin).sum(axis=1)
    n = len(hits)
    return {
        "media": float(hits.mean()),
        "t11": float((hits >= 11).mean() * 100.0),
        "t12": float((hits >= 12).mean() * 100.0),
        "t13": float((hits >= 13).mean() * 100.0),
        "t14": float((hits >= 14).mean() * 100.0),
        "t15": float((hits >= 15).mean() * 100.0),
        "n_tests": int(n),
    }


def metrics_to_row(name: str, m: dict):
    return {
        "modelo": name,
        "media": m["media"],
        "t11": m["t11"],
        "t12": m["t12"],
        "t13": m["t13"],
        "t14": m["t14"],
        "t15": m["t15"],
        "n_tests": m["n_tests"],
    }


def safe_load_model(path: str):
    if not os.path.exists(path):
        print(f"[AVISO] Modelo não encontrado: {path}")
        return None
    try:
        return load_model(path)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar {path}: {e}")
        return None


# ---------------------------------------------------------
# Lotofácil + LS18
# ---------------------------------------------------------
WEIGHTS_LS18 = {
    "ls14pp-recent": 0.38,
    "ls15pp-recent": 0.32,
    "ls17-v2": 0.30,
}


def avaliar_lotofacil(lf_window: int, limit: int, n_test: int):
    print("===============================================")
    print(f"Avaliação LOTOFÁCIL — window={lf_window} | limit={limit} | n_test={n_test}")
    print("===============================================")

    rows_path = os.path.join(DADOS_DIR, "rows_25bin.npy")
    if not os.path.exists(rows_path):
        print(f"[ERRO] rows_25bin.npy não encontrado em {rows_path}")
        return None

    rows = np.load(rows_path)  # (N, 25)
    if limit and limit < len(rows):
        rows = rows[-limit:]

    # Apenas para log geral
    X_base, y_base = make_sequences(rows, lf_window)
    if n_test and n_test < len(X_base):
        X_dbg = X_base[-n_test:]
        y_dbg = y_base[-n_test:]
    else:
        X_dbg, y_dbg = X_base, y_base
    print(f"[dataset] X={X_dbg.shape}, y={y_dbg.shape}")

    modelos_info = [
        ("ls14pp-recent", "recent_ls14pp_final.keras"),
        ("ls14pp-mid",    "mid_ls14pp_final.keras"),
        ("ls14pp-global", "global_ls14pp_final.keras"),
        ("ls15pp-recent", "recent_ls15pp_final.keras"),
        ("ls15pp-mid",    "mid_ls15pp_final.keras"),
        ("ls15pp-global", "global_ls15pp_final.keras"),
        ("ls17-v2",       "ls17_lotofacil_v2.keras"),
    ]

    rows_metrics = []
    probs_list = []  # (name, probs, y_true)

    for name, fname in modelos_info:
        path = os.path.join(MODELS_DIR, fname)
        model = safe_load_model(path)
        if model is None:
            continue

        input_shape = model.input_shape
        _, w_model, f_model = input_shape

        if name.startswith("ls17"):
            # LS17 usa ls17_features_final.npy
            lf_final_path = os.path.join(DADOS_DIR, "ls17_features_final.npy")
            if not os.path.exists(lf_final_path):
                print(f"[AVISO] {name}: ls17_features_final.npy não encontrado, pulando.")
                continue

            data = np.load(lf_final_path)  # (N, 125)
            feats = data[:, :100]
            labels = data[:, 100:]         # (N, 25)

            if feats.shape[1] != 100 or labels.shape[1] != 25:
                print(f"[AVISO] {name}: shapes inesperados em ls17_features_final.npy {data.shape}")
                continue

            X_all, _ = make_sequences(feats, w_model)
            y_all = labels[w_model:]

            if n_test and n_test < len(X_all):
                X_m = X_all[-n_test:]
                y_m = y_all[-n_test:]
            else:
                X_m, y_m = X_all, y_all

            print(f"[{name}] window={w_model}  X={X_m.shape}, y={y_m.shape}")

        else:
            # LS14/15 usam rows_25bin (25 features)
            if rows.shape[1] != f_model:
                print(f"[AVISO] {name}: f_model={f_model} mas rows tem {rows.shape[1]} colunas; pulando.")
                continue

            X_all, y_all = make_sequences(rows, w_model)
            if n_test and n_test < len(X_all):
                X_m = X_all[-n_test:]
                y_m = y_all[-n_test:]
            else:
                X_m, y_m = X_all, y_all

            print(f"[{name}] window={w_model}  X={X_m.shape}, y={y_m.shape}")

        probs = model.predict(X_m, verbose=0)  # (N, 25)
        y_pred_bin = binarize_topk(probs, k=15)
        metrics = compute_metrics(y_m, y_pred_bin)

        print(
            f" → {name}: media={metrics['media']:.2f}, "
            f"≥11={metrics['t11']:.1f}%, ≥12={metrics['t12']:.1f}%, "
            f"≥13={metrics['t13']:.1f}%, ≥14={metrics['t14']:.1f}%, "
            f"15={metrics['t15']:.1f}%"
        )

        rows_metrics.append(metrics_to_row(name, metrics))
        probs_list.append((name, probs, y_m))

    # ----------------- Ensemble LS18 -----------------
    ens_names = ["ls14pp-recent", "ls15pp-recent", "ls17-v2"]
    ens_items = [(n, p, y) for (n, p, y) in probs_list if n in ens_names]

    if len(ens_items) >= 2:
        min_n = min(p.shape[0] for (_, p, _) in ens_items)
        probs_stack = []
        weights = []
        y_ref = None

        for n, p, y_m in ens_items:
            probs_stack.append(p[-min_n:])
            if y_ref is None:
                y_ref = y_m[-min_n:]
            weights.append(WEIGHTS_LS18.get(n, 1.0 / len(ens_items)))

        probs_stack = np.stack(probs_stack, axis=0)  # [M, N, 25]
        w_arr = np.asarray(weights, np.float32)
        w_arr = w_arr / w_arr.sum()
        w_arr = w_arr[:, None, None]

        ensemble_probs = (probs_stack * w_arr).sum(axis=0)  # [N, 25]
        y_pred_bin = binarize_topk(ensemble_probs, k=15)
        metrics = compute_metrics(y_ref, y_pred_bin)

        name_ens = "ls18-ensemble"
        print("\n[LS18] Ensemble Lotofácil (LS14+LS15+LS17-v2)")
        print(
            f" → {name_ens}: media={metrics['media']:.2f}, "
            f"≥11={metrics['t11']:.1f}%, ≥12={metrics['t12']:.1f}%, "
            f"≥13={metrics['t13']:.1f}%, ≥14={metrics['t14']:.1f}%, "
            f"15={metrics['t15']:.1f}%"
        )

        rows_metrics.append(metrics_to_row(name_ens, metrics))
    else:
        print("[AVISO] Ensemble LS18 não pôde ser montado (modelos insuficientes).")

    if rows_metrics:
        df = pd.DataFrame(rows_metrics)
        df = df[["modelo", "media", "t11", "t12", "t13", "t14", "t15", "n_tests"]]
        df = df.sort_values(by=["t13", "t14", "t15", "media"], ascending=False)

        print("\n================= RANKING REAL (Lotofácil) =================")
        print(df.to_string(index=False))

        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_csv = os.path.join(OUT_DIR, f"ranking_lotofacil_lsmodels_v3_{ts}.csv")
        df.to_csv(out_csv, index=False, sep=";")
        print(f"\n[OK] Ranking Lotofácil salvo em: {out_csv}")
        return df
    else:
        print("[AVISO] Nenhuma métrica calculada para Lotofácil.")
        return None


# ---------------------------------------------------------
# Mega-Sena (reaproveita sua versão anterior quase intacta)
# ---------------------------------------------------------
def avaliar_mega(limit: int, n_test: int):
    print("\n===============================================")
    print(f"Avaliação MEGA-SENA — limit={limit} | n_test={n_test}")
    print("===============================================")

    rows_path = os.path.join(DADOS_DIR, "rows_60bin.npy")
    if not os.path.exists(rows_path):
        print(f"[AVISO] rows_60bin.npy não encontrado; pulando Mega-Sena.")
        return None

    rows = np.load(rows_path)
    if limit and limit < len(rows):
        rows = rows[-limit:]

    modelos_info = [
        ("ls14pp-recent-mega", "recent_ls14pp_mega_final.keras"),
        ("ls14pp-mid-mega",    "mid_ls14pp_mega_final.keras"),
        ("ls14pp-global-mega", "global_ls14pp_mega_final.keras"),
        ("ls15pp-recent-mega", "recent_ls15pp_mega_final.keras"),
        ("ls15pp-mid-mega",    "mid_ls15pp_mega_final.keras"),
        ("ls15pp-global-mega", "global_ls15pp_mega_final.keras"),
    ]

    first_model = None
    first_info = None
    for name, fname in modelos_info:
        path = os.path.join(MODELS_DIR, fname)
        m = safe_load_model(path)
        if m is not None:
            first_model = m
            first_info = (name, fname)
            break

    if first_model is None:
        print("[AVISO] Nenhum modelo Mega-Sena carregado; pulando.")
        return None

    _, window, f = first_model.input_shape
    if f != 60:
        print(f"[AVISO] Modelo Mega-Sena com F={f} (esperado 60); pulando.")
        return None

    X_all, y_all = make_sequences(rows, window)
    if n_test and n_test < len(X_all):
        X = X_all[-n_test:]
        y = y_all[-n_test:]
    else:
        X, y = X_all, y_all

    print(f"[Mega] window={window}  X={X.shape}, y={y.shape}")

    def compute_metrics_mega(y_true, y_pred_bin):
        hits = (y_true * y_pred_bin).sum(axis=1)
        n = len(hits)
        return {
            "media": float(hits.mean()),
            "t4": float((hits >= 4).mean() * 100.0),
            "t5": float((hits >= 5).mean() * 100.0),
            "t6": float((hits >= 6).mean() * 100.0),
            "n_tests": int(n),
        }

    hit_keys = ["media", "t4", "t5", "t6"]
    rows_metrics = []

    modelos_loaded = [(first_info[0], first_info[1], first_model)]
    for name, fname in modelos_info:
        if first_info and fname == first_info[1]:
            continue
        m = safe_load_model(os.path.join(MODELS_DIR, fname))
        if m is not None:
            modelos_loaded.append((name, fname, m))

    for name, fname, model in modelos_loaded:
        probs = model.predict(X, verbose=0)
        y_pred_bin = binarize_topk(probs, k=6)
        mtr = compute_metrics_mega(y, y_pred_bin)
        print(
            f" → {name}: media={mtr['media']:.2f}, "
            f"≥4={mtr['t4']:.1f}%, ≥5={mtr['t5']:.1f}%, ≥6={mtr['t6']:.1f}%"
        )
        row = {"modelo": name}
        row.update({k: mtr[k] for k in hit_keys})
        row["n_tests"] = mtr["n_tests"]
        rows_metrics.append(row)

    if rows_metrics:
        df = pd.DataFrame(rows_metrics)
        df = df[["modelo"] + hit_keys + ["n_tests"]].sort_values(
            by=["t6", "t5", "t4", "media"], ascending=False
        )

        print("\n================= RANKING REAL (Mega-Sena) =================")
        print(df.to_string(index=False))

        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_csv = os.path.join(OUT_DIR, f"ranking_megasena_lsmodels_v3_{ts}.csv")
        df.to_csv(out_csv, index=False, sep=";")
        print(f"\n[OK] Ranking Mega-Sena salvo em: {out_csv}")
        return df
    else:
        print("[AVISO] Nenhuma métrica calculada para Mega-Sena.")
        return None


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Ensemble v3 — LS14 / LS15 / LS17 / LS18")
    p.add_argument("--lf_window", type=int, default=150)
    p.add_argument("--lf_limit", type=int, default=220)
    p.add_argument("--lf_n_test", type=int, default=70)
    p.add_argument("--mega_limit", type=int, default=220)
    p.add_argument("--mega_n_test", type=int, default=70)
    return p.parse_args()


def main():
    args = parse_args()
    avaliar_lotofacil(args.lf_window, args.lf_limit, args.lf_n_test)
    avaliar_mega(args.mega_limit, args.mega_n_test)


if __name__ == "__main__":
    main()
