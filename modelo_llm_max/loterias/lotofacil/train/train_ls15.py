import os
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout

BASE = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(BASE, "..", "..", "..", "dados")

X = np.load(os.path.join(DADOS, "X_ls15.npy"))
y = np.load(os.path.join(DADOS, "y_ls15.npy"))

model = Sequential([
    LSTM(96, return_sequences=True, input_shape=(X.shape[1], X.shape[2])),
    Dropout(0.3),
    LSTM(96),
    Dense(25, activation="sigmoid")
])

model.compile(optimizer="adam", loss="binary_crossentropy")

model.fit(X, y, epochs=40, batch_size=32, validation_split=0.1, verbose=2)

OUT = os.path.join(BASE, "..", "..", "..", "models", "ls15", "silver_ls15.keras")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
model.save(OUT)

print("✔ Modelo LS15 salvo:", OUT)
