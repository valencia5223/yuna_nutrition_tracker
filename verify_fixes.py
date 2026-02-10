import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:5000"

def test_settings_endpoints():
    print("\n[TEST] Settings Endpoints")
    
    # 1. Test POST /api/settings (Gemini API Key)
    new_key = f"test_key_{uuid.uuid4()}"
    print(f"  > Setting Gemini API Key to: {new_key}")
    try:
        res = requests.post(f"{BASE_URL}/api/settings", json={"gemini_api_key": new_key})
        print(f"  > POST Response: {res.status_code} {res.json()}")
        if res.status_code != 200:
            print("  [FAIL] POST /api/settings failed")
            return
    except Exception as e:
        print(f"  [FAIL] POST /api/settings error: {e}")
        return

    # 2. Test GET /api/settings
    print("  > Retrieving Settings...")
    try:
        res = requests.get(f"{BASE_URL}/api/settings")
        data = res.json()
        print(f"  > GET Response: {data}")
        if data.get("gemini_api_key") == new_key:
             print("  [PASS] API Key persistence verified.")
        else:
             print(f"  [FAIL] API Key mismatch. Expected {new_key}, got {data.get('gemini_api_key')}")
    except Exception as e:
        print(f"  [FAIL] GET /api/settings error: {e}")

def test_inventory_settings():
    print("\n[TEST] Inventory Settings")
    
    # 1. Test POST /api/inventory/settings
    day_count = 50
    night_count = 30
    print(f"  > Setting Diaper Packs: Day={day_count}, Night={night_count}")
    try:
        res = requests.post(f"{BASE_URL}/api/inventory/settings", json={
            "diaper_day_pack": day_count,
            "diaper_night_pack": night_count
        })
        print(f"  > POST Response: {res.status_code} {res.json()}")
        if res.status_code != 200:
             print("  [FAIL] POST /api/inventory/settings failed")
             return
    except Exception as e:
        print(f"  [FAIL] POST /api/inventory/settings error: {e}")
        return

    # 2. Verify via GET /api/settings
    print("  > Verifying via GET /api/settings...")
    try:
        res = requests.get(f"{BASE_URL}/api/settings")
        data = res.json()
        pack_sizes = data.get("diaper_pack_sizes", {})
        print(f"  > Retrieved Pack Sizes: {pack_sizes}")
        
        if pack_sizes.get("diaper_day") == day_count and pack_sizes.get("diaper_night") == night_count:
            print("  [PASS] Diaper persistence verified.")
        else:
            print("  [FAIL] Diaper pack size mismatch.")
    except Exception as e:
         print(f"  [FAIL] Verification error: {e}")

def test_growth_prediction_endpoint():
    print("\n[TEST] Growth Prediction Endpoint")
    try:
        res = requests.get(f"{BASE_URL}/api/growth/predict")
        print(f"  > GET Response Code: {res.status_code}")
        data = res.json()
        if data.get("status") == "success" and "predictions" in data:
            print(f"  [PASS] Growth prediction data retrieved. Count: {len(data['predictions'])}")
        else:
             print(f"  [WARN] Growth prediction returned: {data}")
    except Exception as e:
        print(f"  [FAIL] /api/growth/predict error: {e}")

if __name__ == "__main__":
    print("Starting Verification...")
    test_settings_endpoints()
    test_inventory_settings()
    test_growth_prediction_endpoint()
