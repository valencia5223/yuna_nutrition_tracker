from supabase import create_client
import os

URL = 'https://aiqodlsxkckvwxeyvgne.supabase.co'
KEY = 'sb_publishable_ClJY0IvWS-mPhw0FaPhxSg_w3x7fbA4'

try:
    supabase = create_client(URL, KEY)
    res = supabase.table('settings').select('*').limit(1).execute()
    print("Settings table data sample:")
    print(res.data)
    if res.data:
        print("Columns found in first row:")
        print(res.data[0].keys())
except Exception as e:
    print(f"FAILURE: {e}")
