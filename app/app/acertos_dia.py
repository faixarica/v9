# acertos_dia_cli.py
from datetime import datetime, date
import argparse
from sqlalchemy import text
from db import Session
from tabulate import tabulate

def parse_num_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    return [int(x) for x in str(value).replace(";", ",").replace("|", ",").replace(" ", ",").split(",") if x.strip().isdigit()]

def sql_date_expr(alias, col):
    return f"""
    (CASE
        WHEN {alias}.{col} IS NULL THEN NULL
        WHEN pg_typeof({alias}.{col})::text IN ('date','timestamp without time zone','timestamp with time zone')
            THEN {alias}.{col}::timestamp::date
        WHEN {alias}.{col}::text ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
            THEN {alias}.{col}::date
        WHEN {alias}.{col}::text ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}$'
            THEN to_date({alias}.{col}::text, 'DD/MM/YYYY')
        ELSE NULL
     END)
    """

def fetch_resultado(data_ref):
    db = Session()
    try:
        sql = f"""
        SELECT concurso, {sql_date_expr('r','data')} AS data_norm,
               n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12,n13,n14,n15
        FROM resultados_oficiais r
        WHERE {sql_date_expr('r','data')} = :d
        ORDER BY concurso DESC LIMIT 1
        """
        row = db.execute(text(sql), {"d": data_ref.isoformat()}).fetchone()
        if not row:
            return None
        nums = [row.n1,row.n2,row.n3,row.n4,row.n5,row.n6,row.n7,row.n8,row.n9,row.n10,row.n11,row.n12,row.n13,row.n14,row.n15]
        return {"concurso": row.concurso, "data": row.data_norm, "numeros": nums}
    finally:
        db.close()

def fetch_palpites(data_ref, tipo, user_id=None):
    db = Session()
    try:
        has_numeros = db.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='palpites' AND column_name='numeros')
        """)).scalar()
        num_col = "numeros" if has_numeros else "dezenas"
        sql = f"""
        SELECT p.id, p.id_usuario, p.{num_col} AS nums, p.modelo, {sql_date_expr('p','data')} AS data_norm
        FROM palpites p WHERE {sql_date_expr('p','data')} = :d
        """
        params = {"d": data_ref.isoformat()}
        if tipo != "admin":
            sql += " AND p.id_usuario = :uid"
            params["uid"] = user_id
        rows = db.execute(text(sql + " ORDER BY p.id DESC"), params).fetchall()
        return [{
            "id": r.id,
            "id_usuario": r.id_usuario,
            "modelo": r.modelo,
            "numeros": parse_num_list(r.nums)
        } for r in rows if r.nums]
    finally:
        db.close()

def comparar(data_ref, tipo, user_id=None):
    res = fetch_resultado(data_ref)
    if not res:
        print("⚠️ Nenhum resultado oficial encontrado.")
        return
    palpites = fetch_palpites(data_ref, tipo, user_id)
    if not palpites:
        print("⚠️ Nenhum palpite encontrado.")
        return
    nums_oficiais = set(res["numeros"])
    rows = []
    for p in palpites:
        acertos = nums_oficiais.intersection(p["numeros"])
        qtd = len(acertos)
        if 11 <= qtd <= 15:
            rows.append([p["id"], p["id_usuario"], p["modelo"], qtd,
                         ",".join(f"{n:02d}" for n in sorted(p["numeros"])),
                         ",".join(f"{n:02d}" for n in sorted(acertos))])
    print(f"\n🧾 Concurso #{res['concurso']} — {data_ref.strftime('%d/%m/%Y')}")
    print(f"Números sorteados: {sorted(nums_oficiais)}")
    print(f"📊 Total de palpites: {len(palpites)}\n")
    if rows:
        print(tabulate(rows, headers=["ID", "Usuário", "Modelo", "Acertos", "Palpite", "Acertados"], tablefmt="grid"))
    else:
        print("Nenhum palpite com 11–15 acertos encontrado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tipo", required=True, choices=["admin","user"])
    parser.add_argument("--data", required=True)
    parser.add_argument("--user", type=int)
    args = parser.parse_args()
    data_ref = datetime.strptime(args.data, "%d/%m/%Y").date()
    comparar(data_ref, args.tipo, args.user)
