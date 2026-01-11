
import os
import sys
from sqlalchemy import text
from datetime import datetime

sys.path.append(os.getcwd())
from app.db import Session

def inspect_hits():
    db = Session()
    try:
        # Check if table exists
        print("--- Checking tables ---")
        tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        table_names = [t[0] for t in tables]
        if "palpites_hits" not in table_names:
            print("Table 'palpites_hits' NOT FOUND.")
            return

        print("Table 'palpites_hits' FOUND.")

        # Check columns
        print("--- Columns ---")
        cols = db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='palpites_hits'")).fetchall()
        for c in cols:
            print(f"{c[0]} ({c[1]})")

        # Check sample data
        print("--- Sample Data ---")
        rows = db.execute(text("SELECT * FROM palpites_hits LIMIT 5")).fetchall()
        if not rows:
            print("Table is empty.")
        else:
            for r in rows:
                print(r)
        
        # Check specific user data if any (generic check)
        print("--- Count by Year/Month ---")
        # Try to guess date column
        date_col = next((c[0] for c in cols if "data" in c[0] or "created" in c[0] or "dt" in c[0]), None)
        if date_col:
             aggs = db.execute(text(f"""
                SELECT EXTRACT(YEAR FROM {date_col}) as y, EXTRACT(MONTH FROM {date_col}) as m, COUNT(*) 
                FROM palpites_hits 
                GROUP BY 1, 2 
                ORDER BY 1 DESC, 2 DESC
             """)).fetchall()
             for a in aggs:
                 print(f"{a.y}-{a.m}: {a[2]}")
        else:
            print("Could not identify a date column for aggregation.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_hits()
