# ms17_v5_model.py
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

def build_ms17_v5(input_dim: int, dropout=0.15):
    inp = keras.Input(shape=(input_dim,), name="x")

    x = layers.LayerNormalization()(inp)
    x = layers.Dense(512, activation="swish")(x)
    x = layers.Dropout(dropout)(x)
    x = layers.Dense(256, activation="swish")(x)
    x = layers.Dropout(dropout)(x)
    x = layers.Dense(128, activation="swish")(x)

    logits = layers.Dense(60, name="logits")(x)  # from_logits=True

    model = keras.Model(inp, logits, name="MS17_v5")
    return model

def compile_ms17_v5(model, lr=2e-3):
    loss = tf.keras.losses.BinaryCrossentropy(from_logits=True, label_smoothing=0.02)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss=loss,
        metrics=[
            tf.keras.metrics.AUC(curve="PR", name="auc_pr"),
            tf.keras.metrics.AUC(curve="ROC", name="auc_roc"),
        ],
    )
    return model
