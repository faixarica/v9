import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.palpites_legacy import _carregar_df_lotofacil, _stats_pack, _amostrar_dezenas

def test_load_df():
    print("Testing _carregar_df_lotofacil...")
    try:
        df, bolas = _carregar_df_lotofacil()
        print(f"Success! DF Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        if not df.empty:
            print(f"First row sample: {df.iloc[0].to_dict()}")
        return True
    except Exception as e:
        print(f"Failed _carregar_df_lotofacil: {e}")
        return False

def test_stats_pack():
    print("\nTesting _stats_pack...")
    try:
        freq_global, freq_rec, corr, df, bolas = _stats_pack(recencia=10)
        print(f"Success! Stats generated.")
        print(f"Freq Global Keys: {len(freq_global)}")
        return True
    except Exception as e:
        print(f"Failed _stats_pack: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_amostrar():
    print("\nTesting _amostrar_dezenas (veto removed)...")
    try:
        # Dummy scores (uniforme)
        scores = np.ones(25) / 25.0
        palpite = _amostrar_dezenas(scores, k=15)
        print(f"Success! Palpite generated: {palpite}")
        return True
    except Exception as e:
        print(f"Failed _amostrar_dezenas: {e}")
        return False

if __name__ == "__main__":
    if test_load_df():
        if test_stats_pack():
           test_amostrar()
