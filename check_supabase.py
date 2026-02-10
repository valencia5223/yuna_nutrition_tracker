from supabase import create_client
import os

URL = 'https://aiqodlsxkckvwxeyvgne.supabase.co'
KEY = 'sb_publishable_ClJY0IvWS-mPhw0FaPhxSg_w3x7fbA4'

print(f"Testing connection to {URL}...")
try:
    supabase = create_client(URL, KEY)
    res = supabase.table('user_profile').select('*').limit(1).execute()
    print("SUCCESS: Connection established.")
    print(res.data)
except Exception as e:
    print(f"FAILURE: {e}")
