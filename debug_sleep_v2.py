
import os
import json
from datetime import datetime, timedelta
from supabase import create_client, Client

# app.py에서 가져온 설정
SUPABASE_URL = 'https://aiqodlsxkckvwxeyvgne.supabase.co'
SUPABASE_KEY = 'sb_publishable_ClJY0IvWS-mPhw0FaPhxSg_w3x7fbA4'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def debug_analyze_sleep():
    print("--- Debugging analyze_sleep ---")
    try:
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        print(f"Querying logs since: {thirty_days_ago}")

        res = supabase.table('sleep_logs').select('*')\
            .gte('start_time', thirty_days_ago)\
            .order('start_time', desc=True).execute()
        
        logs = res.data
        print(f"Total logs found: {len(logs)}")
        
        if not logs:
            print("No logs found in the last 30 days.")
            return

        for idx, log in enumerate(logs):
            print(f"{idx}: Type={log['type']}, Start={log['start_time']}, End={log['end_time']}")

        naps = [l for l in logs if l['type'] == 'nap' and l.get('end_time')]
        night_sleeps = [l for l in logs if l['type'] == 'night_sleep' and l.get('end_time')]
        
        print(f"Naps with end_time: {len(naps)}")
        print(f"Night sleeps with end_time: {len(night_sleeps)}")

        def calculate_avg_test(records):
            if not records: return "No records"
            try:
                total_duration = 0
                for r in records:
                    s_str = r['start_time'].replace('Z', '')
                    e_str = r['end_time'].replace('Z', '')
                    # Handle possible space instead of T
                    if ' ' in s_str and 'T' not in s_str: s_str = s_str.replace(' ', 'T')
                    if ' ' in e_str and 'T' not in e_str: e_str = e_str.replace(' ', 'T')
                    
                    start_utc = datetime.fromisoformat(s_str)
                    end_utc = datetime.fromisoformat(e_str)
                    duration = (end_utc - start_utc).total_seconds() / 60
                    total_duration += duration
                return f"Avg Duration: {total_duration / len(records):.1f} min"
            except Exception as e:
                return f"Error in calculation: {e}"

        print(f"Nap Analysis: {calculate_avg_test(naps)}")
        print(f"Night Analysis: {calculate_avg_test(night_sleeps)}")

    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    debug_analyze_sleep()
