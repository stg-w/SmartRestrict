import os
import json
import oracledb
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 1522))
DB_SERVICE_NAME = os.getenv("DB_SERVICE_NAME")

print(f"Connecting to Oracle at {DB_HOST}:{DB_PORT}/{DB_SERVICE_NAME} as {DB_USER}...")

try:
    conn = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        service_name=DB_SERVICE_NAME
    )
    print(f"Connected successfully! Server version: {conn.version}")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

cursor = conn.cursor()

# 1. List all user tables
cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
tables = [row[0] for row in cursor.fetchall()]
print(f"\nFound {len(tables)} tables in schema {DB_USER}:")

schema_info = {}

for table in tables:
    # Row count
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    row_count = cursor.fetchone()[0]

    # Columns
    cursor.execute("""
        SELECT column_name, data_type, data_length, data_precision, data_scale, nullable
        FROM user_tab_columns
        WHERE table_name = :t
        ORDER BY column_id
    """, {"t": table})
    columns = [
        {
            "name": row[0],
            "type": row[1],
            "length": row[2],
            "precision": row[3],
            "scale": row[4],
            "nullable": row[5] == "Y"
        }
        for row in cursor.fetchall()
    ]

    # Primary and Foreign Keys
    cursor.execute("""
        SELECT c.constraint_name, c.constraint_type, c.r_constraint_name, cc.column_name
        FROM user_constraints c
        JOIN user_cons_columns cc ON c.constraint_name = cc.constraint_name
        WHERE c.table_name = :t
        ORDER BY c.constraint_name, cc.position
    """, {"t": table})
    constraints = [
        {
            "name": row[0],
            "type": row[1],
            "r_name": row[2],
            "column": row[3]
        }
        for row in cursor.fetchall()
    ]

    # Sample rows (first 3)
    cursor.execute(f'SELECT * FROM "{table}" FETCH FIRST 3 ROWS ONLY')
    col_names = [col[0] for col in cursor.description]
    sample_rows = []
    for r in cursor.fetchall():
        row_dict = {}
        for col_name, val in zip(col_names, r):
            row_dict[col_name] = str(val) if val is not None else None
        sample_rows.append(row_dict)

    schema_info[table] = {
        "row_count": row_count,
        "columns": columns,
        "constraints": constraints,
        "sample_rows": sample_rows
    }
    print(f"  {table}: {row_count} rows, {len(columns)} columns")

os.makedirs("docs", exist_ok=True)
with open("docs/schema_metadata.json", "w", encoding="utf-8") as f:
    json.dump(schema_info, f, indent=2)

print("\nSchema metadata dumped to docs/schema_metadata.json successfully!")

# Print details for key tables
print("\n" + "="*50)
print("TAGS:")
cursor.execute('SELECT * FROM "TAGS"')
for r in cursor.fetchall():
    print(" ", r)

print("\nTAG_RULES:")
cursor.execute('SELECT * FROM "TAG_RULES"')
for r in cursor.fetchall():
    print(" ", r)

print("\nRESTRICTIONS:")
cursor.execute('SELECT * FROM "RESTRICTIONS"')
for r in cursor.fetchall():
    print(" ", r)

print("\nRESTRICTION_RULES:")
cursor.execute('SELECT * FROM "RESTRICTION_RULES"')
for r in cursor.fetchall():
    print(" ", r)

print("\nNUTRIENTS:")
cursor.execute('SELECT * FROM "NUTRIENTS"')
for r in cursor.fetchall():
    print(" ", r)

print("\nDIETARY_TYPES:")
cursor.execute('SELECT * FROM "DIETARY_TYPES"')
for r in cursor.fetchall():
    print(" ", r)

cursor.close()
conn.close()
