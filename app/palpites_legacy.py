# -*- coding: utf-8 -*-
"""
palpites_legacy.py (ex-palpites_v8.15.py) v9.13.1  
Consolidado, compatível com Streamlit e PostgreSQL.

MAIS
Inclui:
- geração de palpites (estatístico, pares/ímpares, LS14, LS15, LS16)
- novo pipeline incrementado (LS16/LS17/LS18)
- controle de limites por plano
- salvamento e histórico
"""
TF_ENABLE_ONEDNN_OPTS=0

import os
import sys
import logging

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ============================================================
# 🔧 Controle do pipeline (LEGACY / NOVO)  git
# ============================================================
# Use no ambiente:
#   export USE_NEW_MODEL_PIPELINE=1

USE_NEW_PIPELINE = os.getenv("USE_NEW_MODEL_PIPELINE", "0") == "1"
# FORCE OFF:
USE_NEW_PIPELINE = False

# ============================================================
# 🔧 Estrutura de diretórios
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Pasta dos modelos LS14/LS15/LS16/LS17/LS18
MODEL_ROOT = os.path.join(ROOT_DIR, "modelo_llm_max")
if MODEL_ROOT not in sys.path:
    sys.path.append(MODEL_ROOT)

logging.info(f" Pipeline novo ativo? {USE_NEW_PIPELINE}")
logging.info(f" MODEL_ROOT = {MODEL_ROOT}")
logging.info(f" BASE_DIR  = {BASE_DIR}")
logging.info(f" ROOT_DIR  = {ROOT_DIR}")

import json
import math
import random
import re
from datetime import datetime, date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import text, create_engine

from app.db import Session

# --- LS16: ensemble inteligente (tenta usar modelo_llm_max/ensemble.py)
try:
    from modelo_llm_max.ensemble import gerar_palpite_ensemble as _fxb_ls16_ensemble
except Exception:
    _fxb_ls16_ensemble = None

from modelo_llm_max.utils_ls_loader import carregar_modelo_ls

# (opcional) deixa o layout wide, mas não resolve o flash sozinho

# =========================
# CONFIG LOG
# =========================

DEBUG_MODE = os.environ.get("DEBUG_MODE", "0") == "1"
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

def _safe_rerun():
    """Rerun compatível com versões novas e antigas do Streamlit."""
    try:
        st.rerun()  # Streamlit ≥ 1.27
    except AttributeError:
        # Streamlit mais antigo
        _safe_rerun()

        
def _log_info(msg):
    logging.info(msg)
    if DEBUG_MODE:
        st.info(msg)

def _log_warn(msg):
    logging.warning(msg)
    if DEBUG_MODE:
        st.warning(msg)

def get_conn():
    """
    Retorna conexão SQLAlchemy com o banco PostgreSQL (Neon.tech).
    Usa variáveis de ambiente: DATABASE_URL, POSTGRES_URL ou PG_URI.
    """
    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("PG_URI")
    )

    if not db_url:
        st.error("❌ Variável de conexão DATABASE_URL não encontrada no ambiente.")
        return None

    try:
        engine = create_engine(db_url)
        return engine.connect()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# =========================
# FUNÇÕES AUXILIARES
# =========================
def _existing_cols(table_name: str) -> set:
    """Retorna o conjunto de nomes de colunas existentes."""
    db = Session()
    try:
        rows = db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :t
        """), {"t": table_name}).fetchall()
        return {r[0] for r in rows} if rows else set()
    except Exception as e:
        _log_warn(f"Erro ao buscar colunas da tabela {table_name}: {e}")
        return set()
    finally:
        db.close()

# ================== [MODEL BRIDGE] LS14 / LS15 / LS16 ==================

# --- caminhos / arquivos
BASE_DIR = os.getcwd()
# -------- Estatístico (freq + recência + correlação) --------
import pandas as pd

def _carregar_df_lotofacil():
    """
    Fonte oficial PRD: banco.
    Retorna (df, bolas) compatível com _stats_pack().
    """
    db = Session()
    try:
        rows = db.execute(text("""
            SELECT
                data,
                n1, n2, n3, n4, n5,
                n6, n7, n8, n9, n10,
                n11, n12, n13, n14, n15
            FROM resultados_oficiais
            ORDER BY data DESC
        """)).fetchall()

        if not rows:
            raise RuntimeError("Sem registros em resultados_oficiais (Lotofácil).")

        bolas = [f"Bola{i}" for i in range(1, 16)]
        df = pd.DataFrame(rows, columns=["data"] + bolas)

        # padroniza como o legado esperava: '01'..'25'
        for b in bolas:
            df[b] = df[b].astype(int).astype(str).str.zfill(2)

        return df, bolas
    finally:
        db.close()

@lru_cache(maxsize=1)
def _stats_pack(recencia=100):
    df, bolas = _carregar_df_lotofacil()

    # Frequência global
    todas = df[bolas].values.flatten()
    freq_global = pd.Series(todas).value_counts().sort_index()
    freq_global = {int(k): int(v) for k, v in freq_global.items()}

    # Frequência recente
    subset = df.head(recencia) if len(df) > recencia else df
    todas_rec = subset[bolas].values.flatten()
    freq_rec = pd.Series(todas_rec).value_counts().sort_index()
    freq_rec = {int(k): int(v) for k, v in freq_rec.items()}

    # Correlação (coocorrência par-a-par)
    nums_df = df[bolas].apply(pd.to_numeric)
    corr = pd.DataFrame(0, index=range(1, 26), columns=range(1, 26))
    for _, row in nums_df.iterrows():
        arr = row.values
        for i in range(15):
            for j in range(i+1, 15):
                a, b = int(arr[i]), int(arr[j])
                corr.loc[a, b] += 1
                corr.loc[b, a] += 1

    return freq_global, freq_rec, corr, df, bolas

def scores_estatisticos(alpha_hist=0.7, alpha_recent=0.3):
    """
    Frequência histórica + recência (vetor 25 normalizado).
    """
    freq_global, freq_rec, _, _, _ = _stats_pack()
    v = np.zeros(25, dtype=float)
    for d in range(1, 26):
        g = float(freq_global.get(d, 0))
        r = float(freq_rec.get(d, 0))
        v[d-1] = alpha_hist * g + alpha_recent * r
    return _normalize_probs(v)

def scores_correlacao(boost_from=set()):
    """
    Coocorrência: soma linhas da matriz de coocorrência para dezenas 'boost_from'.
    """
    _, _, corr, _, _ = _stats_pack()
    if not boost_from:
        return np.ones(25, dtype=float) / 25.0
    s = np.zeros(25, dtype=float)
    for b in boost_from:
        try:
            bi = int(b)
            if 1 <= bi <= 25:
                s += np.asarray(corr.loc[bi].values, dtype=float)
        except Exception:
            continue
    s = np.maximum(s, 0.0)
    return _normalize_probs(s)

# cache global para evitar loop recursivo
# --- Anti-loop / caches globais ---
_IN_SCORES_LS16 = False         # flag de reentrância para LS16
_LS15_CACHE = None              # cache de vetor (25,) vindo do LS15
_LOADED_METAS = {}              # cache de modelos carregados por (model_name, models_dir, mtime)

@lru_cache(maxsize=1)
def combinacoes_ja_sorteadas():
    """Set de tuplas(15) com todas as combinações já sorteadas (para veto)."""
    _, _, _, df, bolas = _stats_pack()
    usados = set(tuple(sorted(map(int, r[bolas].values))) for _, r in df.iterrows())
    return usados


# -------- Adapters LS14 / LS15 (não quebram se modelo não estiver pronto) --------
def prepare_seq(T: int):
    """
    Prepara uma sequência neutra de entrada para modelos LS14/LS15/LS16.
    shape esperado: (1, T, 25)
    """
    import numpy as np

    # Distribuição uniforme por dezena
    base = np.ones((T, 25), dtype=float) / 25.0

    # Batch de 1
    return base.reshape(1, T, 25)


def _score_from_ls(model_name: str):
    metas = carregar_modelo_ls(model_name)
    print(">>> ENTROU 1 _score_from_ls")

    if not metas:
        return np.zeros(25, dtype=float)

    # usa ensemble simples de todos os modelos carregados
    acc = np.zeros(25, dtype=float)
    for m in metas:
        model = m["model"]
        T = m["expected_seq_len"]
        seq = prepare_seq(T)   # sua função já existente

        pred = model.predict(seq, verbose=0)[0]
        if pred.sum() > 0 and np.all(np.isfinite(pred)):
            acc += pred

    if acc.sum() == 0:
        return np.zeros(25, float)

    return acc / acc.sum()

def scores_neurais(nome):
    s = _score_from_ls(nome)
    if s.sum() == 0:
        return scores_estatisticos()
    return _normalize_probs(s)

def scores_ls14():
    return scores_neurais("LS14")

def scores_ls15():
    return scores_neurais("LS15")

def scores_ls16():
    # ensemble inteligente
    s15 = scores_neurais("LS15")
    s14 = scores_neurais("LS14")
    sE = scores_estatisticos()
    return _normalize_probs(0.6*s15 + 0.3*s14 + 0.1*sE)

def scores_ls16(model_name_for_ensemble="LS15", w_neural=0.6, w_stats=0.4):
    """
    LS16 híbrido com cache de LS15 e anti-reentrância.
    - Se já está computando LS16, cai para estatístico (evita recursão indireta).
    - Reusa _LS15_CACHE quando existir; não chama LS15 repetidas vezes.
    """
    global _IN_SCORES_LS16, _LS15_CACHE
    if _IN_SCORES_LS16:
        return scores_estatisticos()

    _IN_SCORES_LS16 = True
    try:
        # usa cache LS15 se disponível
        if _LS15_CACHE is not None and np.isfinite(_LS15_CACHE).all() and _LS15_CACHE.sum() > 0:
            s_n = _LS15_CACHE
        else:
            s_n = _score_from_ls(model_name_for_ensemble)
            if s_n is not None and np.isfinite(s_n).all() and s_n.sum() > 0:
                _LS15_CACHE = _normalize_probs(s_n)
            else:
                _LS15_CACHE = None

        s_e = scores_estatisticos()

        if _LS15_CACHE is None:
            return s_e

        s = w_neural * _LS15_CACHE + w_stats * s_e
        return _normalize_probs(s)
    except Exception as e:
        logging.error(f"[scores_ls16] Falhou: {e}")
        return scores_estatisticos()
    finally:
        _IN_SCORES_LS16 = False

# =========================
# GERAÇÃO ESTATÍSTICA
# =========================

def gerar_palpite_estatistico_paridade(limite=15):
    """Gera palpites equilibrando pares e ímpares."""
    pares = [n for n in range(1, 26) if n % 2 == 0]
    impares = [n for n in range(1, 26) if n % 2 == 1]
    random.shuffle(pares)
    random.shuffle(impares)
    qtd_pares = limite // 2
    qtd_impares = limite - qtd_pares
    dezenas = sorted(pares[:qtd_pares] + impares[:qtd_impares])
    return dezenas
# ================================================================
# BLOCO FINAL: SALVAR PALPITE COM TELEMETRIA (meta JSON)
# ================================================================
# ================================================================
# SALVAR PALPITE — versão final (coluna 'numeros' padrão oficial)
# ================================================================

def salvar_palpite(palpite, modelo, extras_meta=None):
    # ✅ Validação: LS16 nunca deve salvar palpite vazio
    if not palpite or len(palpite) < 15:
        _log_warn("⚠️ Palpite LS16 inválido — não será salvo no banco.")
        return None

    """
    Salva palpite no banco (PostgreSQL/Neon), compatível com campo data_norm.
    Retorna o ID do palpite inserido.
    Corrigido para evitar erro 'sql not defined' em exceções.
    """
    usuario = st.session_state.get("usuario", {}) if 'usuario' in st.session_state else {}
    id_usuario = usuario.get("id")

    if not id_usuario:
        _log_warn("Usuário não logado — não é possível salvar palpite.")
        return None

    # 🔹 Força nome correto de modelo híbrido (Platinum → LS16)
    if extras_meta and isinstance(extras_meta, dict):
        plano = str(extras_meta.get("plano", "")).lower()
        if plano == "platinum" and not modelo.upper().startswith("LS16"):
            _log_info(f"Forçando modelo LS16 (plano={plano})")
            modelo = "LS16"

    dezenas_txt = ",".join(f"{int(d):02d}" for d in palpite)
    cols = _existing_cols("palpites")
    if not cols:
        _log_warn("Tabela palpites não encontrada.")
        return None

    # --- [1] Coluna principal ---
    if "numeros" in cols:
        num_col = "numeros"
    elif "dezenas" in cols:
        num_col = "dezenas"
    elif "palpite" in cols:
        num_col = "palpite"
    elif "jogada" in cols:
        num_col = "jogada"
    else:
        _log_warn("Nenhuma coluna de dezenas encontrada.")
        return None

    ts_col = next((c for c in ("created_at", "criado_em", "data") if c in cols), None)
    defaults_map = {"status": "N", "ativo": True, "validado": False}
    extras = {c: defaults_map[c] for c in cols if c in defaults_map}

    # --- [2] Monta meta JSON ---
    meta_payload = {}
    if "meta" in cols:
        try:
            meta_payload = {
                "modelo": modelo,
                "usuario_id": id_usuario,
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "temperature": os.getenv("ENSEMBLE_TEMPERATURE", "1.0"),
                    "ensemble_weights": os.getenv("ENSEMBLE_WEIGHTS", "recent:0.5,mid:0.3,global:0.2"),
                    "use_gumbel": os.getenv("USE_GUMBEL", "0"),
                    "use_soft_constraints": os.getenv("USE_SOFT_CONSTRAINTS", "0"),
                },
                "palpite": palpite,
            }
            if extras_meta and isinstance(extras_meta, dict):
                meta_payload.update(extras_meta)
        except Exception as e:
            _log_warn(f"Erro ao montar meta JSON: {e}")

    # --- [3] SQL dinâmico ---
    db = Session()
    new_id = None
    sql = ""
    params = {}
    try:
        base_cols = ["id_usuario", "modelo", num_col]
        params = {"id_usuario": id_usuario, "modelo": modelo, num_col: dezenas_txt}

        if ts_col:
            base_cols.append(ts_col)
        for k, v in extras.items():
            if k not in base_cols:
                base_cols.append(k)
                params[k] = v

        if "meta" in cols:
            base_cols.append("meta")
            params["meta"] = json.dumps(meta_payload, ensure_ascii=False)

        # ✅ adiciona data_norm se existir
        if "data_norm" in cols:
            base_cols.append("data_norm")
            params["data_norm"] = date.today().isoformat()  # agora 'date' está importado

        placeholders = [("NOW()" if c == ts_col else f":{c}") for c in base_cols]
        sql = f"""
            INSERT INTO palpites ({', '.join(base_cols)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        result = db.execute(text(sql), params)
        new_id = result.scalar()
        db.commit()

        # 🔹 Atualiza contador diário do plano
        try:
            atualizar_contador_palpites(id_usuario)
        except Exception as e:
            _log_warn(f"Falha ao atualizar contador de palpites: {e}")

        _log_info(f"✅ Palpite salvo com sucesso! ID={new_id} (modelo={modelo}, usuario={id_usuario})")
        return new_id


    except Exception as e:
        db.rollback()
        safe_sql = sql or "<não definido>"
        safe_params = params or {}
        _log_warn(f"❌ Falha ao salvar palpite: {e}\nSQL: {safe_sql}\nparams: {safe_params}")
        return None
    finally:
        db.close()

# 🔹 Normalização dos nomes de modelo para exibição amigável

# =========================
# INTERFACE (UI)
# ================================================================
# 🔧 CONFIGURAÇÃO BASE + IMPORT LAZY (TensorFlow sob demanda)

_tf = None
_tf_load_model = None
_to_binary = None

def _lazy_imports():
    """
    Importa TensorFlow e utilitários pesados apenas quando necessário.
    Evita overhead e falhas em ambientes sem TF instalado (ex: Render lite).
    """
    global _tf, _tf_load_model, _to_binary
    if _tf is not None:
        return  # já importado

    try:
        import tensorflow as tf
        from tensorflow.keras.models import load_model as tf_load_model
        from modelo_llm_max.utils_ls_models import to_binary

        _tf = tf
        _tf_load_model = tf_load_model
        _to_binary = to_binary

        logging.info("✅ TensorFlow importado com sucesso via _lazy_imports().")

    except Exception as e:
        logging.error(f"⚠️ TensorFlow indisponível: {e}")
        _tf = None
        _tf_load_model = None
        _to_binary = None
        # Não levanta exceção — o app continua, apenas desativa recursos ML.
        #st.warning("TensorFlow não encontrado — modelos LS14/LS15 estarão desativados.")

# ================================================================
# 📁 CONFIGURAÇÃO DE DIRETÓRIOS E LOGS

try:
    _base_file = __file__
except NameError:
    _base_file = sys.argv[0] if sys.argv and sys.argv[0] else os.getcwd()

BASE_DIR = os.environ.get(
    "FAIXABET_BASE_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(_base_file))))

DEFAULT_MODELS_DIRS = [
    os.path.join(BASE_DIR, "modelo_llm_max", "models", "prod"),
    os.path.join(BASE_DIR, "modelo_llm_max", "models"),
    os.path.join(BASE_DIR, "models"),
    os.environ.get("FAIXABET_MODELS_DIR", "")]

# Usa o primeiro caminho existente como diretório de modelos
MODELS_DIR = next((p for p in DEFAULT_MODELS_DIRS if p and os.path.isdir(p)), DEFAULT_MODELS_DIRS[0])

# Modo debug controlado via variável de ambiente DEBUG_MODE=1
DEBUG_MODE = os.environ.get("DEBUG_MODE", "0") == "1"

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s")

logging.info(f"🧩 MODELS_DIR definido como: {MODELS_DIR}")
logging.info(f"🔧 Base dir: {BASE_DIR}")
logging.info(f"🪶 DEBUG_MODE: {DEBUG_MODE}")

def _log_warn(msg):
    if DEBUG_MODE:
        st.warning(msg)
    logging.warning(msg)

def _log_info(msg):
    if DEBUG_MODE:
        st.info(msg)
    logging.info(msg)

# TFSMLayer fallback (opcional - usado apenas como último recurso)
try:
    from keras.layers import TFSMLayer  # type: ignore
except Exception:
    try:
        from tensorflow.keras.layers import TFSMLayer  # type: ignore
    except Exception:
        TFSMLayer = None

# -------------------- REGRAS DE PLANOS --------------------
_PLAN_TO_GROUPS = {
    "free": ["recent"],
    "silver": ["recent", "mid"],
    "gold": ["recent", "mid", "global"],
    "plano pago x": ["recent", "mid", "global"]}

def _groups_allowed_for_plan(nome_plano):
    if not nome_plano:
        return _PLAN_TO_GROUPS["free"]
    key = str(nome_plano).strip().lower()
    return _PLAN_TO_GROUPS.get(key, _PLAN_TO_GROUPS["free"])

# -------------------- UTILITÁRIOS DE BUSCA DE MODELO --------------------

def _model_name_variants(model_name):
    """Cria variações para facilitar matching."""
    m = model_name.lower()
    variants = set([m])
    variants.add(m + "pp")
    variants.add(m.replace("ls", "ls_"))
    variants.add(m + "_pp")
    # sem underscore
    variants.add(m.replace("_", ""))
    return list(variants)

def _detect_group_and_expected_from_path(p):
    """Detecta grupo (recent/mid/global) a partir do path/filename e sugere expected_seq_len."""
    low = p.lower()
    if "recent" in low:
        return "recent", 500
    if "mid" in low:
        return "mid", 1000
    if "global" in low:
        return "global", 1550
    # fallback: tenta por prefixos
    bv = os.path.basename(low)
    if bv.startswith("recent_"):
        return "recent", 500
    if bv.startswith("mid_"):
        return "mid", 1000
    if bv.startswith("global_"):
        return "global", 1550
    return "unknown", None

def _dir_mtime(models_dir):
    """Retorna o maior mtime dentre os arquivos em models_dir (0 se inexistente)."""
    try:
        max_m = 0.0
        for root, dirs, files in os.walk(models_dir):
            for f in files:
                try:
                    p = os.path.join(root, f)
                    t = os.path.getmtime(p)
                    if t > max_m:
                        max_m = t
                except Exception:
                    continue
        return max_m
    except Exception:
        return 0.0

@st.cache_resource
def _cached_load_ensemble_models(model_name: str, models_dir: str, dir_mtime: float):
    """
    Carrega e retorna lista de metadados para os modelos do ensemble.
    `dir_mtime` é usado apenas para invalidar cache quando a pasta muda.
    """
    _lazy_imports()
    metas = []

    candidates = _model_paths_for(model_name, models_dir=models_dir)
    logging.info(f"[load_models] candidatos encontrados para '{model_name}': {len(candidates)} (base={models_dir})")

    for p in candidates:
        group, expected_from_path = _detect_group_and_expected_from_path(p)
        loaded = None
        try:
            try:
                loaded = _tf_load_model(p, compile=False)
            except Exception as e_load:
                logging.debug(f"Falha load_model {p}: {e_load}")
                if os.path.isdir(p) and os.path.isfile(os.path.join(p, "saved_model.pb")):
                    if TFSMLayer is not None and expected_from_path is not None:
                        try:
                            in_seq = _tf.keras.Input(shape=(expected_from_path, 25), name="seq")
                            tsl = TFSMLayer(p, call_endpoint="serving_default")
                            out = tsl(in_seq)
                            loaded = _tf.keras.Model(inputs=in_seq, outputs=out)
                        except Exception as e_tfs:
                            logging.warning(f"TFSMLayer falhou ({p}): {e_tfs}")
        except Exception as e_outer:
            logging.warning(f"Erro inesperado carregando {p}: {e_outer}")
            loaded = None

        if loaded is not None:
            expected_from_model = infer_expected_seq_from_loaded_model(loaded)
            expected = expected_from_model or expected_from_path
            input_shape = infer_model_input_shape(loaded)
            # n_inputs: número de entradas do modelo (1 ou >1)
            try:
                n_inputs = len(getattr(loaded, "inputs", []) or [1])
            except Exception:
                n_inputs = 1

            metas.append({
                "model": loaded,
                "path": p,
                "group": group,
                "expected_seq_len": expected,
                "n_inputs": n_inputs,
                "input_shape": input_shape
            })
            logging.info(f"✅ Modelo carregado: {p} (group={group}, expected={expected}, input_shape={input_shape})")

        else:
            logging.warning(f"⚠️ Modelo não carregado: {p}")

    if not metas:
        logging.warning(f"Nenhum modelo válido encontrado para '{model_name}' (dir={models_dir})")

    return metas

# ======================================================
# PATCH DE COMPATIBILIDADE - aceitar models_dir

def carregar_ensemble_models(model_name, models_dir=None):
    """
    Wrapper compatível com versões antigas de palpites.py.
    Agora aceita models_dir explicitamente (opcional).
    """
    import streamlit as st
    import os
    import logging
    from datetime import datetime

    # tenta localizar o diretório de modelos
    if models_dir is None:
        base_dir = os.environ.get("FAIXABET_BASE_DIR", os.getcwd())
        possiveis = [
            os.path.join(base_dir, "modelo_llm_max", "models", "prod"),
            os.path.join(base_dir, "modelo_llm_max", "models"),
            os.path.join(base_dir, "models"),
        ]
        for p in possiveis:
            if os.path.isdir(p):
                models_dir = p
                break
        else:
            models_dir = possiveis[0]

    # chama função original (sem parâmetro extra) se existir
    try:
        from tensorflow.keras.models import load_model as tf_load_model
    except Exception as e:
        logging.error(f"TensorFlow indisponível: {e}")
        return []

    # --- cache simples para invalidar se a pasta mudar ---
    def _dir_mtime(models_dir):
        import os
        try:
            return max(
                os.path.getmtime(os.path.join(root, f))
                for root, _, files in os.walk(models_dir)
                for f in files
            )
        except Exception:
            return 0.0

    dir_mtime = _dir_mtime(models_dir)
    logging.info(f"[carregar_ensemble_models] usando base {models_dir} (mtime={dir_mtime})")

    # tenta usar versão nova (com cache)
    try:
        from palpites import _cached_load_ensemble_models
        metas = _cached_load_ensemble_models(model_name, models_dir=models_dir, dir_mtime=dir_mtime)
        return metas
    except TypeError:
        logging.warning("Versão antiga detectada, usando fallback simples.")
        # fallback para versões antigas que não aceitavam models_dir
        try:
            from palpites import _cached_load_ensemble_models
            metas = _cached_load_ensemble_models(model_name, dir_mtime=dir_mtime)
            return metas
        except Exception as e:
            logging.error(f"Falha ao carregar modelos: {e}")
            st.error(f"Erro ao carregar modelos ({model_name}): {e}")
            return []

# -------------------- DEBUG / DIAGNÓSTICO --------------------

def listar_candidatos_modelo(model_name, models_dir=None):
    """Retorna e escreve candidatos (para debug)."""
    if models_dir is None:
        models_dir = MODELS_DIR
    cand = _model_paths_for(model_name, models_dir=models_dir)
    st.write(f"🔎 Candidatos encontrados para '{model_name}' (base={models_dir}):")
    if cand:
        for c in cand:
            group, expected = _detect_group_and_expected_from_path(c)
            st.write(" - ", c, f" (group={group}, expected={expected})")
    else:
        st.write(" (nenhum candidato encontrado)")
    return cand

def verificar_modelos(models_dir=None):
    """Chamada via UI para diagnosticar pasta e arquivos de modelos."""
    _lazy_imports()
    if models_dir is None:
        models_dir = MODELS_DIR
    st.write(f"🔍 Procurando modelos em: {models_dir}")
    for key in ("ls14", "ls15"):
        st.write(f"\n--- Candidatos para {key} ---")
        listar_candidatos_modelo(key, models_dir=models_dir)

    st.write('\n--- Conteúdo raiz da pasta models/ (até 200 itens) ---')
    try:
        arquivos = os.listdir(models_dir)
        st.write(arquivos[:200])
    except Exception as e:
        st.write(f"Erro ao listar pasta de modelos: {e}")

# -------------------- UTILITÁRIOS DE PREPARO / PREDIÇÃO --------------------

def _ensure_window_list(ultimos_full, expected):
    cur = len(ultimos_full)
    if expected is None or cur >= expected:
        return ultimos_full[-expected:] if expected else ultimos_full
    if cur == 0:
        return [[0]*15 for _ in range(expected)]
    pad_count = expected - cur
    pad = [ultimos_full[0]] * pad_count
    return pad + ultimos_full

def infer_model_input_shape(loaded):
    """
    Retorna tupla (time_steps, features) extraída de loaded.inputs quando possível.
    Se não puder inferir, retorna None.
    """
    try:
        ins = getattr(loaded, 'inputs', None)
        if not ins:
            return None
        # normalize to list
        if not isinstance(ins, (list, tuple)):
            ins = [ins]
        for inp in ins:
            shape = getattr(inp, 'shape', None)
            if not shape:
                continue
            dims = []
            for d in shape:
                try:
                    dims.append(int(d))
                except Exception:
                    dims.append(None)
            # queremos pelo menos (batch, time_steps, features)
            if len(dims) >= 3:
                time_dim = dims[-2]
                feat_dim = dims[-1]
                return (time_dim, feat_dim)
        return None
    except Exception:
        return None

def infer_expected_seq_from_loaded_model(loaded):
    try:
        ins = getattr(loaded, 'inputs', None)
        if not ins:
            return None
        for inp in ins:
            try:
                shape = getattr(inp, 'shape', None)
                if shape is None:
                    continue
                dims = []
                for d in shape:
                    try:
                        dims.append(int(d))
                    except Exception:
                        dims.append(None)
                if len(dims) >= 3 and dims[-1] == 25:
                    return dims[-2]
            except Exception:
                continue
    except Exception:
        pass
    return None

def _prepare_inputs_for_model_meta(meta, ultimos_full):
    """
    Prepara X com one-hot de 25 features: (1, expected_seq_len, 25)
    """
    import numpy as np

    def _one_hot_25(jogo):
        v = np.zeros(25, dtype=np.float32)
        for d in jogo:
            try:
                di = int(d)
                if 1 <= di <= 25:
                    v[di - 1] = 1.0
            except Exception:
                continue
        return v

    expected_seq_len = meta.get("expected_seq_len") or 50

    seq = []
    for jogo in ultimos_full:
        try:
            if "_to_binary" in globals() and _to_binary is not None:
                seq.append(np.array(_to_binary(jogo), dtype=np.float32))
            else:
                seq.append(_one_hot_25(jogo))
        except Exception:
            seq.append(_one_hot_25(jogo))

    seq = np.asarray(seq, dtype=np.float32)  # (n, 25)

    if seq.shape[0] > expected_seq_len:
        seq = seq[-expected_seq_len:]
    elif seq.shape[0] < expected_seq_len:
        pad = np.zeros((expected_seq_len - seq.shape[0], 25), dtype=np.float32)
        seq = np.vstack([pad, seq])

    return np.expand_dims(seq, axis=0)  # (1, T, 25)

def _ultimos_sorteios_para_modelo(limit=50):
    try:
        db = Session()
        rows = db.execute(text("""
            SELECT n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15
            FROM resultados_oficiais
            ORDER BY data DESC
            LIMIT :lim
        """), {"lim": limit}).fetchall()
        db.close()
        if not rows:
            return []
        jogos = [[int(x) for x in row if x is not None] for row in rows]
        return list(reversed([sorted(j) for j in jogos]))  # cronológico
    except Exception as e:
        logging.warning(f"[ultimos_sorteios_para_modelo] Falhou: {e}")
        return []

# ================================================================
# BLOCO NOVO: CALIBRAÇÃO & PESOS (SOFTMAX + ENSEMBLE)
# ================================================================

def _softmax(x, temperature=1.0):
    """Aplica softmax com temperatura para calibrar probabilidades."""
    x = np.array(x, dtype=np.float32)
    x = x / float(temperature)
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

def _parse_weights_from_env(default="recent:0.5,mid:0.3,global:0.2"):
    """
    Lê os pesos de ensemble a partir da variável de ambiente ENSEMBLE_WEIGHTS.
    Exemplo: ENSEMBLE_WEIGHTS="recent:0.6,mid:0.3,global:0.1"
    """
    raw = os.getenv("ENSEMBLE_WEIGHTS", default)
    parts = [p.strip() for p in raw.split(",") if ":" in p]
    weights = {}
    for p in parts:
        k, v = p.split(":")
        try:
            weights[k.strip()] = float(v)
        except ValueError:
            continue

    total = sum(weights.values())
    if total <= 0:
        return {"recent": 0.5, "mid": 0.3, "global": 0.2}

    return {k: v / total for k, v in weights.items()}

def combinar_modelos_com_pesos(predicoes_por_grupo, temperature=1.0):
    """
    Recebe um dicionário {grupo: vetor_predição(25,)} e aplica:
    - Softmax (calibração)
    - Média ponderada conforme ENSEMBLE_WEIGHTS
    Retorna vetor final (25,)
    """
    weights = _parse_weights_from_env()
    grupos_validos = [g for g in predicoes_por_grupo.keys() if g in weights]
    if not grupos_validos:
        grupos_validos = list(predicoes_por_grupo.keys())
        weights = {g: 1 / len(grupos_validos) for g in grupos_validos}

    soft_preds = {}
    for g in grupos_validos:
        soft_preds[g] = _softmax(predicoes_por_grupo[g], temperature=temperature)

    # Média ponderada
    final = np.zeros_like(list(soft_preds.values())[0])
    for g in grupos_validos:
        final += weights[g] * soft_preds[g]

    # Normaliza novamente
    final /= final.sum()

    _log_info(f"[Ensemble] Grupos={grupos_validos}, Pesos={weights}, Temp={temperature:.2f}")
    return final

def ensemble_predict(models_list, X_inputs):
    if not models_list:
        raise ValueError("Nenhum modelo carregado para ensemble.")
    preds = []
    for entry in models_list:
        model_obj = entry
        if isinstance(entry, dict):
            model_obj = entry.get("model")
        if model_obj is None:
            _log_warn(f"Ignorando entrada inválida no ensemble: {entry}")
            continue
        try:
            p = model_obj.predict(X_inputs, verbose=0)
            if isinstance(p, (list, tuple)):
                p = p[0]
            p = np.asarray(p, dtype=np.float32)
            if p.ndim == 1:
                p = p.reshape(1, -1)
            preds.append(p)
        except Exception as e:
            name = getattr(model_obj, "name", getattr(model_obj, "__class__", None))
            _log_warn(f"Predição falhou para um dos modelos do ensemble ({name}): {e}")

    if not preds:
        raise ValueError("Nenhuma predição válida obtida dos modelos.")

    # --- Novo ensemble calibrado ---
    temperature = float(os.getenv("ENSEMBLE_TEMPERATURE", "1.0"))

    # Determina grupo de cada modelo, se possível
    preds_por_grupo = {}
    for i, entry in enumerate(models_list):
        group = "recent"
        if isinstance(entry, dict):
            group = entry.get("group", f"m{i}")
        preds_por_grupo[group] = preds[i][0] if preds[i].ndim > 1 else preds[i]

    mean_pred = combinar_modelos_com_pesos(preds_por_grupo, temperature=temperature)
    return mean_pred

# -------------------- FEATURES / GERADORES SIMPLES --------------------

def montar_entrada_binaria(ultimos_concursos):
    arr = np.array([[1.0 if (i+1) in jogo else 0.0 for i in range(25)] for jogo in ultimos_concursos], dtype=np.float32)
    return arr

def apply_temperature(p, T=1.0):
    p = np.clip(p, 1e-12, 1.0)
    logits = np.log(p)
    scaled = np.exp(logits / float(T))
    return scaled / scaled.sum()

# ================================================================
# Utilitários para diversidade (Gumbel-top-k)

def _sample_gumbel(shape, eps=1e-20):
    """Ruído Gumbel i.i.d para amostragem Top-K."""
    U = np.random.uniform(0.0, 1.0, shape)
    return -np.log(-np.log(U + eps) + eps)

def _gumbel_top_k_sampling(probs, k=15, temperature=1.0):
    """
    Seleciona Top-K aplicando ruído Gumbel nos logits.
    - probs: vetor (25,) normalizado
    - k: número de dezenas
    - temperature: >1 aumenta diversidade; <1 deixa mais “focado”
    """
    logits = np.log(np.clip(probs, 1e-12, 1.0))
    g = _sample_gumbel(logits.shape)
    noisy = (logits + g) / float(temperature)
    topk = np.argsort(-noisy)[:k]
    return np.sort(topk + 1).tolist()

def gerar_palpite_from_probs(
    probs,
    limite=15,
    reinforce_threshold=0.06,
    boost_factor=2.0,
    temperature=1.0,
    deterministic=False):
    """
    Gera palpites a partir de probabilidades.
    Agora com diversidade opcional (Gumbel-top-k) controlada por env USE_GUMBEL.
    Mantém compatibilidade total com chamadas existentes.
    """
    use_gumbel = os.getenv("USE_GUMBEL", "0") == "1"

    # 1) Aplica temperatura (mesma lógica existente)
    p = apply_temperature(probs, temperature)

    # 2) Reforço leve em probabilidades altas (mesma lógica existente)
    mask = p > reinforce_threshold
    if mask.any():
        p[mask] = p[mask] * boost_factor
        p = p / p.sum()

    # 3) Caminho determinístico (inalterado)
    if deterministic:
        idxs = np.argsort(-p)[:limite]
        chosen = np.sort(idxs + 1).tolist()
        return chosen

    # 4) Caminho estocástico:
    #    - se USE_GUMBEL=1 => usa Gumbel-top-k (mais diversidade)
    #    - caso contrário => amostragem atual por np.random.choice (comportamento igual ao antigo)
    if use_gumbel:
        return _gumbel_top_k_sampling(p, k=limite, temperature=temperature)
    else:
        chosen_idxs = np.random.choice(np.arange(25), size=limite, replace=False, p=p)
        return np.sort(chosen_idxs + 1).tolist()

# ================================================================
# BLOCO NOVO: DIVERSIDADE — GUMBEL-TOP-K SAMPLER (OPCIONAL)

def _sample_gumbel(shape, eps=1e-20):
    """Gera ruído Gumbel i.i.d para amostragem Top-K."""
    U = np.random.uniform(0, 1, shape)
    return -np.log(-np.log(U + eps) + eps)

def gumbel_top_k_sampling(probs, k=15, temperature=1.0):
    """
    Retorna índices Top-K com ruído Gumbel (para mais diversidade).
    - probs: vetor (25,) normalizado
    - k: número de dezenas
    """
    logits = np.log(np.clip(probs, 1e-12, 1.0))
    gumbels = _sample_gumbel(logits.shape)
    noisy_logits = (logits + gumbels) / float(temperature)
    topk = np.argsort(-noisy_logits)[:k]
    return np.sort(topk + 1).tolist()

def gerar_palpite_from_probs_diverso(probs, limite=15, reinforce_threshold=0.06,
                                     boost_factor=2.0, temperature=1.0,
                                     deterministic=False):
    """
    Wrapper compatível com gerar_palpite_from_probs, adicionando diversidade.
    Ativado se USE_GUMBEL=1 no ambiente.
    """
    use_gumbel = os.getenv("USE_GUMBEL", "0") == "1"

    # Reforço leve, igual ao método original
    p = np.array(probs, dtype=np.float32)
    p = np.clip(p, 1e-12, 1.0)
    mask = p > reinforce_threshold
    if mask.any():
        p[mask] *= boost_factor
        p /= p.sum()

    if deterministic:
        idxs = np.argsort(-p)[:limite]
        return np.sort(idxs + 1).tolist()

    if use_gumbel:
        return gumbel_top_k_sampling(p, k=limite, temperature=temperature)
    else:
        chosen_idxs = np.random.choice(np.arange(25), size=limite, replace=False, p=p)
        return np.sort(chosen_idxs + 1).tolist()

# ================================================================
# BLOCO NOVO: CONSTRAINTS SUAVES (paridade, consecutivos, distribuição)

def _score_palpite_regras(palpite):
    """
    Calcula um score baseado em regras da Lotofácil:
    - Paridade: ideal ~7 ou 8 pares
    - Consecutivos: penaliza mais de 3 seguidos
    - Distribuição 5x5: idealmente equilibrado entre 5 linhas e 5 colunas
    Retorna score ∈ [0,1], quanto maior melhor.
    """
    palpite = np.array(sorted(palpite))
    pares = np.sum(palpite % 2 == 0)
    impares = len(palpite) - pares

    # ---- regra 1: paridade ----
    par_score = 1.0 - abs(pares - 7.5) / 7.5  # máximo quando 7 ou 8 pares

    # ---- regra 2: consecutivos ----
    diffs = np.diff(palpite)
    consecutivos = np.sum(diffs == 1)
    consecutivo_score = 1.0 - min(consecutivos, 5) / 5.0  # penaliza mais de 3-4 consecutivos

    # ---- regra 3: distribuição 5x5 (linhas e colunas de 1 a 25) ----
    matriz = np.arange(1, 26).reshape(5, 5)
    lin_counts = [np.sum(np.isin(row, palpite)) for row in matriz]
    col_counts = [np.sum(np.isin(matriz[:, c], palpite)) for c in range(5)]
    dist_score = 1.0 - (
        (np.std(lin_counts) + np.std(col_counts)) / (2 * len(palpite))
    )

    # Score final (média ponderada)
    final_score = 0.4 * par_score + 0.3 * consecutivo_score + 0.3 * dist_score
    return max(0.0, min(1.0, final_score))

def ajustar_palpite_por_regras(palpite, max_tentativas=50):
    """
    Tenta melhorar o palpite com pequenas trocas até atingir score aceitável.
    Mantém a mesma quantidade de dezenas.
    """
    alvo_minimo = 0.75  # limiar de qualidade
    limite = len(palpite)
    melhor = sorted(palpite)
    melhor_score = _score_palpite_regras(melhor)

    for _ in range(max_tentativas):
        candidato = melhor.copy()
        trocas = np.random.randint(1, 4)  # até 3 trocas aleatórias
        for _ in range(trocas):
            rem = np.random.choice(candidato)
            add = np.random.choice([x for x in range(1, 26) if x not in candidato])
            candidato.remove(rem)
            candidato.append(add)
        candidato = sorted(candidato)
        sc = _score_palpite_regras(candidato)
        if sc > melhor_score:
            melhor, melhor_score = candidato, sc
        if melhor_score >= alvo_minimo:
            break

    return melhor

def aplicar_constraints_suaves(palpite):
    """
    Wrapper para aplicar constraints apenas se USE_SOFT_CONSTRAINTS=1
    """
    use_constraints = os.getenv("USE_SOFT_CONSTRAINTS", "0") == "1"
    if not use_constraints:
        return palpite
    return ajustar_palpite_por_regras(palpite)

# ============ Bloco filha ===========================================

def _calc_features_from_window(ultimos):
    seq_bin = np.array([to_binary(j) for j in ultimos], dtype=np.float32)
    window = len(ultimos)
    freq_vec = seq_bin.sum(axis=0) / float(window)
    atraso_vec = np.zeros(25, dtype=np.float32)
    for d in range(1, 26):
        atraso = 0
        for jogo in reversed(ultimos):
            atraso += 1
            if d in jogo:
                break
        atraso_vec[d - 1] = min(atraso, window) / float(window)
    last = ultimos[-1]
    soma = sum(last) / (25.0 * 15.0)
    pares = sum(1 for x in last if x % 2 == 0) / 15.0
    global_vec = np.array([soma, pares], dtype=np.float32)
    return seq_bin, freq_vec.astype(np.float32), atraso_vec.astype(np.float32), global_vec

# -------------------- DB / PLANOS (mantive a lógica original) --------------------

def obter_limite_dezenas_por_plano(tipo_plano):
    db = Session()
    try:
        resultado = db.execute(text("""
            SELECT palpites_max FROM planos WHERE nome = :nome
        """), {"nome": tipo_plano}).fetchone()
        return resultado[0] if resultado else 15
    except Exception as e:
        st.error(f"Erro ao obter limite de dezenas: {e}")
        return 15
    finally:
        db.close()

def atualizar_contador_palpites(id_usuario: int):
    """
    Incrementa o contador de palpites do dia em client_plans.palpites_dia_usado
    para o plano ativo do usuário.

    Obs:
    - Usa a coluna correta: palpites_dia_usado (não palpites_usados_dia)
    - Não bloqueia o fluxo em caso de erro (apenas loga warning)
    """
    db = Session()
    try:
        db.execute(text("""
            UPDATE client_plans
            SET palpites_dia_usado = COALESCE(palpites_dia_usado, 0) + 1
            WHERE id_client = :id
              AND ativo = TRUE
              AND (
                    data_expira_plan IS NULL
                    OR DATE(data_expira_plan) >= CURRENT_DATE
                  )
        """), {"id": id_usuario})
        db.commit()
    except Exception as e:
        logging.warning(f"Erro ao atualizar contador de palpites (modo teste): {e}")
        # em modo teste não vamos estourar erro na tela
    finally:
        db.close()

def gerar_palpite_pares_impares(limite=15):
    num_pares = limite // 2
    num_impares = limite - num_pares
    pares = random.sample(range(2, 26, 2), num_pares)
    impares = random.sample(range(1, 26, 2), num_impares)
    return sorted(pares + impares)

def gerar_palpite_estatistico(limite=15):
    db = Session()
    try:
        resultados = db.execute(text("""
            SELECT n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15
            FROM resultados_oficiais
        """))
        resultados = resultados.fetchall()
        if not resultados:
            return gerar_palpite_aleatorio(limite)

        todos_numeros = [num for row in resultados for num in row]
        frequencia = {num: todos_numeros.count(num) for num in range(1, 26)}
        numeros_ordenados = sorted(frequencia.items(), key=lambda x: x[1], reverse=True)

        top_10 = [num for num, _ in numeros_ordenados[:10]]
        outros = [num for num, _ in numeros_ordenados[10:20]]
        baixa_freq = [num for num, _ in numeros_ordenados[20:]]

        palpite = (
            random.sample(top_10, min(7, len(top_10))) +
            random.sample(outros, min(5, len(outros))) +
            random.sample(baixa_freq, min(3, len(baixa_freq)))
        )
        return sorted(palpite)[:limite]

    except Exception:
        return gerar_palpite_aleatorio(limite)
    finally:
        db.close()

# -------------------- GERADORES ML (LS16 / LS15 / LS14) --------------------
def gerar_palpites_por_modelo(modelo: str, qtd: int = 3, k: int = 15):
    """
    Gera palpites usando o pipeline atual.
    Modelos permitidos:
      LS14, LS15, LS16, ESTAT, ALEATORIO
    """
    modelo = (modelo or "").upper()

    # --- 1) Escolha correta do vetor de scores neural ---
    if modelo == "LS14":
        s = scores_neurais("LS14")

    elif modelo == "LS15":
        s = scores_neurais("LS15")

    elif modelo == "LS16":
        # ensemble inteligente
        s = scores_ls16()

    elif modelo in ("ESTAT", "ESTATISTICO"):
        s = scores_estatisticos()

    elif modelo in ("ALEATORIO", "RANDOM"):
        # gera palpites totalmente aleatórios
        out = []
        for _ in range(qtd):
            p = sorted(random.sample(range(1, 26), k))
            out.append(p)
        return out

    else:
        logging.warning(f"[gerar_palpites_por_modelo] Modelo desconhecido '{modelo}' → estatístico.")
        s = scores_estatisticos()

    # --- 2) Geração dos palpites usando o vetor s ---
    palpites = []
    tries = 0

    while len(palpites) < qtd and tries < 8000:
        p = _amostrar_dezenas(s, k=k)
        if p:
            palpites.append(p)
        tries += 1

    return palpites

def _model_paths_for(model_name: str, models_dir: str = None):
    """
    Retorna lista de caminhos de modelos (regular, mid, global) para LS14/LS15.
    Funciona tanto em DEV quanto em PROD.
    """
    if models_dir and os.path.isdir(models_dir):
        base_dir = models_dir
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "modelo_llm_max", "models", "prod"),
            os.path.join(base_dir, "modelo_llm_max", "models"),
            os.path.join(base_dir, "models", "prod"),
            os.path.join(base_dir, "models")
        ]
        base_dir = next((p for p in candidates if os.path.isdir(p)), None)

    if not base_dir:
        logging.warning(f"[_model_paths_for] models_dir inválido: {models_dir}")
        return []

    tipos = ['recent', 'mid', 'global', 'regular']  # recent primeiro
    encontrados = []

    for tipo in tipos:
        padrao = f"{tipo}_{model_name}pp_final.keras"
        # busca direta
        caminho = os.path.join(base_dir, padrao)
        if os.path.exists(caminho):
            encontrados.append(caminho)
        else:
            # busca recursiva
            for root, _, files in os.walk(base_dir):
                for f in files:
                    if f.lower() == padrao.lower():
                        encontrados.append(os.path.join(root, f))
                        break
                if encontrados and encontrados[-1].lower().endswith(padrao.lower()):
                    break

    logging.info(f"[_model_paths_for] Modelos encontrados para {model_name}: {encontrados}")
    return encontrados

def _safe_dir_mtime(path):
    try:
        max_m = 0.0
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    t = os.path.getmtime(os.path.join(root, f))
                    if t > max_m:
                        max_m = t
                except Exception:
                    pass
        return max_m
    except Exception:
        return 0.0

# =============================================================
#  MODELO: CARREGAMENTO CACHEADO DOS LS14/LS15/LS16/LS17
# =============================================================
_MODEL_CACHE = {}

def carregar_modelo_ls(model_name: str, models_dir=None):
    """
    Carrega modelos LS14, LS15, LS16 ou LS17 com cache real.
    Evita recarregar .keras toda vez e deixa o pipeline 10x mais rápido.
    """

    _lazy_imports()

    # TF indisponível → ignora modelos neurais
    if _tf_load_model is None:
        if not globals().get("_TF_WARN_EMITTED", False):
            logging.warning("[carregar_modelo_ls] TensorFlow indisponível — usando fallback estatístico.")
            globals()["_TF_WARN_EMITTED"] = True
        return []

    model_name = (model_name or "").upper()

    # Usa cache
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    base = models_dir or MODELS_DIR
    caminhos = _model_paths_for(model_name, models_dir=base)

    metas = []

    for path in caminhos:
        try:
            model_obj = _tf_load_model(path, compile=False)

            # Captura a expected_seq_len automaticamente
            expected_seq_len = None
            try:
                shp = model_obj.inputs[0].shape  # (None, T, 25)
                if len(shp) >= 3:
                    expected_seq_len = int(shp[-2])
            except Exception:
                expected_seq_len = 50

            metas.append({
                "model": model_obj,
                "path": path,
                "expected_seq_len": expected_seq_len,
            })

            logging.info(f"[carregar_modelo_ls] Modelo carregado: {path}")

        except Exception as e:
            logging.warning(f"[carregar_modelo_ls] Falha ao carregar {path}: {e}")

    # INSERE NO CACHE
    _MODEL_CACHE[model_name] = metas
    return metas

def _load_and_filter_metas_for_plan(model_name, nome_plano, models_dir=None):
    metas = carregar_ensemble_models(model_name, models_dir=models_dir)
    if not metas:
        return []
    allowed_groups = _groups_allowed_for_plan(nome_plano)
    filtered = [m for m in metas if m.get("group") in allowed_groups or m.get("group") == "unknown"]
    return filtered

def gerar_palpite_ls16_platinum(k=15):
    """
    Tenta primeiro o ensemble inteligente (modelo_llm_max/ensemble.py).
    Se não der, usa o caminho atual baseado em scores_ls16 (LS15 + estatístico).
    Retorna uma lista ordenada de dezenas (int).
    """
    # 1) Tenta o ensemble.py novo
    if _fxb_ls16_ensemble is not None:
        try:
            dezenas = _fxb_ls16_ensemble()  # retorna ['01','07',...]
            if dezenas and isinstance(dezenas, (list, tuple)):
                dz_int = sorted({int(str(d).strip()) for d in dezenas})[:k]
                dz_int = [x for x in dz_int if 1 <= x <= 25]
                if len(dz_int) >= min(15, k):
                    return sorted(dz_int[:k])
        except Exception as e:
            logging.warning(f"[LS16 ensemble] fallback por erro: {e}")

    # 2) Fallback: usar seu pipeline atual (scores_ls16 -> amostragem)
    s = scores_ls16(model_name_for_ensemble="LS15", w_neural=0.6, w_stats=0.4)
    p = _amostrar_dezenas(s, k=k)
    return sorted(p or gerar_palpite_estatistico(limite=k))

def historico_palpites():
    import datetime as dt

    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.warning("Você precisa estar logado para acessar o histórico.")
        return

    st.markdown("##  Histórico de Palpites / Bets")

    # ==============================
    # 🔹 Filtros Superiores
    # ==============================
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        opcoes_modelo = ["Todos", "Aleatório", "Estatístico", "Ímpares-Pares", "LS15", "LS14","LS16"]
        filtro_modelo = st.selectbox(" Modelo de Palpite:", opcoes_modelo)

    with col2:
        filtro_status = st.selectbox(
            "📊 Status:",
            ["Todos", "✅ Válido", "⏳ Não usado"]
        )

    with col3:
        data_inicio = st.date_input(" Início:", value=dt.date.today() - dt.timedelta(days=30))
        data_fim = st.date_input(" Fim:", value=dt.date.today())

    # ==============================
    # 🔹 Consulta SQL dinâmica
    # ==============================
    db = Session()
    try:
        query = """
            SELECT id, numeros, modelo, data, status 
            FROM palpites 
            WHERE id_usuario = :id
              AND DATE(data) BETWEEN :data_inicio AND :data_fim
        """
        params = {
            "id": st.session_state.usuario["id"],
            "data_inicio": data_inicio,
            "data_fim": data_fim
        }

        if filtro_modelo != "Todos":
            query += " AND modelo = :modelo"
            params["modelo"] = filtro_modelo

        if filtro_status == "✅ Válido":
            query += " AND status = 'S'"
        elif filtro_status == "⏳ Não usado":
            query += " AND (status IS NULL OR status <> 'S')"

        query += " ORDER BY data DESC"
        result = db.execute(text(query), params)
        palpites = result.fetchall()

        # ==============================
        # 🔹 Contadores Dinâmicos
        # ==============================
        total = len(palpites)
        validos = sum(1 for p in palpites if p.status == "S")
        pendentes = total - validos

        st.markdown("""
            <div style='display:flex; gap:20px; margin-top:10px; margin-bottom:12px;'>
                <div style='flex:1; background:#f8f9fa; padding:10px; border-radius:8px; border:1px solid #ccc; text-align:center;'>
                    <div style='font-size:13px; color:#444;'>Total</div>
                    <div style='font-size:18px; font-weight:bold; color:#007bff;'>{total}</div>
                </div>
                <div style='flex:1; background:#f8fff8; padding:10px; border-radius:8px; border:1px solid #c7e6ca; text-align:center;'>
                    <div style='font-size:13px; color:#444;'>✅ Válidos</div>
                    <div style='font-size:18px; font-weight:bold; color:#28a745;'>{validos}</div>
                </div>
                <div style='flex:1; background:#fffaf8; padding:10px; border-radius:8px; border:1px solid #f2c2b0; text-align:center;'>
                    <div style='font-size:13px; color:#444;'>⏳ Não usados</div>
                    <div style='font-size:18px; font-weight:bold; color:#e67e22;'>{pendentes}</div>
                </div>
            </div>
        """.format(total=total, validos=validos, pendentes=pendentes), unsafe_allow_html=True)

        # ==============================
        # 🔹 Exibição dos resultados
        # ==============================
        if palpites:
            for i in range(0, len(palpites), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(palpites):
                        pid, numeros, modelo, data, status = palpites[i + j]
                        eh_valido = status == "S"
                        status_str = "✅ Válido" if eh_valido else "⏳ Não usado"
                        cor = "#28a745" if eh_valido else "#999"

                        with cols[j]:
                            st.markdown(f"""
                                <div style='background:#fff; padding:10px 14px; border-radius:10px; 
                                            border:1px solid #ccc; margin-bottom:12px; min-height:90px;
                                            box-shadow:0 1px 3px rgba(0,0,0,0.08)'>
                                    <div style='font-size:13px; color:#444; font-weight:bold;'>
                                        Palpite #{pid} | <span style='color:#007bff'>{modelo}</span>
                                    </div>
                                    <div style='font-size:12px; color:{cor}; margin-bottom:4px;'>{status_str}</div>
                                    <div style='font-size:11px; color:gray;'>{data.strftime('%d/%m/%Y %H:%M')}</div>
                                    <div style='font-family:monospace; font-size:14px; margin-top:6px;'>{numeros}</div>
                                    <button onclick="navigator.clipboard.writeText('{numeros}')" 
                                            style="margin-top:6px; padding:3px 8px; font-size:11px; border:none; 
                                                   background-color:#1f77b4; color:white; border-radius:6px; cursor:pointer;">
                                        Copiar
                                    </button>
                                </div>
                            """, unsafe_allow_html=True)
        else:
            st.info("Nenhum palpite encontrado com os filtros selecionados.")
    except Exception as e:
        st.error(f"Erro inesperado em histórico de palpites: {e}")
    finally:
        db.close()

# 🔹 Helper para compatibilidade de rerun
def _safe_rerun():
    """Rerun compatível com versões novas e antigas do Streamlit."""
    try:
        st.rerun()  # Streamlit >= 1.27
    except AttributeError:
        st.experimental_rerun()  # compatibilidade com versões antigas

def _normalize_probs(vec, eps=1e-12):
    """
    Normaliza vetor de pesos garantindo:
      - sem NaN/Inf
      - soma > 0
    Se falhar, retorna uniforme (25) para Lotofácil.
    """
    v = np.asarray(vec, dtype=float)
    if not np.all(np.isfinite(v)):
        v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    s = v.sum()
    if s <= 0:
        # uniforme de 25 posições (Lotofácil)
        return np.ones(25, dtype=float) / 25.0
    v = v / s
    # sanidade final
    if not np.all(np.isfinite(v)):
        return np.ones(25, dtype=float) / 25.0
    return v

# 🔹 Função para atualizar o status do palpite no banco
def _validar_no_banco(pid: int):
    db = Session()
    try:
        db.execute(text("""
            UPDATE palpites SET status = 'S' WHERE id = :pid
        """), {"pid": pid})
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao validar: {e}")
    finally:
        db.close()

# 🔹 Função principal
def validar_palpite():
    """Exibe os palpites em cards com botão de validação individual."""
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.warning("Você precisa estar logado para validar seus Palpites.")
        return

    st.markdown("## Validar Palpites/ Bets")

    db = Session()
    try:
        rows = db.execute(text("""
            SELECT id, numeros, modelo, data, status
            FROM palpites
            WHERE id_usuario = :uid
            ORDER BY data DESC
            LIMIT 50
        """), {"uid": st.session_state.usuario["id"]}).fetchall()
    except Exception as e:
        st.error(f"Erro ao buscar Palpites: {e}")
        return
    finally:
        db.close()

    if not rows:
        st.info("Você ainda não gerou nenhum Palpite.")
        return

    # --- CSS grid responsiva ---
    st.markdown("""
    <style>
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 14px;
        max-height: 550px;
        overflow-y: auto;
        padding: 8px;
    }
    .palpite-card {
        background: #f9fff9;
        border: 2px solid #009900;
        border-radius: 12px;
        padding: 10px 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,.08);
    }
    .palpite-header {
        font-weight: bold;
        color: #009900;
        margin-bottom: 4px;
    }
    .palpite-data {
        font-size: 13px;
        color: #555;
        margin-bottom: 6px;
    }
    .palpite-dezenas {
        font-family: monospace;
        font-size: 15px;
        color: #000;
        word-spacing: 5px;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Renderização em grid ---
    st.markdown('<div class="grid">', unsafe_allow_html=True)

    for pid, numeros, modelo, data, status in rows:
        dezenas = " ".join(f"{int(d):02d}" for d in str(numeros).replace(",", " ").split() if d.isdigit())

        # renderiza o card
        st.markdown(
            f"""
            <div class="palpite-card">
                <div class="palpite-header">#{pid} — {modelo}</div>
                <div class="palpite-data">{data.strftime('%d/%m/%Y %H:%M')}</div>
                <div class="palpite-dezenas">{dezenas}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # renderiza botão abaixo do card
        if status != "S":
            if st.button(f"✅ Validar #{pid}", key=f"val_{pid}"):
                _validar_no_banco(pid)
                st.success(f"Palpite #{pid} validado com sucesso! ")
                _safe_rerun()
        else:
            st.caption("✅ Já validado")

    st.markdown('</div>', unsafe_allow_html=True)

# ================== [PLAN RULES] ==================
# =============================================================
#   DEFINIÇÃO OFICIAL DOS MODELOS POR PLANO
# =============================================================

def modelo_por_plano(nome_plano: str) -> str:
    nome = (nome_plano or "").strip().lower()

    if nome == "free":
        return "ESTAT"

    elif nome == "silver":
        return "LS14"

    elif nome == "gold":
        return "LS15"

    elif nome == "platinum":
        return "LS16"   # Seu modelo oficial Platinum

    elif nome in ("rnd", "r&d", "pesquisa"):
        return "LS17"

    return "ESTAT"

# ================== [PLAN RULES - LEGACY DESATIVADO] ==================
# Este bloco foi mantido apenas como referência histórica.
# O código em produção usa PLAN_RULES + _modelo_e_k_por_plano +
# _gerar_para_plano_legacy + gerar_para_plano (dispatcher novo).

def modelo_por_plano_legacy(nome_plano: str) -> str:
    """
    VERSÃO LEGACY — NÃO USAR MAIS NA UI NEM NA GERAÇÃO.
    Mantida só como referência caso precise comparar comportamento antigo.
    """
    nome = (nome_plano or "").strip().lower()

    if nome == "free":
        return "ESTAT"
    elif nome == "silver":
        return "LS14"
    elif nome == "gold":
        return "LS15"
    elif nome == "platinum":
        return "LS16"   # modelo oficial Platinum antigo
    elif nome in ("rnd", "r&d", "pesquisa"):
        return "LS17"

    return "ESTAT"

def gerar_para_plano_legacy_v0(nome_plano: str, qtd: int = 3, k_escolhido: int | None = None):
    """
    VERSÃO LEGACY — NÃO USAR MAIS.
    Substituída pelo dispatcher gerar_para_plano() lá em cima.
    """
    from warnings import warn
    warn("[LEGACY] gerar_para_plano_legacy_v0 chamado — bloco antigo, não deveria ser usado.", RuntimeWarning)

    # Mantido só para referência: este era o fluxo antigo.
    modelo = modelo_por_plano_legacy(nome_plano)
    k = 15 if k_escolhido is None else int(k_escolhido)
    palpites = gerar_palpites_por_modelo(modelo, qtd=qtd, k=k)
    return modelo, k, palpites

# ================== [GENERATOR CORE] ==================
def _amostrar_dezenas(scores_25, k=15, correl_steps=10, pares_range=(6,9)):
    # OBS: Veto de combinações já sorteadas REMOVIDO a pedido.
    # usados = combinacoes_ja_sorteadas() 
    
    dezenas = list(range(1, 26))

    base_weights = _normalize_probs(scores_25)

    for _ in range(5000):
        base = set(random.choices(dezenas, weights=base_weights, k=min(5, k)))
        atual = set(base)

        for _step in range(correl_steps):
            if len(atual) >= k:
                break
            aff = scores_correlacao(atual)
            mixed = _normalize_probs(0.5*aff + 0.5*base_weights)
            prox = random.choices(dezenas, weights=mixed, k=1)[0]
            atual.add(prox)

        while len(atual) < k:
            prox = random.choices(dezenas, weights=base_weights, k=1)[0]
            atual.add(prox)

        comb = sorted(atual)
        
        # Logica de veto removida
        # if tuple(comb) in usados:
        #    continue
            
        pares = sum(1 for d in comb if d % 2 == 0)
        if not (pares_range[0] <= pares <= pares_range[1]):
            continue
        return comb

    return None
# ============================================================
# 🔧 PATCH: Motor Legacy isolado (sem alterar comportamento)
# ============================================================
def scores_neurais(nome):
    s = _score_from_ls(nome)
    if s.sum() == 0:
        return scores_estatisticos()
    return _normalize_probs(s)

def scores_ls14():
    return scores_neurais("LS14")

def scores_ls15():
    return scores_neurais("LS15")

def scores_ls16():
    # ensemble inteligente
    s15 = scores_neurais("LS15")
    s14 = scores_neurais("LS14")
    sE = scores_estatisticos()
    return _normalize_probs(0.6*s15 + 0.3*s14 + 0.1*sE)

# ============================================================
# 🔧 PATCH: Modelo/K por plano (Organizado + preparado para expansão)
# ============================================================

# PLANOS / MODELOS BASE (Lotofácil)
# Free     → LS14 (fallback: estatístico)
# Silver   → LS14 (LS14++), mais estatístico / ímpares-pares nos menus antigos
# Gold     → LS15 (LS15++), com acesso a LS14/estat/ímpares-pares
# Platinum → LS16 (ensemble LS15++ + estatístico), com acesso aos demais
# R&D      → LS17 (pode ser expandido p/ LS18 depois)

PLAN_RULES = {
    # Free → LS14 / Estatístico (aqui vamos usar LS14 como base)
    "free": {
        "modelo": "LS14",  # interno usa neural v14
        "kmin": 15,
        "kmax": 15,
    },
    # Silver → LS14++ / Estatístico / Ímpares-Pares
    # Internamente mapearemos LS14++ → LS14
    "silver": {
        "modelo": "LS14++",  # alias, vamos tratar no patch 2
        "kmin": 15,
        "kmax": 17,
    },
    # Gold → LS15++ / LS14++ / Estatístico / Ímpares-Pares
    # Internamente mapearemos LS15++ → LS15
    "gold": {
        "modelo": "LS15++",  # alias
        "kmin": 15,
        "kmax": 19,
    },
    # Platinum → LS16 / LS15++ / LS14++ / Estatístico / Ímpares-Pares
    "platinum": {
        "modelo": "LS16",  # ensemble híbrido
        "kmin": 15,
        "kmax": 20,
    },
    # R&D → LS17 / LS18 (podemos usar LS17 como base por enquanto)
    "r&d": {
        "modelo": "LS17",
        "kmin": 15,
        "kmax": 20,
    },
}

# -------------------------------
# Normalizador de nomes de modelos
# -------------------------------
MODEL_ALIAS = {
    "LS14++": "LS14",
    "LS15++": "LS15",
    "LS16++": "LS16",
}

def normalize_model(name: str) -> str:
    """Normaliza LS14++ → LS14, LS15++ → LS15, etc."""
    if not name:
        return "ESTAT"
    name = name.strip().upper()
    return MODEL_ALIAS.get(name, name)

# ------------------------------------------
# Helper: normalizar nome de plano do banco
# ------------------------------------------
def _canonical_plan_name(nome_plano: str) -> str:
    """
    Normaliza nomes de plano vindo da tabela ou sessão.
    A ordem de detecção é CRÍTICA:
      1. platinum
      2. gold
      3. silver
      4. r&d
      5. free
    Isso impede que qualquer variação seja interpretada como FREE por acidente.
    """

    if not nome_plano:
        return "free"

    n = (
        nome_plano.strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("á", "a")
        .replace("é", "e")
        .replace("ê", "e")
    )

    tokens = n.split()

    # 1️⃣ PLATINUM — detecta FIRST sempre
    if "plat" in n or "plati" in n:
        return "platinum"

    # 2️⃣ GOLD
    if "gold" in n or "ouro" in n:
        return "gold"

    # 3️⃣ SILVER
    if "silver" in n or "prata" in n or "silv" in n:
        return "silver"

    # 4️⃣ R&D
    if "r&d" in n or "rd" in tokens or "pesquisa" in n:
        return "r&d"

    # 5️⃣ FREE (somente se realmente for free)
    if n.strip() in ("free", "gratis", "grátis"):
        return "free"

    # fallback nunca vira free automaticamente
    return "free"

def _modelo_e_k_por_plano(nome_plano: str, k_escolhido: int | None):
    """
    Resolve qual modelo neural/stat usar e qual K.
    DEBUG COMPLETO habilitado.
    """
    print("\n============================")
    print("DEBUG _modelo_e_k_por_plano")
    print("============================")

    print(">> nome_plano recebido:", repr(nome_plano))

    # 1. Normaliza nome bruto (minusculo + strip)
    nome_bruto = (nome_plano or "").strip().lower()
    print(">> nome_bruto (lower/strip):", repr(nome_bruto))

    # 2. Canonical (unifica variações)
    plano_key = _canonical_plan_name(nome_bruto)
    print(">> plano_key (canonical):", repr(plano_key))

    # 3. Carrega regra da tabela PLAN_RULES
    cfg = PLAN_RULES.get(plano_key, PLAN_RULES["free"])
    print(">> cfg carregado:", cfg)

    # 4. Lê modelo bruto (pode ser LS14++, LS15++ etc)
    modelo_raw = cfg.get("modelo", "ESTAT")
    print(">> modelo_raw:", repr(modelo_raw))

    # 5. Normaliza modelo (remove ++)
    modelo = normalize_model(modelo_raw)
    print(">> modelo normalizado:", repr(modelo))

    # 6. Faixa de dezenas
    kmin = cfg.get("kmin", 15)
    kmax = cfg.get("kmax", 15)
    print(">> faixa:", kmin, "-", kmax)

    # k escolhido
    if k_escolhido is None:
        k = kmin
    else:
        k = max(kmin, min(kmax, int(k_escolhido)))
    print(">> k_escolhido:", k_escolhido)
    print(">> k final:", k)

    print("===== FIM DEBUG =====\n")

    return modelo, k

# ============================================================
# 🔧 PATCH: Função Principal - Dispatcher de Pipeline
# ============================================================
# IMPORTANTE:
# No topo do arquivo, USE_NEW_PIPELINE já foi definido como:
#   USE_NEW_PIPELINE = os.getenv("USE_NEW_MODEL_PIPELINE", "0") == "1"
# Não redefina aqui, para não sobrescrever a flag de ambiente.
# Basta usar USE_NEW_MODEL_PIPELINE=1 no ambiente para ativar o pipeline novo.

def verificar_limite_palpites(id_usuario: int):
    """
    Retorna:
        permitido (bool)
        nome_plano (str)
        restantes (int)

    Versão simplificada (DEV / estável):
    - Fonte ÚNICA do plano: usuarios.id_plano
    - Limite vem SEMPRE da tabela planos (palpites_max ou palpites_dia)
    - Se não achar plano no usuário, cai para plano Free.
    - NÃO usa mais client_plans aqui (evita conflito de dados sujos).
    """

    from datetime import date
    from sqlalchemy import text
    from db import Session

    hoje = date.today()
    ano = hoje.year
    mes = hoje.month

    db = Session()
    try:
        # ----------------------------------------------------
        # 1) PLANO DO USUÁRIO (usuarios.id_plano)
        # ----------------------------------------------------
        row = db.execute(text("""
            SELECT
                p.id   AS id_plano,
                p.nome AS nome_plano,
                COALESCE(p.palpites_max, p.palpites_dia, 0) AS limite_mes
            FROM usuarios u
            JOIN planos p ON p.id = u.id_plano
            WHERE u.id = :uid
              AND p.status = 'A'
            LIMIT 1
        """), {"uid": id_usuario}).mappings().fetchone()

        fonte_plano = "usuarios.id_plano"

        # ----------------------------------------------------
        # 2) Fallback: plano Free (se não achar nada no usuário)
        # ----------------------------------------------------
        if not row:
            row = db.execute(text("""
                SELECT
                    id   AS id_plano,
                    nome AS nome_plano,
                    COALESCE(palpites_max, palpites_dia, 0) AS limite_mes
                FROM planos
                WHERE LOWER(nome) = 'free'
                  AND status = 'A'
                LIMIT 1
            """)).mappings().fetchone()
            fonte_plano = "free-fallback"

        if not row:
            print("[verificar_limite_palpites] Nenhum plano encontrado; bloqueando.")
            return False, "Sem plano", 0

        nome_plano = (row["nome_plano"] or "").strip()
        limite_mes = int(row["limite_mes"] or 0)

        if limite_mes <= 0:
            print(
                f"[verificar_limite_palpites] "
                f"Plano {nome_plano} sem limite definido; bloqueando."
            )
            return False, nome_plano, 0

        # ----------------------------------------------------
        # 3) CONTAGEM DE PALPITES NO MÊS  (campo CORRETO: data)
        # ----------------------------------------------------
        usados = db.execute(text("""
            SELECT COUNT(*)
            FROM palpites
            WHERE id_usuario = :uid
              AND DATE_PART('year', data)  = :ano
              AND DATE_PART('month', data) = :mes
        """), {
            "uid": id_usuario,
            "ano": ano,
            "mes": mes,
        }).scalar() or 0

        restantes = max(0, limite_mes - usados)
        permitido = restantes > 0

        print(
            "[verificar_limite_palpites] "
            f"fonte={fonte_plano} "
            f"id_usuario={id_usuario} "
            f"plano={nome_plano} "
            f"limite_mes={limite_mes} "
            f"usados={usados} "
            f"restantes={restantes}"
        )

        return permitido, nome_plano, restantes

    finally:
        db.close()

# ============ LEGACY ============
def _gerar_para_plano_legacy(nome_plano, qtd, k_escolhido):
    """
    Mantém o comportamento legacy, mas pegando modelo e k
    exclusivamente de _modelo_e_k_por_plano() (PLAN_RULES).
    """
    print(">>> ENTROU scores_neurais (LEGACY)")

    # modelo e k vindos da tabela PLAN_RULES
    modelo, k = _modelo_e_k_por_plano(nome_plano, k_escolhido)

    # usa exatamente esse modelo aqui (nada de modelo_por_plano)
    palpites = gerar_palpites_por_modelo(modelo = modelo,   # 👈 usa o modelo vindo do PLAN_RULES
    qtd = qtd,
    k = k
)
    return modelo, k, palpites

# ============================================================
#          PIPELINE NOVO — FINAL (LS14 / LS15 / LS16)
# ============================================================

def _amostrar_por_modelo_keras(metas, k):
    """
    Gera 1 palpite a partir de uma lista de modelos carregados (metas).
    Seleciona 1 modelo aleatoriamente, roda predict() e amostra k dezenas.
    """
    import numpy as np

    meta = random.choice(metas)
    model = meta["model"]
    seq_len = meta["expected_seq_len"]

    # usa histórico mínimo → 50 zeros
    arr = np.zeros((1, seq_len, 25), dtype=np.float32)

    pred = model.predict(arr, verbose=0)[0]
    pred = np.maximum(pred, 0)

    idx = np.argsort(pred)[-k:] + 1
    return sorted(idx.tolist())

def gerar_para_plano(nome_plano: str, qtd: int = 3, k_escolhido: int | None = None):
    """
    Dispatcher único: decide se usa pipeline novo ou legacy,
    sempre respeitando PLAN_RULES + _modelo_e_k_por_plano.
    """
    nome_norm = _canonical_plan_name(nome_plano)
    if USE_NEW_PIPELINE:
        # pipeline novo (LS16, LS17 etc.)
        return _gerar_para_plano_pipeline_novo(nome_norm, qtd, k_escolhido)
    else:
        # pipeline legacy (mantém comportamento atual)
        return _gerar_para_plano_legacy(nome_norm, qtd, k_escolhido)

def _gerar_para_plano_novo(nome_plano, qtd, k_escolhido):
    modelo, k = _modelo_e_k_por_plano(nome_plano, k_escolhido)
    modelo_up = (modelo or "ESTAT").upper()

    palpites = []

    # função anti-duplicação
    def add_unique(p):
        if not p:
            return
        t = tuple(sorted(p))
        if t not in [tuple(sorted(x)) for x in palpites]:
            palpites.append(list(t))

    try:
        # → ESTATÍSTICO
        if modelo_up in ("ESTAT", "ESTATÍSTICO", "ESTATISTICO"):
            for _ in range(qtd):
                p = gerar_palpite_estatistico(limite=k)
                add_unique(p)

        # → LS14 / LS15 = mesmo motor
        elif modelo_up in ("LS14", "LS15"):
            metas = carregar_modelo_ls(model_name=modelo_up)

            if not metas:
                logging.warning(f"[NOVO PIPELINE] {modelo_up} não carregado → fallback estat.")
                for _ in range(qtd):
                    p = gerar_palpite_estatistico(limite=k)
                    add_unique(p)
            else:
                for _ in range(qtd):
                    p = _amostrar_por_modelo_keras(metas, k)
                    add_unique(p)

        # → LS16 (PLATINUM)
        elif modelo_up == "LS16":
            for _ in range(qtd):
                try:
                    p = gerar_palpite_ls16_platinum(k=k)
                except Exception as e:
                    logging.warning(f"[LS16] falhou → fallback estat. erro: {e}")
                    p = gerar_palpite_estatistico(limite=k)
                add_unique(p)

        # → LS17 / LS18 / R&D → usar legacy por enquanto
        else:
            logging.warning(f"[NOVO PIPELINE] Modelo {modelo_up} sem implementação → legacy.")
            return _gerar_para_plano_legacy(nome_plano, qtd, k_escolhido)

    except Exception as e:
        logging.error(f"[NOVO PIPELINE] erro: {e}")
        return _gerar_para_plano_legacy(nome_plano, qtd, k_escolhido)

    if not palpites:
        return _gerar_para_plano_legacy(nome_plano, qtd, k_escolhido)

    return modelo_up, k, palpites

def _produto_copy_modelo(modelo_key: str) -> tuple[str, str]:
    """
    Retorna (nome_exibicao, copy_curta) para o modelo.
    """
    m = (modelo_key or "").upper()

    if m in ("ALEATÓRIO", "ALEATORIO", "RANDOM"):
        return ("Aleatório", "Combinações aleatórias equilibradas.")

    if m in ("ESTAT", "ESTATÍSTICO", "ESTATISTICO"):
        return ("Estatístico Inteligente", "Frequência histórica + recência + correlação (coocorrência).")

    if m in ("LS14", "LS14++"):
        # Free / Silver base
        return ("IA Neural v14++" if "++" in m else "IA Neural v14",
                "Padrões avançados aprendidos com janela REDUZIDA.")

    if m in ("LS15", "LS15++"):
        return ("IA Neural v15++" if "++" in m else "IA Neural v15",
                "Padrões avançados + robustez temporal (eNSEMble).")

    if m in ("LS16", "LS16_PLATINUM", "LS_PLATINUM"):
        return ("IA Híbrida LS16 (Platinum)",
                "Ensemble Neural + Estatística (o melhor dos  2(DOIS)  mundos).")

    if m == "LS17":
        return ("IA Experimental LS17", "Arquitetura avançada focada em pesquisa (R&D).")

    # fallback: devolve como vier
    return (modelo_key, "")

# ================================================================
# Modal FaixaBet — versão estável e funcional (sem congelar tela)
# ================================================================

def _normalize_numbers(x):
    out = []
    if isinstance(x, (list, tuple)):
        for v in x:
            out.extend(_normalize_numbers(v))
        return out
    if isinstance(x, str):
        return [int(n) for n in re.findall(r"\d+", x)]
    try:
        return [int(x)]
    except Exception:
        return out

def _extract_id_and_numbers(item):
    pid = None
    dezenas = []
    if isinstance(item, dict):
        for k in ("id", "id_palpite", "id_registro", "pk", "id_palpites"):
            if k in item and item[k]:
                pid = str(item[k])
                break
        for k in ("numeros", "dezenas", "palpite", "jogada"):
            if k in item and item[k]:
                dezenas = _normalize_numbers(item[k])
                break
    elif isinstance(item, (list, tuple)):
        for v in item:
            dezenas.extend(_normalize_numbers(v))
        if dezenas and isinstance(item[0], (int, str)) and not isinstance(item[0], list):
            pid = str(item[0])
    elif isinstance(item, str):
        dezenas = _normalize_numbers(item)
    else:
        dezenas = _normalize_numbers(item)
    id_str = f" · id {pid}" if pid else ""
    return id_str, dezenas

def exibir_modal_palpites(palpites_gerados):
    """
    Exibe o modal de palpites usando o ID REAL salvo no banco.

    Espera cada item no formato:
        {"id": <id_palpite>, "numeros": [1,2,3,...] }
    ou uma lista simples de dezenas, ex: [1,2,3,...]
    """

    cards = []

    for i, item in enumerate(palpites_gerados or [], start=1):
        # Aceita tanto dict quanto lista simples
        palpite_id = None
        dezenas_list = []

        if isinstance(item, dict):
            palpite_id = item.get("id", None)
            dezenas_list = item.get("numeros") or item.get("dezenas") or []
        else:
            dezenas_list = item

        id_suffix = f" · id {palpite_id}" if palpite_id is not None else ""
        dezenas_txt = " ".join(f"{int(d):02d}" for d in dezenas_list)

        cards.append(f"""
        <div class="palpite-card">
            <div class="palpite-num">#{i}{id_suffix}</div>
            <div class="palpite-dezenas">{dezenas_txt}</div>
        </div>
        """)

    cards_html = "".join(cards) or "<div style='opacity:.7'>Sem palpites.</div>"

    rows = math.ceil(max(1, len(palpites_gerados or [1])) / 3)
    fallback_height = max(400, min(1100, 240 + rows * 100))

    html = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8" />
            <style>
                :root {{
                    --brand: #07a507;
                    --bg-dim: rgba(0,0,0,.45);
                }}
                html, body {{
                    margin:0; padding:0;
                    font-family: system-ui, 'Segoe UI', Roboto, Arial, sans-serif;
                    background: transparent;
                }}
                .overlay {{
                    position: fixed; inset:0;
                    background: var(--bg-dim);
                    display:flex; align-items:center; justify-content:center;
                }}
                .modal {{
                    position: relative;
                    width: min(940px, 94vw);
                    max-height: 88vh; overflow:auto;
                    background:#fff;
                    border:2px solid var(--brand);
                    border-radius:16px;
                    box-shadow:0 10px 30px rgba(0,0,0,.25);
                    padding:20px 22px;
                }}
                .close {{
                    position:absolute; top:10px; right:14px;
                    border:0; background:none; color:var(--brand);
                    font-size:24px; cursor:pointer;
                }}
                h3 {{ text-align:center; color:var(--brand); margin:6px 0 10px; }}
                .msg {{ text-align:center; margin:4px 0 14px; font-weight:600; }}
                .grid {{
                    display:grid; gap:12px;
                    grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
                }}
                .palpite-card {{
                    background:#eaffe9;
                    border:2px solid var(--brand);
                    border-radius:12px;
                    padding:8px 10px;
                    word-wrap:break-word; overflow-wrap:break-word;
                }}
                .palpite-num {{
                    color:var(--brand);
                    font-weight:700;
                    margin-bottom:4px;
                }}
                .palpite-dezenas {{
                    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
                    font-size:14px; color:#000; line-height:1.4;
                    white-space:normal;
                }}
                .tip {{
                    margin-top:14px; text-align:center; color:#555; font-size:13px;
                }}
            </style>
        </head>

        <body>
            <div class="overlay" id="fxb-overlay">
                <div class="modal" role="dialog" aria-modal="true">
                    <button class="close" id="fxb-close" title="Fechar">✕</button>
                    <h3>Palpites Gerados</h3>
                    <div class="msg">Hoje é o dia certo para apostar!</div>
                    <div class="grid">{cards_html}</div>
                    <div class="tip">Selecione e copie os números (Ctrl+C) para colar onde quiser.</div>
                </div>
            </div>
            <script>
                (function(){{
                    const iframe = window.frameElement;
                    function lockScroll(lock){{
                        const pd = window.parent.document;
                        const ht = pd.documentElement, bd = pd.body;
                        if(lock){{ ht.style.overflow='hidden'; bd.style.overflow='hidden'; }}
                        else{{ ht.style.overflow=''; bd.style.overflow=''; }}
                    }}
                    function closeModal(){{
                        if(!iframe) return;
                        lockScroll(false);
                        iframe.remove();
                    }}
                    if(iframe){{
                        iframe.style.position='fixed';
                        iframe.style.top='0'; iframe.style.left='0';
                        iframe.style.width='100vw'; iframe.style.height='100vh';
                        iframe.style.zIndex='999999'; iframe.style.background='transparent';
                        lockScroll(true);
                        document.getElementById('fxb-close').onclick=closeModal;
                        document.getElementById('fxb-overlay').onclick=(e)=>{{ if(e.target.id==='fxb-overlay') closeModal(); }};
                        window.onkeydown=(e)=>{{ if(e.key==='Escape') closeModal(); }};
                    }}
                }})();
            </script>
        </body>
    </html>
        """

    components.html(html, height=fallback_height, scrolling=False)

# -------------------- UI / CORE - GENERATION --------------------

def _render_badge_modelo(modelo_usado: str, k_final: int):
    """
    Mostra o badge do modelo na UI sem quebrar o Streamlit.
    """
    nome, desc = _produto_copy_modelo(modelo_usado)
    st.markdown(
        f"""
        <div style="padding:6px 10px; background:#e7ffe7; border-left:4px solid #0a0; margin:10px 0; border-radius:6px;">
            <b>Modelo utilizado:</b> {nome} · {k_final} dezenas<br>
            <span style="opacity:.8;">{desc}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

def show_loader():
    loader_placeholder = st.empty()

    icons = ["🏃‍♂️", "🚴‍♂️", "🏊‍♂️"]

    def render(icon):
        loader_placeholder.markdown(
            f"""
            <div style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                font-size: 70px;
                opacity: 0.85;
                z-index: 9999;
            ">
                {icon}
            </div>
            """,
            unsafe_allow_html=True,
        )

    return loader_placeholder, render, icons

def gerar_palpite_ui_legacy():
    """
    Tela original de geração de Bets (Lotofácil).
    - Usa regras por plano (Free, Silver, Gold, Platinum)
    - Respeita limites por dia/mês (verificar_limite_palpites)
    - Usa gerar_para_plano() por baixo
    - Salva no banco via salvar_palpite()
    - Exibe resultado no modal exibir_modal_palpites()
    """
    import time

    t0 = time.time()
    print(">>> ENTROU 2 na UI legacy")

    _lazy_imports()

    # ----------------- 1) Verifica login -----------------
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Você precisa estar logado para gerar Bets.")
        return
    usuario = st.session_state.usuario
    id_usuario = usuario.get("id")
    nome_plano_session = (usuario.get("nome_plano") or "").strip()  # volta a existir

    st.title(" Gerar Novas Bets - Lotofácil")

    # ----------------- 2) Limite de palpites -----------------

    permitido, nome_plano_limite, restantes_hoje = verificar_limite_palpites(id_usuario)

    if not permitido:
        st.error(f"Limite diário atingido para o plano **{nome_plano_limite}**.")
        return
    else:
        st.info(
            f"Plano ativo: **{nome_plano_limite}** · "
            f"Palpites restantes hoje: **{restantes_hoje}**"
        )

    nome_plano_raw = (nome_plano_limite or nome_plano_session or "").strip()
    plano_key = _canonical_plan_name(nome_plano_raw)

    # ⚠️ FONTE DA VERDADE DO PLANO:
    # Se o banco trouxe um nome (nome_plano_limite), usamos ele;
    # senão caímos para o que está na sessão.
    nome_plano_raw = (nome_plano_limite or nome_plano_session or "").strip()

    # Normalizamos para chave canônica (free/silver/gold/platinum/r&d)
    plano_key = _canonical_plan_name(nome_plano_raw)
    nome_plano_norm = plano_key  # usado em meta / logs

    # DEBUG para conferir tudo
    print("===== DEBUG GERAR UI =====")
    print("nome_plano_session =", repr(nome_plano_session))
    print("nome_plano_limite  =", repr(nome_plano_limite))
    print("nome_plano_raw     =", repr(nome_plano_raw))
    print("plano_key          =", repr(plano_key))
    print("==========================")

    # ----------------- 3) Configuração de geração -----------------
    col1, col2 = st.columns(2)
    with col1:
        qtd = st.number_input(
            "Quantidade de Bets para gerar:",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
        )

    # Regras do plano vindas do PLAN_RULES (kmin / kmax / modelo base)
    regra_plano = PLAN_RULES.get(plano_key, PLAN_RULES["free"])
    kmin = regra_plano["kmin"]
    kmax = regra_plano["kmax"]

    # Slider / valor fixo para escolher quantidade de dezenas por Bet
    with col2:
        if kmin == kmax:
            k_escolhido = kmin
            st.markdown(
                f"**Dezenas por Bet:** {kmin} "
                f"(fixo para o plano **{nome_plano_raw or nome_plano_limite}**)"
            )
        else:
            k_escolhido = st.slider(
                "Quantidade de dezenas por Bet:",
                min_value=kmin,
                max_value=kmax,
                value=kmin,
                step=1,
                help=(
                    f"Seu plano **{nome_plano_raw or nome_plano_limite}** "
                    f"permite entre {kmin} e {kmax} dezenas por Bet."
                ),
            )

    # ============================================================
    # Labels para os modelos
    # ============================================================
    LABELS = {
        "ESTAT": "Estatístico Inteligente",
        "LS14": "IA Neural v14",
        "LS15": "IA Neural v15",
        "LS16": "IA Neural Platinum",
        "LS17": "IA Neural Research v17",
    }


    # ============================================================
    # Modelo PREVIEW usando a MESMA função oficial de modelos
    # ============================================================
    modelo_preview, k_base_preview = _modelo_e_k_por_plano(plano_key, k_escolhido)

    print(
        ">>> PREVIEW modelo_preview =", modelo_preview,
        "k_base_preview =", k_base_preview
    )

    # Texto de preview com modelo em verde e bold
    st.markdown(
        "Seu modelo neural será o: "
        f"<b><span style='color:#009929'>"
        f"{LABELS.get(modelo_preview, modelo_preview)}"
        "</span></b> · "
        f"{k_base_preview} dezenas",
        unsafe_allow_html=True,
    )

    _, copy_txt = _produto_copy_modelo(modelo_preview)
    if copy_txt:
        st.caption(copy_txt)

    st.markdown(
    """
    <style>
    /* ===== BOTÃO GERAR BETS – FULL WIDTH REAL ===== */

    /* força o container do botão ocupar toda a largura */
    div[data-testid="stButton"] {
        width: 100% !important;
        display: block !important;
    }

    /* botão em si */
    div[data-testid="stButton"] > button {
        width: 100% !important;
        min-width: 100% !important;

        background-color: #009929 !important;
        color: #ffffff !important;

        border: none !important;
        outline: none !important;
        box-shadow: none !important;

        padding: 0.9em 1.4em !important;
        font-size: 1.1em !important;
        font-weight: 700 !important;
        border-radius: 10px !important;

        transition: background-color 0.15s ease-in-out !important;
    }

    /* hover */
    div[data-testid="stButton"] > button:hover {
        background-color: #00b33c !important;
    }

    /* active / focus */
    div[data-testid="stButton"] > button:active,
    div[data-testid="stButton"] > button:focus,
    div[data-testid="stButton"] > button:focus-visible {
        background-color: #009929 !important;
        color: #ffffff !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

    # ----------------- 4) Botão de gerar -----------------
    if st.button(" Gerar Novos Palpites", type="primary"):
        # === Loader simples visível imediatamente ===
        status = st.empty()

        try:
            # ---- PROCESSAMENTO PESADO ----
            modelo_usado, k_final, palpites = gerar_para_plano(
                nome_plano=plano_key,
                qtd=int(qtd),
                k_escolhido=int(k_escolhido) if k_escolhido else None,
            )

            # Remover loader
            status.empty()

            if not palpites:
                st.error("Não foi possível gerar Bets neste momento.")
                return

            # Salvar palpites
            ids_salvos = []
            for p in palpites:
                pid = salvar_palpite(
                    palpite=p,
                    modelo=modelo_usado,
                    extras_meta={"plano": plano_key},
                )
                if pid:
                    ids_salvos.append(pid)

            _render_badge_modelo(modelo_usado, k_final)

            st.success(
                f"Foram geradas **{len(palpites)}** Bets "
                f"(modelo **{modelo_usado}**, {k_final} dezenas)."
            )

            if ids_salvos:
                st.caption("IDs: " + ", ".join(map(str, ids_salvos)))

            exibir_modal_palpites([
                {"id": pid, "numeros": nums}
                for pid, nums in zip(ids_salvos, palpites)
            ])

        except Exception as e:
            status.empty()
            st.error(f"Erro inesperado: {e}")
            logging.exception(e)


def gerar_palpite_ui_novo():
    """
    Pipeline NOVO (LS16/LS17/LS18).
    Por enquanto, apenas delega ao LEGACY.
    """
    logging.info("[PIPELINE NOVO] Stub chamado — delegando ao LEGACY.")
    return gerar_palpite_ui_legacy()

def gerar_palpite_ui():
    """
    Entrada oficial da geração de palpites.
    O Streamlit sempre chama esta função.
    O switch entre LEGACY ↔ NOVO é controlado pela flag:
        USE_NEW_MODEL_PIPELINE=0/1
    """
    if USE_NEW_PIPELINE:
        logging.info("[PIPELINE] Usando NOVO pipeline (flag=1).")
        return gerar_palpite_ui_novo()
    else:
        logging.info("[PIPELINE] Usando pipeline LEGACY (flag=0).")
        return gerar_palpite_ui_legacy()
