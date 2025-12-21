# -*- coding: utf-8 -*-
"""
palpites_m.py – UI e lógica de Mega-Sena (v9)

Exposto para o main.py:
    - gerar_palpite_ui()
    - historico_palpites()
    - validar_palpite()

Regras v9 (Mega-Sena):
- Mostrar plano atual + usados hoje vs limite do plano (sempre).
- Mostrar bônus do mês atual (sempre).
- Selectbox de modelos filtrado por plano (Admin vê todos).
- Dezenas por plano:
    Free: 6
    Silver: 6–10
    Gold: 6–14
    Platinum: 6–20
- Qtde de palpites por solicitação:
    botões 1/3/7 + input numérico (Free desabilita 3/7 e input).
- Tipo usuário:
    U (cliente): respeita limite diário do plano; se exceder, tenta bônus do mês corrente.
    A (admin): sem restrição (modelos e quantidades).
- Grava na tabela palpites_m (id serial + demais campos).
- Exibe palpites em cards com mini-círculos verdes (padrão Lotofácil).

Obs:
- Este arquivo NÃO carrega modelos neurais diretamente; quem carrega é o engine.
"""

import random
from datetime import date
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import Session


# ================================================================
# 🔧 Imports v9 (registry/dispatcher/engines)
# ================================================================
try:
    from loterias.megasena.config.models_registry import MEGASENA_MODEL_REGISTRY
except Exception:
    MEGASENA_MODEL_REGISTRY = {}

try:
    from loterias.megasena.dispatcher import resolver_motor_por_plano
except Exception:
    def resolver_motor_por_plano(plano: str) -> str:
        cfg = MEGASENA_MODEL_REGISTRY.get(plano)
        if not cfg:
            raise ValueError("Plano inválido")
        return cfg["motor"]


# Engines (cada engine deve expor: gerar(qtd_dezenas:int) -> list[int])
_ENGINE_MAP: Dict[str, Any] = {}


def _load_engines_registry():
    """
    Carrega engines disponíveis (sem quebrar caso algum não exista no ambiente).
    """
    global _ENGINE_MAP
    if _ENGINE_MAP:
        return _ENGINE_MAP

    candidates = [
        ("RANDOM_MS", "loterias.megasena.engines.random_ms"),
        ("STAT_MS_V1", "loterias.megasena.engines.stat_ms_v1"),
        ("STAT_MS_V2", "loterias.megasena.engines.stat_ms_v2"),
        ("MS17_V5", "loterias.megasena.engines.ms17_v5_engine"),
    ]

    for key, modpath in candidates:
        try:
            mod = __import__(modpath, fromlist=["gerar"])
            if hasattr(mod, "gerar"):
                _ENGINE_MAP[key] = mod
        except Exception:
            pass

    return _ENGINE_MAP


# ================================================================
# 🔧 Utilitários gerais (DB/colunas/contagem)
# ================================================================
def _descobrir_coluna_data_palpites_m(db) -> Optional[str]:
    colunas_validas = ["created_at", "data", "dt", "timestamp"]
    rows = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'palpites_m'
    """)).fetchall()
    cols = [r[0].lower() for r in rows]
    for c in colunas_validas:
        if c.lower() in cols:
            return c
    return None


def _descobrir_colunas_promo_bonus(db) -> Dict[str, Optional[str]]:
    rows = db.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'promo_bonus'
    """)).fetchall()
    cols = [r[0] for r in rows]
    lower = {c.lower(): c for c in cols}

    def pick(*names):
        for n in names:
            if n.lower() in lower:
                return lower[n.lower()]
        return None

    return {
        "qtd": pick("qtde_bonus", "qtd_bonus", "bonus_mes", "qtde-bonus", "qtd-bonus"),
        "usados": pick("bonus_usados", "qtde_usados", "bonus-usados"),
        "mes": pick("mes_bonus", "mes-bonus"),
        "data": pick("data", "created_at", "dt", "timestamp"),
        "id_client": pick("id_client", "idcliente", "id_usuario", "iduser"),
    }


def _get_usuario_ctx(uid: int) -> Dict[str, Any]:
    db = Session()
    try:
        ts_col = _descobrir_coluna_data_palpites_m(db) or "created_at"

        plano = db.execute(text("""
            SELECT p.nome AS plano_nome,
                   COALESCE(p.palpites_dia, 0) AS limite_dia
            FROM usuarios u
            JOIN planos p ON p.id = u.id_plano
            WHERE u.id = :uid
        """), {"uid": uid}).fetchone()

        plano_nome = (plano.plano_nome if plano else "Free") or "Free"
        limite_dia = int(plano.limite_dia) if plano and plano.limite_dia is not None else 0

        usados_hoje = db.execute(text(f"""
            SELECT COUNT(*)
            FROM palpites_m
            WHERE id_usuario = :uid
              AND DATE({ts_col}) = CURRENT_DATE
        """), {"uid": uid}).scalar() or 0
        usados_hoje = int(usados_hoje)

        bonus_total = 0
        bonus_usados = 0

        promo_cols = _descobrir_colunas_promo_bonus(db)
        if promo_cols.get("qtd") and promo_cols.get("usados") and promo_cols.get("mes") and promo_cols.get("id_client"):
            mes_atual = date.today().month
            try:
                row = db.execute(
                    text(f"""
                        SELECT
                            COALESCE({promo_cols['qtd']}, 0) AS qtd,
                            COALESCE({promo_cols['usados']}, 0) AS usados
                        FROM promo_bonus
                        WHERE {promo_cols['id_client']} = :uid
                          AND {promo_cols['mes']} = :mes
                        ORDER BY id DESC
                        LIMIT 1
                    """),
                    {"uid": uid, "mes": mes_atual},
                ).fetchone()
                if row:
                    bonus_total = int(row.qtd or 0)
                    bonus_usados = int(row.usados or 0)
            except Exception:
                try:
                    row = db.execute(
                        text(f"""
                            SELECT
                                COALESCE({promo_cols['qtd']}, 0) AS qtd,
                                COALESCE({promo_cols['usados']}, 0) AS usados
                            FROM promo_bonus
                            WHERE {promo_cols['id_client']} = :uid
                            ORDER BY id DESC
                            LIMIT 1
                        """),
                        {"uid": uid},
                    ).fetchone()
                    if row:
                        bonus_total = int(row.qtd or 0)
                        bonus_usados = int(row.usados or 0)
                except Exception:
                    pass

        bonus_restante = max(0, bonus_total - bonus_usados)
        bonus_dia_teorico = int(bonus_total / 26) if bonus_total else 0
        bonus_dia_disponivel = min(bonus_dia_teorico, bonus_restante)

        return {
            "plano_nome": plano_nome,
            "limite_dia": limite_dia,
            "usados_hoje": usados_hoje,
            "bonus_total_mes": bonus_total,
            "bonus_usados_mes": bonus_usados,
            "bonus_restante_mes": bonus_restante,
            "bonus_dia_teorico": bonus_dia_teorico,
            "bonus_dia_disponivel": bonus_dia_disponivel,
        }
    finally:
        db.close()


def _regras_dezenas(plano_nome: str, tipo_usuario: str) -> Tuple[int, int, bool]:
    if (tipo_usuario or "").upper() == "A":
        return 6, 20, False

    p = (plano_nome or "Free").strip().lower()
    if p == "free":
        return 6, 6, True
    if p == "silver":
        return 6, 10, False
    if p == "gold":
        return 6, 14, False
    if p == "platinum":
        return 6, 20, False
    return 6, 6, True


def _modelos_disponiveis_por_plano(plano_nome: str, tipo_usuario: str) -> Dict[str, Dict[str, Any]]:
    """
    Admin (A): vê todos os modelos.
      - Se registry estiver vazio, devolve fallback admin com TODOS os motores.
    Usuário (U): vê apenas o modelo do próprio plano (com normalização de chave).
    """
    reg = MEGASENA_MODEL_REGISTRY or {}

    # ✅ ADMIN: sempre tem lista "cheia", mesmo se registry não carregou
    if (tipo_usuario or "").upper() == "A":
        if reg:
            return {
                f"{plano} — {cfg.get('motor')}": {"plano": plano, **cfg}
                for plano, cfg in reg.items()
            }

        # Fallback admin (mantém UX e permite testar engines)
        return {
            "RANDOM_MS — Aleatório": {
                "plano": "ALL",
                "motor": "RANDOM_MS",
                "descricao": "Aleatório (fallback admin)"
            },
            "STAT_MS_V1 — Estatístico": {
                "plano": "ALL",
                "motor": "STAT_MS_V1",
                "descricao": "Estatístico v1 (fallback admin)"
            },
            "STAT_MS_V2 — Estatístico+": {
                "plano": "ALL",
                "motor": "STAT_MS_V2",
                "descricao": "Estatístico v2 (fallback admin)"
            },
            "MS17_V5 — IA Platinum": {
                "plano": "ALL",
                "motor": "MS17_V5",
                "descricao": "IA Neural Mega-Sena (Admin)"
            },
        }

    # ✅ USUÁRIO: usa registry; se não existir, fallback seguro
    if not reg:
        return {
            "Fallback — Aleatório": {
                "plano": "Free",
                "motor": "RANDOM_MS",
                "descricao": "Fallback de segurança (registry vazio)"
            }
        }

    plano_key = (plano_nome or "").strip().title()
    cfg = reg.get(plano_key)

    if not cfg:
        cfg = reg.get("Free") or next(iter(reg.values()), None)

    if not cfg:
        return {
            "Fallback — Aleatório": {
                "plano": "Free",
                "motor": "RANDOM_MS",
                "descricao": "Fallback absoluto"
            }
        }

    return {
        f"{plano_key} — {cfg.get('motor')}": {
            "plano": plano_key,
            **cfg
        }
    }


def _render_dezenas_circulos(dezenas):
    st.markdown(
        "<div style='text-align:center; margin-top:10px; margin-bottom:5px;'>"
        + "".join(
            f"<span style='display:inline-block; background:#10b981; "
            f"color:white; border-radius:50%; width:40px; height:40px; "
            f"line-height:40px; margin:4px; font-weight:800;'>"
            f"{int(d):02d}</span>"
            for d in dezenas
        )
        + "</div>",
        unsafe_allow_html=True,
    )


# ================================================================
# 💾 Salvamento (retorna ID)
# ================================================================
def salvar_palpite_m(id_usuario: int, dezenas_fmt: str, modelo: str) -> Optional[int]:
    if not dezenas_fmt or len(str(dezenas_fmt).strip()) < 5:
        st.warning("⚠️ Palpite inválido ou vazio. Tente novamente.")
        return None

    db = Session()
    try:
        ts_col = _descobrir_coluna_data_palpites_m(db) or "created_at"
        sql = text(f"""
            INSERT INTO palpites_m (id_usuario, numeros, modelo, {ts_col})
            VALUES (:uid, :nums, :modelo, NOW())
            RETURNING id
        """)
        new_id = db.execute(sql, {"uid": id_usuario, "nums": dezenas_fmt, "modelo": modelo}).scalar()
        db.commit()
        return int(new_id) if new_id is not None else None
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao salvar palpite: {e}")
        return None
    finally:
        db.close()


def _atualizar_bonus_usados(uid: int, incrementar: int) -> None:
    if incrementar <= 0:
        return

    db = Session()
    try:
        promo_cols = _descobrir_colunas_promo_bonus(db)
        if not (promo_cols.get("usados") and promo_cols.get("mes") and promo_cols.get("id_client")):
            return

        mes_atual = date.today().month
        try:
            db.execute(
                text(f"""
                    UPDATE promo_bonus
                    SET {promo_cols['usados']} = COALESCE({promo_cols['usados']}, 0) + :inc
                    WHERE id = (
                        SELECT id
                        FROM promo_bonus
                        WHERE {promo_cols['id_client']} = :uid
                          AND {promo_cols['mes']} = :mes
                        ORDER BY id DESC
                        LIMIT 1
                    )
                """),
                {"inc": incrementar, "uid": uid, "mes": mes_atual},
            )
        except Exception:
            db.execute(
                text(f"""
                    UPDATE promo_bonus
                    SET {promo_cols['usados']} = COALESCE({promo_cols['usados']}, 0) + :inc
                    WHERE id = (
                        SELECT id
                        FROM promo_bonus
                        WHERE {promo_cols['id_client']} = :uid
                        ORDER BY id DESC
                        LIMIT 1
                    )
                """),
                {"inc": incrementar, "uid": uid},
            )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ================================================================
# 🧠 Engines dispatch
# ================================================================
def _gerar_por_motor(motor: str, qtd_dezenas: int):
    engines = _load_engines_registry()

    if motor in engines and hasattr(engines[motor], "gerar"):
        dezenas = engines[motor].gerar(int(qtd_dezenas))
        return sorted(list(map(int, dezenas)))

    return sorted(random.sample(range(1, 61), int(qtd_dezenas)))


# ================================================================
# 🎯 UI – Gerar Palpite Mega-Sena (v9)
# ================================================================
def gerar_palpite_ui():
    # ✅ CSS: botão verde + alinhamento visual (aplica 1x por sessão)
    if "ms_v9_css_injetado" not in st.session_state:
        st.markdown("""<style>...</style>""", unsafe_allow_html=True)
        st.session_state["ms_v9_css_injetado"] = True
        st.markdown("""
    <style>
    /* Só o botão "primary" (Gerar Palpites) */
    button[kind="primary"] {
        background-color: #10b981 !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 800 !important;
        height: 3rem !important;
        border: 1px solid #10b981 !important;
    }
    button[kind="primary"]:hover {
        background-color: #059669 !important;
        border: 1px solid #059669 !important;
    }
    </style>
    """, unsafe_allow_html=True)



    st.subheader("🎯 Gerar Palpites — Mega-Sena")

    usuario = st.session_state.get("usuario", {})
    if not usuario:
        st.warning("Você precisa estar logado para gerar palpites.")
        return

    uid = int(usuario.get("id", 0) or 0)

    # Tipo de usuário (U/A) – tolerante a chaves diferentes
    tipo_usuario = (usuario.get("tipo") or usuario.get("tipo_usuario") or usuario.get("perfil") or "U")
    tipo_usuario = str(tipo_usuario).upper().strip()
    if tipo_usuario not in ("U", "A"):
        tipo_usuario = "U"

    # Contexto do usuário
    ctx = _get_usuario_ctx(uid)
    plano_nome = ctx["plano_nome"]

    # Mostrar sempre: plano + usados vs limite + bônus do mês
    st.info(
        f"Plano atual: **{plano_nome}**  |  "
        f"Hoje: **{ctx['usados_hoje']}/{ctx['limite_dia']}**  |  "
        f"Bônus do mês: **{ctx['bonus_usados_mes']}/{ctx['bonus_total_mes']}** "
        f"(restante: **{ctx['bonus_restante_mes']}**)  |  "
        f"Bônus/dia (teórico): **{ctx['bonus_dia_disponivel']}**"
    )

    # Modelos por plano (Admin vê todos)
    opcoes = _modelos_disponiveis_por_plano(plano_nome, tipo_usuario)
    labels = list(opcoes.keys())

    if not labels:
        st.warning("⚠️ Nenhum modelo disponível no momento.")
        return

    escolha = st.selectbox(
        "Modelo de Geração:",
        labels,
        index=0,
        key="ms_v9_modelo_select"
    )

    cfg_modelo = opcoes.get(escolha)
    if not cfg_modelo:
        st.warning("⚠️ Modelo inválido no estado atual. Recarregue a seleção.")
        return

    motor = cfg_modelo.get("motor")
    st.caption(f"🧠 {cfg_modelo.get('descricao', '')}")

    # Dezenas por regra de negócio
    min_dz, max_dz, disabled_dz = _regras_dezenas(plano_nome, tipo_usuario)
    dezenas = st.number_input(
        "Quantidade de dezenas:",
        min_value=int(min_dz),
        max_value=int(max_dz),
        value=int(min_dz),
        disabled=bool(disabled_dz),
        key="ms_v9_qtd_dezenas"
    )

    # ============================================================
    # Qtde palpites por solicitação (ESTÁVEL)
    # ============================================================
    # ============================================================
    # Qtde palpites por solicitação (DEFINITIVO / SEM BUG)
    # ============================================================
    st.markdown("### Quantos palpites gerar agora?")
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

    # Estado inicial
    if "ms_qtd_palpites" not in st.session_state:
        st.session_state["ms_qtd_palpites"] = 1

    is_free_cliente = (
        tipo_usuario == "U"
        and (plano_nome or "").strip().lower() == "free"
    )

    # ----------------------------
    # Botões → ESCREVEM o estado
    # ----------------------------
    def set_qtd(n: int):
        st.session_state["ms_qtd_palpites"] = n

    c1.button("1", use_container_width=True, on_click=set_qtd, args=(1,))
    c2.button("3", use_container_width=True, disabled=is_free_cliente, on_click=set_qtd, args=(3,))
    c3.button("7", use_container_width=True, disabled=is_free_cliente, on_click=set_qtd, args=(7,))

    # ----------------------------
    # Input → ESCREVE o estado
    # ----------------------------
    novo_valor = c4.number_input(
        "Outro (qtde):",
        min_value=1,
        max_value=50 if tipo_usuario == "A" else 22,
        value=st.session_state["ms_qtd_palpites"],
        step=1,
        disabled=is_free_cliente,
        label_visibility="collapsed",
    )

    # Só atualiza se o usuário mexeu no input
    if novo_valor != st.session_state["ms_qtd_palpites"]:
        st.session_state["ms_qtd_palpites"] = int(novo_valor)

    qtd_palpites = int(st.session_state["ms_qtd_palpites"])

    st.success(f"DEBUG FINAL → qtd_palpites = {qtd_palpites}")


    # ============================================================
    # Validar limites (somente U)
    # ============================================================
    def validar_consumo(qtd: int) -> Tuple[bool, str, int]:
        if tipo_usuario == "A":
            return True, "Admin: sem limites.", 0

        limite = int(ctx["limite_dia"])
        usados = int(ctx["usados_hoje"])
        restante_plano = max(0, limite - usados)

        if qtd <= restante_plano:
            return True, f"Consumo do plano: {qtd}/{restante_plano} disponíveis hoje.", 0

        excedente = qtd - restante_plano

        bonus_dia = int(ctx["bonus_dia_disponivel"])
        if bonus_dia <= 0:
            return False, (
                f"⚠️ Limite diário do seu plano atingido ({usados}/{limite}). "
                f"Você não possui bônus diário disponível hoje."
            ), 0

        if excedente > bonus_dia:
            return False, (
                f"⚠️ Você pediu {qtd} palpites. Hoje você tem {restante_plano} pelo plano + "
                f"{bonus_dia} de bônus = {restante_plano + bonus_dia} no total."
            ), 0

        return True, (
            f"Usando {restante_plano} do plano + {excedente} de bônus hoje "
            f"(bônus/dia disponível: {bonus_dia})."
        ), excedente

    permitido, msg_limite, bonus_a_consumir = validar_consumo(qtd_palpites)
    st.write(msg_limite)
    if not permitido:
        return

    # ============================================================
    # Gerar (botão verde via CSS)
    # ============================================================
    if st.button("🎲 Gerar Palpites", use_container_width=True, key="ms_v9_btn_gerar", type="primary"):
    
        palpites_gerados = []

        for _ in range(qtd_palpites):
            dezenas_list = _gerar_por_motor(str(motor), int(dezenas))
            dezenas_list = _evitar_repetidos(dezenas_list)
            dezenas_fmt = " ".join(f"{n:02d}" for n in dezenas_list)

            novo_id = salvar_palpite_m(uid, dezenas_fmt, str(motor))
            palpites_gerados.append((novo_id, dezenas_list, str(motor)))

        if tipo_usuario == "U" and bonus_a_consumir > 0:
            _atualizar_bonus_usados(uid, int(bonus_a_consumir))

        st.success(f"✅ {len(palpites_gerados)} palpite(s) gerado(s) e salvo(s)!")

        # ✅ "Modal" fechável: expander aberto
        with st.expander("📋 Palpites Gerados (clique para fechar)", expanded=True):
            for pid, nums, motor_used in palpites_gerados:
                st.markdown(
                    f"""
                    <div style="border:2px solid #10b981; border-radius:14px; padding:10px; margin:10px 0; background:#f9fafb;">
                      <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div><b>ID:</b> {pid if pid is not None else "-"}</div>
                        <div style="opacity:0.85;"><b>Modelo:</b> {motor_used}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                _render_dezenas_circulos(nums)


# ================================================================
# Reaproveitado (com tolerância)
# ================================================================
def _evitar_repetidos(dezenas):
    try:
        df = pd.read_csv("loteriamega.csv")
        bolas = [f"Bola{i}" for i in range(1, 7)]
        existentes = {tuple(sorted(map(int, r))) for r in df[bolas].values.tolist()}
        while tuple(sorted(dezenas)) in existentes:
            dezenas = sorted(random.sample(range(1, 61), len(dezenas)))
        return dezenas
    except Exception:
        return dezenas


# ================================================================
# 📜 Histórico de Palpites (mantido)
# ================================================================
def historico_palpites():
    st.subheader("📜 Histórico de Palpites — Mega-Sena")
    usuario = st.session_state.get("usuario", {})
    if not usuario:
        st.warning("Você precisa estar logado.")
        return

    uid = int(usuario.get("id", 0) or 0)
    data_ini = st.date_input("Data inicial:", date.today().replace(day=1), key="ms_v9_hist_ini")
    data_fim = st.date_input("Data final:", date.today(), key="ms_v9_hist_fim")

    db = Session()
    try:
        ts_col = _descobrir_coluna_data_palpites_m(db) or "created_at"
        sql = f"""
            SELECT id, numeros, modelo, {ts_col} AS dt, valido
            FROM palpites_m
            WHERE id_usuario = :uid
              AND DATE({ts_col}) BETWEEN :ini AND :fim
            ORDER BY {ts_col} DESC
        """
        rows = db.execute(text(sql), {"uid": uid, "ini": data_ini, "fim": data_fim}).fetchall()
    finally:
        db.close()

    if not rows:
        st.info("Nenhum palpite encontrado no período.")
        return

    for r in rows:
        idp, nums, modelo, dt, valido = r
        txt_status = "✅ Validado" if (valido or "").upper() == "S" else "⏳ Não validado"
        cor = "#10b981" if (valido or "").upper() == "S" else "#d97706"

        st.markdown(
            f"""
            <div style="border:2px solid {cor}; border-radius:12px; padding:10px; margin-bottom:10px; background:#f9fafb;">
                <b>ID:</b> {idp} &nbsp;|&nbsp; <b>📅 {dt.strftime('%d/%m/%Y %H:%M')}</b><br>
                <b>🧠 Modelo:</b> {modelo}<br>
                <b>🎲 Números:</b> {nums}<br>
                <b>📌 Status:</b> <span style="color:{cor}; font-weight:600;">{txt_status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ================================================================
# ✅ Validação de Palpites (mantido)
# ================================================================
def validar_palpite():
    st.subheader("✅ Validar Palpite — Mega-Sena")
    usuario = st.session_state.get("usuario", {})
    if not usuario:
        st.warning("Você precisa estar logado.")
        return

    uid = int(usuario.get("id", 0) or 0)

    db = Session()
    try:
        ts_col = _descobrir_coluna_data_palpites_m(db) or "created_at"
        sql = f"""
            SELECT id, numeros, modelo, {ts_col} AS dt, valido
            FROM palpites_m
            WHERE id_usuario = :uid
            ORDER BY {ts_col} DESC
            LIMIT 30
        """
        rows = db.execute(text(sql), {"uid": uid}).fetchall()
    finally:
        db.close()

    if not rows:
        st.info("Nenhum palpite para validar.")
        return

    for r in rows:
        idp, nums, modelo, dt, valido = r
        is_validado = (valido or "").upper() == "S"
        status_txt = "✅ Validado" if is_validado else "⏳ Pendente"
        cor = "#10b981" if is_validado else "#d97706"

        st.markdown(
            f"""
            <div style="border:1px solid {cor}; border-radius:10px; padding:10px; margin-bottom:6px; background:#fff;">
                <b>ID:</b> {idp}<br>
                <b>🧠 Modelo:</b> {modelo}<br>
                <b>📅 Data:</b> {dt.strftime('%d/%m/%Y %H:%M')}<br>
                <b>🎲 Números:</b> {nums}<br>
                <b>📌 Status:</b> <span style="color:{cor}; font-weight:600;">{status_txt}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not is_validado:
            if st.button(f"✅ Validar #{idp}", key=f"ms_v9_validar_{idp}"):
                atualizar_status_palpite(idp)
                st.success(f"Palpite #{idp} validado com sucesso!")
                st.rerun()


def atualizar_status_palpite(id_palpite: int):
    db = Session()
    try:
        db.execute(text("""
            UPDATE palpites_m
            SET valido = 'S'
            WHERE id = :id
        """), {"id": id_palpite})
        db.commit()
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao validar palpite: {e}")
    finally:
        db.close()
