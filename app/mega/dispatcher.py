# loterias/megasena/engines/dispatcher.py

from loterias.megasena.config.models_registry import MEGASENA_MODEL_REGISTRY

def resolver_motor_por_plano(plano: str) -> str:
    cfg = MEGASENA_MODEL_REGISTRY.get(plano)
    if not cfg:
        raise ValueError("Plano inválido")
    return cfg["motor"]
