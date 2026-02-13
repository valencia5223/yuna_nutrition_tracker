
import os
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def debug_sleep_logs():
    print("--- Fetching ALL Sleep Logs ---")
    try:
        # Fetch all logs without date filter first
        res = supabase.table('sleep_logs').select('*').order('start_time', desc=True).execute()
        logs = res.data
        
        print(f"Total records found: {len(logs)}")
        for log in logs:
            print(f"ID: {log.get('id')}, Type: {log.get('type')}, Start: {log.get('start_time')}, End: {log.get('end_time')}")

        print("\n--- Testing 7-Day Filter ---")
        seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat() + 'Z'
        print(f"Filter Date (gte): {seven_days_ago}")
        
        filtered_res = supabase.table('sleep_logs').select('*')\
            .gte('start_time', seven_days_ago)\
            .order('start_time', desc=True).execute()
            
        print(f"Filtered records found: {len(filtered_res.data)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_sleep_logs()
