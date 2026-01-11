
import os
import sys
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.db import Session
except ImportError:
    # Fail gracefully if path setup is wrong
    print("Could not import Session. Check path.")
    sys.exit(1)

def list_columns(table_name):
    db = Session()
    try:
        print(f"--- Columns for {table_name} ---")
        cols = db.execute(text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = '{table_name}'
        """)).fetchall()
        for c in cols:
            print(c[0])
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_columns("resultados_oficiais_m")
