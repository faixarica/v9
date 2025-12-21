import numpy as np
from tensorflow.keras.models import load_model

def validar_ls17_v4(model_path="models/ls17_v4/ls17_v4_transformer.keras"):
    print("🔍 Validando LS17-v4...")

    model = load_model(model_path)

    y_true = np.load("dados/rows_25bin.npy")
    y_prob = np.load("dados/preds_last.npy")  # gerado no treino

    acertos = []
    for prob, real in zip(y_prob, y_true):
        dezenas = prob.argsort()[-15:]
        real_dz = np.where(real == 1)[0]

        hits = len(set(dezenas) & set(real_dz))
        acertos.append(hits)

    media = np.mean(acertos)

    print(f"🎯 Média de acertos: {media:.2f}")

    if media >= 13:
        print("🟩 Modelo aprovado!")
    else:
        print("🟥 Modelo reprovado — precisa de novo treino.")

if __name__ == "__main__":
    validar_ls17_v4()
