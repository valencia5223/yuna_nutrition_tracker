from app import app
import sys

print("Checking Routes...")
rules = [str(p) for p in app.url_map.iter_rules()]
quick_routes = [r for r in rules if '/quick/diaper' in r]

if len(quick_routes) > 0:
    print(f"SUCCESS: Found {len(quick_routes)} quick routes.")
    for r in quick_routes:
        print(f" - {r}")
else:
    print("FAILURE: No quick routes found.")
    sys.exit(1)
