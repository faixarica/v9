"""
ls14pp_model.py — Arquitetura LS14++
------------------------------------
Modelo LSTM leve para Lotofácil Silver.
"""

from tensorflow.keras import layers, models

def build_ls14_model(window=25):
    m = models.Sequential([
        layers.Input((window, 25)),
        layers.LSTM(64),
        layers.Dense(25, activation="sigmoid")
    ])
    return m
