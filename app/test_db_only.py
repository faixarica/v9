import sys
import os
import pandas as pd
import numpy as np
import random
from sqlalchemy import text
import logging

# Setup mocked environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import Session

def _carregar_df_lotofacil_isolated():
    """
    Copied from palpites_legacy.py for isolation testing
    """
    db = Session()
    try:
        # Busca concurso e dezenas
        query = text("""
            SELECT concurso, n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15
            FROM resultados_oficiais
            ORDER BY concurso DESC
        """)
        rows = db.execute(query).fetchall()
        
        if not rows:
             cols = ["Concurso"] + [f"Bola{i}" for i in range(1, 16)]
             return pd.DataFrame(columns=cols), [f"Bola{i}" for i in range(1, 16)]

        data = []
        for r in rows:
            row_dict = {"Concurso": r[0]}
            for i in range(1, 16):
                val = r[i]
                row_dict[f"Bola{i}"] = f"{int(val):02d}" if val is not None else "00"
            data.append(row_dict)
            
        df = pd.DataFrame(data)
        bolas = [f"Bola{i}" for i in range(1, 16)]
        
        return df, bolas

    except Exception as e:
        print(f"Error in _carregar_df_lotofacil_isolated: {e}")
        return pd.DataFrame(), []
    finally:
        db.close()

def _stats_pack_isolated(recencia=100):
    df, bolas = _carregar_df_lotofacil_isolated()
    if df.empty:
        return {}, {}, pd.DataFrame(), df, bolas

    # Frequência global
    todas = df[bolas].values.flatten()
    freq_global = pd.Series(todas).value_counts().sort_index()
    freq_global = {int(k): int(v) for k, v in freq_global.items()}
    
    return freq_global, df

def _amostrar_dezenas_isolated(scores_25, k=15):
    # Mocked function without all the correlation logic complexity, just testing the veto part
    dezenas = list(range(1, 26))
    # Normalize
    s = np.array(scores_25)
    s /= s.sum()
    
    # Just sample once to prove it runs
    chosen = np.random.choice(dezenas, size=k, replace=False, p=s)
    return sorted(chosen)

if __name__ == "__main__":
    print(" running isolated tests...")
    
    # 1. DB Load
    df, bolas = _carregar_df_lotofacil_isolated()
    print(f"DB Load: DF Shape {df.shape}")
    if not df.empty:
        print("DB Load: Success")
    else:
        print("DB Load: Empty (might be DB connection error or empty table)")

    # 2. Stats
    freq, _ = _stats_pack_isolated()
    print(f"Stats: Freq keys {len(freq)}")
    
    # 3. Sampling
    p = _amostrar_dezenas_isolated(np.ones(25), 15)
    print(f"Sampling: {p}")
