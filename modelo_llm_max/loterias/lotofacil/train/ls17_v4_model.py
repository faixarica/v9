"""
ls17_v4_model.py — fAIxaBet
---------------------------
Define o modelo Transformer LS17-v4.

Uso:
    from ls17_v4_model import build_ls17_v4_model
"""

import tensorflow as tf
from tensorflow.keras import layers, models

D_MODEL = 128
NUM_HEADS = 4
FF_DIM = 256
DROPOUT = 0.2

class TransformerBlock(layers.Layer):
    def __init__(self, d_model, num_heads, ff_dim, rate=0.1, **kwargs):
        super().__init__(**kwargs)
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=d_model)
        self.ffn = tf.keras.Sequential([
            layers.Dense(ff_dim, activation="relu"),
            layers.Dense(d_model),
        ])
        self.ln1 = layers.LayerNormalization(epsilon=1e-6)
        self.ln2 = layers.LayerNormalization(epsilon=1e-6)
        self.drop1 = layers.Dropout(rate)
        self.drop2 = layers.Dropout(rate)

    def call(self, x, training=False):
        att = self.att(x, x)
        att = self.drop1(att, training=training)
        out1 = self.ln1(x + att)

        ffn = self.ffn(out1)
        ffn = self.drop2(ffn, training=training)
        return self.ln2(out1 + ffn)

def build_ls17_v4_model(window, feature_dim):
    input_x = layers.Input(shape=(window, feature_dim), name="input_seq")

    x = layers.LayerNormalization(epsilon=1e-6)(input_x)

    x = TransformerBlock(D_MODEL, NUM_HEADS, FF_DIM, DROPOUT)(x)
    x = TransformerBlock(D_MODEL, NUM_HEADS, FF_DIM, DROPOUT)(x)

    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(DROPOUT)(x)

    out = layers.Dense(25, activation="sigmoid")(x)

    model = models.Model(input_x, out, name="LS17_v4_Transformer")
    return model
