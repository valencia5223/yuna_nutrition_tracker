from supabase import create_client
import os

URL = 'https://aiqodlsxkckvwxeyvgne.supabase.co'
KEY = 'sb_publishable_ClJY0IvWS-mPhw0FaPhxSg_w3x7fbA4'

try:
    supabase = create_client(URL, KEY)
    # Supabase Python client doesn't have a direct "list tables" method 
    # but we can try to select from expected tables to check existence.
    tables = ['user_profile', 'meals', 'growth', 'settings', 'sleep_logs', 'diaper_logs', 'completed_vaccinations']
    for table in tables:
        try:
            res = supabase.table(table).select('*').limit(1).execute()
            print(f"Table '{table}': EXISTS ({len(res.data)} rows found)")
        except Exception as e:
            if "does not exist" in str(e):
                print(f"Table '{table}': DOES NOT EXIST")
            else:
                print(f"Table '{table}': ERROR ({e})")
except Exception as e:
    print(f"FAILURE: {e}")
