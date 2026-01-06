# loterias/megasena/config/models_registry.py

MEGASENA_MODEL_REGISTRY = {
    "Free": {
        "motor": "RANDOM_MS",
        "descricao": "Aleatório controlado",
        "tipo": "stat",
    },
    "Silver": {
        "motor": "STAT_MS_V1",
        "descricao": "Estatístico frequência + recência",
        "tipo": "stat",
    },
    "Gold": {
        "motor": "STAT_MS_V2",
        "descricao": "Estatístico avançado",
        "tipo": "stat",
    },
    "Platinum": {
        "motor": "MS17_V5",
        "descricao": "Rede neural Mega-Sena",
        "tipo": "neural",
    },
}
