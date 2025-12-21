import numpy as np

# carrega o MESMO Y usado no validate
Y = np.load("dados/Y_val.npy")  # ajuste o path se necessário

def baseline_random(y_true, k=10, trials=200):
    hits = []
    for _ in range(trials):
        for i in range(len(y_true)):
            verdade = set(np.where(y_true[i] == 1)[0])
            rand = set(np.random.choice(60, k, replace=False))
            hits.append(len(verdade & rand))
    return np.mean(hits)

print("Baseline Top-10:", baseline_random(Y, k=10))
