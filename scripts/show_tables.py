import json

with open('docs/schema_metadata.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for table, info in data.items():
    cols = [f"{c['name']} ({c['type']})" for c in info['columns']]
    print(f"=== {table} ({info['row_count']} rows) ===")
    print("  Columns:", ", ".join(cols))
    if info['constraints']:
        c_strs = [f"{c['name']}: {c['type']} on {c['column']}" for c in info['constraints'] if c['type'] in ('P', 'R', 'U')]
        print("  Keys:", "; ".join(c_strs[:6]))
    if info['sample_rows']:
        print("  Sample:", info['sample_rows'][0])
    print()
