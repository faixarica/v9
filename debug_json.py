
import os
import sys
import json
from sqlalchemy import text

sys.path.append(os.getcwd())
from app.db import Session

def inspect_json():
    db = Session()
    try:
        row = db.execute(text("""
            SELECT concurso, premiacao_json
            FROM resultados_oficiais_m
            ORDER BY concurso DESC
            LIMIT 1
        """)).fetchone()
        
        if row:
            print(f"Concurso: {row[0]}")
            val = row[1]
            print(f"Type: {type(val)}")
            print("--- Content ---")
            if isinstance(val, str):
                print(val)
            else:
                print(json.dumps(val, indent=2, default=str))
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_json()
