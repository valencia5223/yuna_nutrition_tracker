from flask import Flask, render_template, request, jsonify
from flask_compress import Compress
import json
import os
from datetime import datetime, timedelta
import uuid
import socket
import random
from supabase import create_client, Client
import google.generativeai as genai
import base64
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
Compress(app)  # Gzip 압축 활성화

# === 서버 캐싱 시스템 (TTL 30초) ===
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 30  # 초

def cache_get(key):
    with _cache_lock:
        if key in _cache:
            data, ts = _cache[key]
            if time.time() - ts < CACHE_TTL:
                return data
            del _cache[key]
    return None

def cache_set(key, data):
    with _cache_lock:
        _cache[key] = (data, time.time())

def cache_invalidate(*keys):
    with _cache_lock:
        if keys:
            for k in keys:
                _cache.pop(k, None)
        else:
            _cache.clear()

# Supabase 설정 (환경 변수 우선, 없으면 사용자 제공값 사용)
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://aiqodlsxkckvwxeyvgne.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_ClJY0IvWS-mPhw0FaPhxSg_w3x7fbA4')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gemini API 초기 설정 함수
def configure_gemini(api_key):
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
configure_gemini(GEMINI_API_KEY)

# 로컬 백업용 데이터 파일 경로
DATA_FILE = 'data.json'

# 음식 영양 정보 데이터베이스 (1인분 평균 기준)
# 영양 데이터베이스 보강 (100g 또는 1회 제공량 기준 대략적 수치)
FOOD_NUTRITION_DATA = {
    # 이유식 기초 및 채소류
    "쌀미음": {"calories": 45, "carbs": 10, "protein": 0.8, "fat": 0.1},
    "찹쌀미음": {"calories": 50, "carbs": 11, "protein": 0.9, "fat": 0.1},
    "청경채": {"calories": 15, "carbs": 2.5, "protein": 1.5, "fat": 0.2},
    "애호박": {"calories": 20, "carbs": 4.5, "protein": 1.1, "fat": 0.2},
    "감자": {"calories": 75, "carbs": 17, "protein": 2, "fat": 0.1},
    "고구마": {"calories": 130, "carbs": 32, "protein": 1.5, "fat": 0.2},
    "브로콜리": {"calories": 35, "carbs": 7, "protein": 2.8, "fat": 0.4},
    "양배추": {"calories": 25, "carbs": 6, "protein": 1.3, "fat": 0.1},
    "단호박": {"calories": 50, "carbs": 12, "protein": 1.5, "fat": 0.3},
    "시금치": {"calories": 23, "carbs": 3.6, "protein": 2.9, "fat": 0.4},
    
    # 단백질 및 고기류
    "소고기": {"calories": 150, "carbs": 0, "protein": 24, "fat": 6}, # 100g 기준 평균
    "닭고기": {"calories": 110, "carbs": 0, "protein": 23, "fat": 1.5},
    "대구살": {"calories": 80, "carbs": 0, "protein": 18, "fat": 0.7},
    "전복": {"calories": 90, "carbs": 4, "protein": 15, "fat": 0.8},
    "계란": {"calories": 155, "carbs": 1.1, "protein": 13, "fat": 11},
    "두부": {"calories": 80, "carbs": 2, "protein": 8, "fat": 4.5},
    "새우": {"calories": 99, "carbs": 0.2, "protein": 24, "fat": 0.3},
    "멸치": {"calories": 114, "carbs": 0, "protein": 25, "fat": 1.6},
    "생선": {"calories": 150, "carbs": 0, "protein": 20, "fat": 8},
    
    # 죽 및 진밥류
    "소고기죽": {"calories": 90, "carbs": 15, "protein": 4, "fat": 1.5},
    "닭고기죽": {"calories": 85, "carbs": 14, "protein": 4.5, "fat": 1.2},
    "야채죽": {"calories": 70, "carbs": 16, "protein": 1.5, "fat": 0.5},
    "진밥": {"calories": 120, "carbs": 25, "protein": 2.5, "fat": 0.3},
    
    # 유아식 메뉴 (100g 기준 추정치)
    "볶음밥": {"calories": 150, "carbs": 25, "protein": 5, "fat": 3},
    "짜장밥": {"calories": 160, "carbs": 28, "protein": 6, "fat": 3.5},
    "카레라이스": {"calories": 160, "carbs": 28, "protein": 6, "fat": 3.5},
    "불고기": {"calories": 120, "carbs": 5, "protein": 15, "fat": 6},
    "카레": {"calories": 80, "carbs": 12, "protein": 4, "fat": 2},
    "된장국": {"calories": 30, "carbs": 3, "protein": 2, "fat": 1},
    "미역국": {"calories": 35, "carbs": 1, "protein": 3, "fat": 2},
    "곰탕": {"calories": 100, "carbs": 0, "protein": 10, "fat": 6},
    "오므라이스": {"calories": 170, "carbs": 22, "protein": 8, "fat": 6},
    "스테이크": {"calories": 150, "carbs": 2, "protein": 18, "fat": 8},
    
    # 면류 및 기타 탄수화물
    "짜장면": {"calories": 150, "carbs": 25, "protein": 5, "fat": 4},
    "잔치국수": {"calories": 100, "carbs": 20, "protein": 4, "fat": 1},
    "파스타": {"calories": 160, "carbs": 30, "protein": 5, "fat": 2},
    "스파게티": {"calories": 160, "carbs": 30, "protein": 5, "fat": 2},
    "우동": {"calories": 110, "carbs": 22, "protein": 3, "fat": 1},
    "칼국수": {"calories": 120, "carbs": 25, "protein": 4, "fat": 1},
    "식빵": {"calories": 250, "carbs": 50, "protein": 8, "fat": 4},
    "모닝롤": {"calories": 280, "carbs": 55, "protein": 7, "fat": 5},
    "면": {"calories": 140, "carbs": 28, "protein": 4, "fat": 1},
    
    # 간식 및 기타
    "사과": {"calories": 30, "carbs": 8, "protein": 0.2, "fat": 0.1},
    "배": {"calories": 35, "carbs": 9, "protein": 0.2, "fat": 0.1},
    "바나나": {"calories": 50, "carbs": 12, "protein": 0.6, "fat": 0.2},
    "요거트": {"calories": 50, "carbs": 4, "protein": 3, "fat": 2.5},
    "치즈": {"calories": 60, "carbs": 0.5, "protein": 4, "fat": 5}, # 1장 기준
    "우유": {"calories": 65, "carbs": 5, "protein": 3.3, "fat": 3.5},
    "블루베리": {"calories": 30, "carbs": 7, "protein": 0.4, "fat": 0.2},
    "퓨레": {"calories": 40, "carbs": 10, "protein": 0.3, "fat": 0.1},
    
    # 기본 식재료 (아기 1회 섭취분량 고려)
    "밥": {"calories": 150, "carbs": 33, "protein": 3, "fat": 0.5},
    "잡곡밥": {"calories": 160, "carbs": 34, "protein": 4, "fat": 1},
}

def calculate_nutrition(menu_name, months=12, amount="보통"):
    import re
    result = {"calories": 0, "carbs": 0, "protein": 0, "fat": 0}
    
    # 중량 정보 추출 (예: 100g, 50그람, 50그램 등)
    weight_match = re.search(r'(\d+)\s*(g|그람|그램)', menu_name)
    input_weight = None
    if weight_match:
        input_weight = float(weight_match.group(1))
    
    # 섭취량 보정 계수
    if input_weight is not None:
        amount_multiplier = input_weight / 100.0
    else:
        amount_multiplier = {"조금": 0.6, "보통": 1.0, "많이": 1.4}.get(amount, 1.0)
    
    # 개월수별 성장 단계 가중치
    if months < 7: stage_multiplier = 0.4
    elif months < 10: stage_multiplier = 0.5
    elif months < 13: stage_multiplier = 0.6
    elif months < 24: stage_multiplier = 0.7
    else: stage_multiplier = 0.8
    
    if input_weight is not None:
        stage_multiplier = 1.0
    
    # 중량 텍스트 제거하고 분석
    clean_menu = menu_name
    if weight_match:
        clean_menu = clean_menu.replace(weight_match.group(0), "")
    
    found_keys = []
    # 데이터베이스의 모든 키에 대해 매칭 시도
    for key in FOOD_NUTRITION_DATA.keys():
        if key in clean_menu:
            found_keys.append(key)
    
    # 중복 매칭 제거 (예: '소고기죽'이 매칭되면 '소고기'는 제외)
    # 긴 단어 우선 매칭 로직
    found_keys.sort(key=len, reverse=True)
    final_keys = []
    for i, key in enumerate(found_keys):
        is_sub = False
        for longer_key in found_keys[:i]:
            if key in longer_key:
                is_sub = True
                break
        if not is_sub:
            final_keys.append(key)
    
    if final_keys:
        for key in final_keys:
            value = FOOD_NUTRITION_DATA[key]
            result["calories"] += value["calories"]
            result["carbs"] += value["carbs"]
            result["protein"] += value["protein"]
            result["fat"] += value["fat"]
    else:
        # 데이터가 없는 경우 기본값 (현실적인 한 끼 권장량)
        result = {"calories": 120, "carbs": 20, "protein": 6, "fat": 3}
    
    # 최종 보정
    for key in result:
        result[key] = round(result[key] * stage_multiplier * amount_multiplier, 1)
        
    return result

def calculate_months(birth_date_str):
    """생년월일을 기준으로 현재 개월수를 계산합니다."""
    if not birth_date_str:
        return 12
    try:
        # birth_date_str이 'YYYY-MM-DD' 형식이라고 가정
        birth_date = datetime.strptime(birth_date_str.split('T')[0], '%Y-%m-%d')
        today = datetime.now()
        months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
        # 일(day)이 생일보다 전이면 1개월 뺌
        if today.day < birth_date.day:
            months -= 1
        return max(0, months)
    except Exception as e:
        print(f"개월수 계산 에러: {e}")
        return 12

def load_data():
    """Supabase에서 데이터를 불러오고, 필요 시 로컬 데이터를 마이그레이션합니다.
    캐싱 + 병렬 쿼리로 최적화."""
    # 캐시 확인
    cached = cache_get('load_data')
    if cached:
        return cached
    
    try:
        # 병렬 쿼리로 모든 테이블 동시 조회
        results = {}
        def fetch_user():
            return supabase.table('user_profile').select('*').eq('id', '00000000-0000-0000-0000-000000000000').execute()
        def fetch_meals():
            return supabase.table('meals').select('*').order('date', desc=True).execute()
        def fetch_growth():
            return supabase.table('growth').select('*').order('date', desc=True).execute()
        def fetch_settings():
            try:
                return supabase.table('settings').select('*').limit(1).execute()
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_user = executor.submit(fetch_user)
            future_meals = executor.submit(fetch_meals)
            future_growth = executor.submit(fetch_growth)
            future_settings = executor.submit(fetch_settings)
            
            user_res = future_user.result(timeout=10)
            meals_res = future_meals.result(timeout=10)
            growth_res = future_growth.result(timeout=10)
            settings_res = future_settings.result(timeout=10)
        
        # 만약 DB가 비어있고 로컬 파일이 있다면 마이그레이션 수행
        if not user_res.data and os.path.exists(DATA_FILE):
            return migrate_local_to_supabase()
        
        user_info = user_res.data[0] if user_res.data else {
            "name": "차유나", "months": 12, "likes": [], "dislikes": [], 
            "birth_date": "2024-07-19", "gender": "여아",
            "target_nutrition": {"calories": 1000, "carbs": 130, "protein": 25, "fat": 30}
        }
        
        # 개월수 자동 계산 적용
        user_info['months'] = calculate_months(user_info.get('birth_date'))
        
        # 데이터 정규화(camelCase -> snake_case) 보장
        normalized_meals = []
        for meal in (meals_res.data or []):
            normalized_meals.append({
                "id": meal.get('id'),
                "date": str(meal.get('date')),
                "meal_type": meal.get('meal_type') or meal.get('mealType') or "간식",
                "menu_name": meal.get('menu_name') or meal.get('menuName') or "기록 없음",
                "amount": meal.get('amount') or "보통",
                "calories": float(meal.get('calories') or 0),
                "carbs": float(meal.get('carbs') or 0),
                "protein": float(meal.get('protein') or 0),
                "fat": float(meal.get('fat') or 0)
            })

        # 설정 정보
        db_settings = {}
        if settings_res and settings_res.data:
            db_settings = settings_res.data[0]
            # JSONB 내부의 접종 데이터를 최상위로 노출 (프론트엔드 호환성)
            diaper_settings = db_settings.get('diaper_pack_sizes', {})
            if isinstance(diaper_settings, dict) and 'completed_vaccinations' in diaper_settings:
                db_settings['completed_vaccinations'] = diaper_settings['completed_vaccinations']
        else:
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, 'r', encoding='utf-8') as f:
                        local_data = json.load(f)
                        db_settings = local_data.get('settings', {})
                except:
                    pass
        
        # 만약 DB에 API 키가 있다면 환경 변수보다 우선 적용
        global GEMINI_API_KEY
        db_api_key = db_settings.get('gemini_api_key')
        if db_api_key:
            GEMINI_API_KEY = db_api_key
            configure_gemini(GEMINI_API_KEY)

        result = {
            "user": user_info,
            "meals": normalized_meals,
            "growth": growth_res.data or [],
            "settings": db_settings
        }
        
        # 캐시에 저장
        cache_set('load_data', result)
        return result
    except Exception as e:
        print(f"Supabase 로드 에러: {e}")
        # 에러 발생 시 로컬 파일 fallback (개발 편의성)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                local_data = json.load(f)
                
                user_info = local_data.get('user', {})
                user_info['months'] = calculate_months(user_info.get('birth_date'))
                
                # 데이터 정규화 (camelCase -> snake_case)
                normalized_meals = []
                for m in local_data.get('meals', []):
                    normalized_meals.append({
                        "id": m.get('id'),
                        "date": m.get('date'),
                        "meal_type": m.get('meal_type') or m.get('mealType') or "간식",
                        "menu_name": m.get('menu_name') or m.get('menuName') or "기록 없음",
                        "amount": m.get('amount') or "보통",
                        "calories": float(m.get('calories') or 0),
                        "carbs": float(m.get('carbs') or 0),
                        "protein": float(m.get('protein') or 0),
                        "fat": float(m.get('fat') or 0)
                    })
                return {
                    "user": user_info,
                    "meals": normalized_meals,
                    "growth": local_data.get('growth', []),
                    "settings": local_data.get('settings', {})
                }
        return {"user": {}, "meals": [], "growth": []}

def migrate_local_to_supabase():
    """로컬 json 데이터를 Supabase 클라우드로 이전합니다."""
    print("🚀 로컬 데이터를 Supabase로 마이그레이션 시작...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        local_data = json.load(f)
    
    # 사용자 프로필 이전
    user = local_data.get('user', {})
    supabase.table('user_profile').upsert({
        "id": "00000000-0000-0000-0000-000000000000",
        "name": user.get('name', '차유나'),
        "birth_date": user.get('birth_date', '2024-07-19'),
        "likes": user.get('likes', []),
        "dislikes": user.get('dislikes', []),
        "target_nutrition": user.get('target_nutrition', {}),
        "gender": user.get('gender', '여아')
    }).execute()
    
    # 식단 데이터 이전 (컬럼명 동기화)
    meals = local_data.get('meals', [])
    if meals:
        normalized_meals = []
        for m in meals:
            normalized_meals.append({
                "id": m.get('id') or str(uuid.uuid4()),
                "date": m.get('date'),
                "meal_type": m.get('meal_type') or m.get('mealType'),
                "menu_name": m.get('menu_name') or m.get('menuName'),
                "amount": m.get('amount') or "보통", # Stores preference value
                "calories": m.get('calories'),
                "carbs": m.get('carbs'),
                "protein": m.get('protein'),
                "fat": m.get('fat')
            })
        supabase.table('meals').upsert(normalized_meals).execute()
        
    # 성장 데이터 이전
    growth = local_data.get('growth', [])
    if growth:
        supabase.table('growth').upsert(growth).execute()
        
    print("✅ 마이그레이션 완료!")
    # 마이그레이션 후 로드된 형태(정규화된 형태)로 다시 가져오기
    return load_data()

def save_data(data):
    """Supabase를 주 저장소로 사용하므로 로컬 저장은 백업용으로만 유지합니다."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"로컬 백업 실패: {e}")

# 한국 여아 성장 표준 데이터 (2017 소아청소년 성장도표 50백분위수)
# {개월수: [평균키, 평균몸무게]}
GIRLS_GROWTH_STANDARD = {
    0: [49.1, 3.3], 1: [53.7, 4.3], 2: [57.1, 5.2], 3: [59.8, 5.9], 
    4: [62.1, 6.5], 5: [64.0, 7.0], 6: [65.7, 7.4], 7: [67.3, 7.8], 
    8: [68.7, 8.1], 9: [70.1, 8.4], 10: [71.5, 8.7], 11: [72.8, 8.9], 
    12: [74.0, 9.1], 13: [75.2, 9.4], 14: [76.4, 9.6], 15: [77.5, 9.8], 
    16: [78.6, 10.0], 17: [79.7, 10.2], 18: [80.7, 10.4], 19: [81.7, 10.5], 
    20: [82.7, 10.7], 21: [83.7, 10.9], 22: [84.6, 11.1], 23: [85.5, 11.2], 
    24: [86.4, 11.4], 30: [91.3, 12.7], 36: [95.4, 13.9],
    48: [103.3, 16.9], 60: [109.9, 19.3], 72: [116.3, 21.9],
    84: [122.5, 24.9], 96: [128.2, 28.3], 108: [133.7, 32.5],
    120: [139.1, 37.3], 132: [145.4, 42.9], 144: [151.7, 48.7],
    156: [155.6, 52.4], 168: [157.7, 54.3], 180: [158.5, 55.0],
    192: [158.8, 55.4], 204: [159.0, 55.6], 216: [159.0, 55.6]
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    """통합 API - 모든 데이터 + 성장 예측을 한번에 반환"""
    data = load_data()
    
    # 성장 예측도 함께 포함 (별도 API 호출 불필요)
    growth_prediction = None
    try:
        growth_list = data.get('growth', [])
        if growth_list:
            # 캐시 확인
            cached_pred = cache_get('growth_prediction')
            if cached_pred:
                growth_prediction = cached_pred
            else:
                last = growth_list[0]  # desc 정렬이므로 첫번째가 최신
                h_percentile = last.get('h_percentile', 50)
                w_percentile = last.get('w_percentile', 50)
                
                import math
                def get_value_from_percentile(percentile, avg, cv):
                    p = percentile / 100.0
                    if p <= 0: return avg * (1 - 3*cv)
                    if p >= 1: return avg * (1 + 3*cv)
                    c0, c1, c2 = 2.515517, 0.802853, 0.010328
                    d1, d2, d3 = 1.432788, 0.189269, 0.001308
                    t = math.sqrt(-2 * math.log(min(p, 1-p)))
                    z = t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1)
                    if p < 0.5: z = -z
                    return round(avg + (z * avg * cv), 1)
                
                predictions = []
                target_ages = [24, 36, 48, 60, 72, 96, 120, 144, 168, 192, 216, 240]
                for age in target_ages:
                    lookup_age = min(age, 216)
                    standard_months = sorted(GIRLS_GROWTH_STANDARD.keys())
                    closest_m = min(standard_months, key=lambda x: abs(x - lookup_age))
                    avg_h, avg_w = GIRLS_GROWTH_STANDARD[closest_m]
                    pred_h = get_value_from_percentile(h_percentile, avg_h, 0.035)
                    pred_w = get_value_from_percentile(w_percentile, avg_w, 0.11)
                    predictions.append({"age": age // 12, "months": age, "height": pred_h, "weight": pred_w})
                
                growth_prediction = {"status": "success", "predictions": predictions}
                cache_set('growth_prediction', growth_prediction)
    except Exception as e:
        print(f"인라인 성장 예측 에러: {e}")
    
    data['growth_prediction'] = growth_prediction
    return jsonify(data)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """통합 대시보드 API - 단일 호출로 모든 데이터 제공"""
    try:
        data = load_data()
        user = data.get('user', {})
        meals = data.get('meals', [])
        growth = data.get('growth', [])
        
        # 오늘 날짜 계산
        now = datetime.now()
        today = f"{now.year}-{str(now.month).zfill(2)}-{str(now.day).zfill(2)}"
        today_meals = [m for m in meals if m['date'].startswith(today)]
        
        # 영양소 합계 계산
        totals = {'carbs': 0, 'protein': 0, 'fat': 0, 'calories': 0}
        for meal in today_meals:
            totals['carbs'] += meal.get('carbs', 0)
            totals['protein'] += meal.get('protein', 0)
            totals['fat'] += meal.get('fat', 0)
            totals['calories'] += meal.get('calories', 0)
        
        # 추천 식단 생성
        months = user.get('months', 12)
        likes = user.get('likes', [])
        dislikes = user.get('dislikes', [])
        target = user.get('target_nutrition', {"calories": 1000})
        
        # 간단한 추천 로직 (기존 /api/recommend와 동일)
        recommendation = generate_recommendation(months, likes, dislikes, meals, target)
        
        # 성장 데이터 (최근 기록)
        latest_growth = growth[-1] if growth else None
        
        return jsonify({
            'user': user,
            'today_meals': today_meals,
            'nutrition_totals': totals,
            'recommendation': recommendation,
            'latest_growth': latest_growth,
            'all_meals': meals[:50],  # 최근 50개만
            'growth_history': growth[-20:] if len(growth) > 20 else growth  # 최근 20개만
        })
    except Exception as e:
        print(f"Dashboard API 에러: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_recommendation(months, likes, dislikes, meals, target):
    """추천 식단 생성 헬퍼 함수"""
    STAGE_DETAILS = {
        "early": {
            "menus": [
                {"breakfast": "쌀미음", "lunch": "청경채미음", "dinner": "애호박미음", "snack": "사과퓨레"},
                {"breakfast": "찹쌀미음", "lunch": "감자미음", "dinner": "브로콜리미음", "snack": "배퓨레"},
            ],
            "tip": "알레르기 반응을 살피며 새로운 재료를 하나씩 시작해보세요."
        },
        "middle": {
            "menus": [
                {"breakfast": "소고기 오이죽", "lunch": "닭고기 양파죽", "dinner": "대구살 무죽", "snack": "바나나 요거트"},
                {"breakfast": "연두부 채소죽", "lunch": "소고기 표고버섯죽", "dinner": "고구마 사과죽", "snack": "아기치즈"},
            ],
            "tip": "철분 보충을 위해 매끼 소고기나 닭고기를 포함하는 것이 좋아요."
        },
        "late": {
            "menus": [
                {"breakfast": "소고기 가지 진밥", "lunch": "대구살 시금치 진밥", "dinner": "닭고기 단호박 진밥", "snack": "삶은 계란"},
                {"breakfast": "전복 채소 진밥", "lunch": "계란 채소 진밥", "dinner": "소고기 브로콜리 진밥", "snack": "블루베리"},
            ],
            "tip": "핑거 푸드를 통해 스스로 먹는 즐거움을 가르쳐줄 시기예요."
        },
        "completion": {
            "menus": [
                {"breakfast": "해물 볶음밥", "lunch": "소고기 미역국 진밥", "dinner": "두부 스테이크 & 찐 채소", "snack": "찐 감자"},
                {"breakfast": "닭다리살 채소 볶음밥", "lunch": "대구전 & 시금치 무침", "dinner": "야채 치즈 오므라이스", "snack": "아기용 우유"},
            ],
            "tip": "간을 최소화하고 다양한 식감을 경험하게 해주세요."
        },
        "toddler": {
            "menus": [
                {"breakfast": "불고기 덮밥", "lunch": "곰탕 & 생선구이", "dinner": "닭안심 간장구이 & 밥", "snack": "제철 과일"},
                {"breakfast": "새우 볶음밥", "lunch": "계란국 & 계란말이", "dinner": "소고기 무국 & 두부조림", "snack": "견과류 한알"},
            ],
            "tip": "세 끼 식사와 간식의 영양 밸런스를 맞춰 성장을 도와주세요."
        }
    }
    
    if months < 7: stage = "early"
    elif months < 10: stage = "middle"
    elif months < 13: stage = "late"
    elif months < 16: stage = "completion"
    else: stage = "toddler"
    
    selected_set = random.choice(STAGE_DETAILS[stage]["menus"]).copy()
    tip = STAGE_DETAILS[stage]["tip"]
    
    # 최근 데이터 분석
    tendency_msg = "유나의 성장 단계에 딱 맞는 하루 식단을 준비했어요."
    if meals:
        try:
            last_week = datetime.now() - timedelta(days=7)
            recent_meals = []
            for m in meals:
                date_str = m['date'].replace('T', ' ').split('+')[0].split('.')[0]
                try:
                    meal_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    if meal_date > last_week:
                        recent_meals.append(m)
                except:
                    continue
            
            if recent_meals:
                total_cal = sum(float(m.get('calories', 0)) for m in recent_meals)
                avg_cal = total_cal / 7
                cal_rate = (avg_cal / target.get('calories', 1000)) * 100
                tendency_msg = f"최근 1주일간 유나는 목표 칼로리의 {cal_rate:.1f}%를 섭취 중이에요."
        except Exception as e:
            print(f"추천 분석 에러: {e}")
    
    return {
        "recommendation": selected_set,
        "tip": tip,
        "tendency": tendency_msg,
        "months": months,
        "stage_name": stage
    }

@app.route('/api/record', methods=['POST'])
def record_meal():
    meal_data = request.json
    menu_name = meal_data.get('menuName', '')
    preference = meal_data.get('preference', '보통')
    
    data = load_data()
    user_months = data['user'].get('months', 12)
    
    # 영양소가 비어있거나 0인 경우 자동 계산 시도
    calories = float(meal_data.get('calories', 0))
    carbs = float(meal_data.get('carbs', 0))
    protein = float(meal_data.get('protein', 0))
    fat = float(meal_data.get('fat', 0))
    
    status_msg = "식단이 기록되었습니다."
    if calories == 0 and carbs == 0 and protein == 0 and fat == 0:
        # 이제 UI에서 '얼마나' 항목이 삭제되었으므로 기본값은 항상 '보통'으로 계산합니다.
        auto_nutrition = calculate_nutrition(menu_name, user_months, "보통")
        calories = auto_nutrition['calories']
        carbs = auto_nutrition['carbs']
        protein = auto_nutrition['protein']
        fat = auto_nutrition['fat']
        status_msg = f"'{menu_name}'을(를) 분석하여 기록했습니다."

    new_meal = {
        "id": str(uuid.uuid4()),
        "date": datetime.utcnow().isoformat() + 'Z',
        "meal_type": meal_data.get('mealType') or meal_data.get('meal_type') or "간식",
        "menu_name": menu_name,
        "amount": preference, # UI preference value stored in DB amount column
        "calories": calories,
        "carbs": carbs,
        "protein": protein,
        "fat": fat
    }
    
    try:
        supabase.table('meals').insert(new_meal).execute()
        cache_invalidate('load_data')  # 캐시 무효화
        return jsonify({"status": "success", "message": status_msg, "record": new_meal})
    except Exception as e:
        return jsonify({"status": "error", "message": f"기록 실패: {e}"}), 500

@app.route('/api/delete', methods=['POST'])
def delete_meal():
    meal_id = request.json.get('id')
    try:
        res = supabase.table('meals').delete().eq('id', meal_id).execute()
        cache_invalidate('load_data')  # 캐시 무효화
        if res.data:
            return jsonify({"status": "success", "message": "삭제되었습니다."})
        return jsonify({"status": "error", "message": "삭제할 기록을 찾지 못했습니다."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"삭제 실패: {e}"}), 500

@app.route('/api/meals', methods=['GET'])
def get_meals():
    try:
        res = supabase.table('meals').select('*').order('date', desc=True).limit(100).execute()
        return jsonify({"status": "success", "meals": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": f"식단 조회 실패: {e}"}), 500


@app.route('/api/growth', methods=['POST'])
def record_growth():
    growth_data = request.json
    height = float(growth_data.get('height', 0))
    weight = float(growth_data.get('weight', 0))
    
    data = load_data()
    months = data['user'].get('months', 12)
    
    # 한국 여아 평균 데이터와 비교 (Z-Score 기반 백분위 추정)
    def calculate_percentile(value, avg, cv):
        if avg <= 0: return 50
        z = (value - avg) / (avg * cv)
        import math
        percentile = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100
        return round(max(1, min(99, percentile)), 1)

    standard_months = sorted(GIRLS_GROWTH_STANDARD.keys())
    closest_m = min(standard_months, key=lambda x: abs(x - months))
    avg_h, avg_w = GIRLS_GROWTH_STANDARD[closest_m]
    
    h_percentile = calculate_percentile(height, avg_h, 0.035)
    w_percentile = calculate_percentile(weight, avg_w, 0.11)
    
    status_msg = f"기록 완료! {months}개월 기준 [키: 백분위 {h_percentile} (상위 {round(100-h_percentile, 1)}%)] | [몸무게: 백분위 {w_percentile} (상위 {round(100-w_percentile, 1)}%)]"
    
    new_record = {
        "id": str(uuid.uuid4()),
        "date": datetime.utcnow().isoformat() + 'Z',
        "months": months,
        "height": height,
        "weight": weight,
        "h_percentile": h_percentile,
        "w_percentile": w_percentile
    }
    
    try:
        supabase.table('growth').insert(new_record).execute()
        cache_invalidate('load_data', 'growth_prediction')  # 캐시 무효화
        return jsonify({"status": "success", "message": status_msg, "record": new_record})
    except Exception as e:
        return jsonify({"status": "error", "message": f"성장 기록 실패: {e}"}), 500

@app.route('/api/growth/delete', methods=['POST'])
def delete_growth():
    record_id = request.json.get('id')
    try:
        res = supabase.table('growth').delete().eq('id', record_id).execute()
        cache_invalidate('load_data', 'growth_prediction')  # 캐시 무효화
        if res.data:
            return jsonify({"status": "success", "message": "성장 기록이 삭제되었습니다."})
        return jsonify({"status": "error", "message": "삭제할 기록을 찾지 못했습니다."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"성장 삭제 실패: {e}"}), 500

@app.route('/api/user/preferences', methods=['POST'])
def update_preferences():
    pref_data = request.json
    try:
        supabase.table('user_profile').update({
            "likes": pref_data.get('likes', []),
            "dislikes": pref_data.get('dislikes', [])
        }).eq('id', '00000000-0000-0000-0000-000000000000').execute()
        cache_invalidate('load_data')  # 캐시 무효화
        return jsonify({"status": "success", "message": "음식 취향이 저장되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"저장 실패: {e}"}), 500

@app.route('/api/user/update', methods=['POST'])
def update_user():
    # 개월수는 자동 계산되므로 이 API는 사실상 birth_date 등을 수정할 때 사용하도록 확장 가능
    # 현재는 호환성을 위해 유지하거나 메시지만 반환
    return jsonify({"status": "success", "message": "사용자 정보는 자동 계산 방식으로 관리됩니다."})

@app.route('/api/growth/history', methods=['GET'])
def get_growth_history():
    try:
        res = supabase.table('growth').select('*').order('date', desc=False).execute()
        return jsonify({"status": "success", "history": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/growth/predict', methods=['GET'])
def predict_growth():
    try:
        # 최신 성장 데이터 가져오기
        res = supabase.table('growth').select('*').order('date', desc=True).limit(1).execute()
        if not res.data:
            return jsonify({"status": "error", "message": "성장 기록이 없습니다."}), 404
        
        last = res.data[0]
        h_percentile = last.get('h_percentile', 50)
        w_percentile = last.get('w_percentile', 50)
        
        predictions = []
        # 예측할 나이 (개월수): 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20세
        target_ages = [24, 36, 48, 60, 72, 96, 120, 144, 168, 192, 216, 240]
        
        # Z-Score 역계산 함수
        import math
        def get_value_from_percentile(percentile, avg, cv):
            # 정규분포 역함수 근사 (Peter John Acklam's algorithm or simple rational approximation)
            # scipy.stats.norm.ppf(p) 대체
            p = percentile / 100.0
            if p <= 0: return avg * (1 - 3*cv) # 하한선
            if p >= 1: return avg * (1 + 3*cv) # 상한선
            
            # Rational approximation for inverse normal standard deviation
            # Coefficients
            c0 = 2.515517
            c1 = 0.802853
            c2 = 0.010328
            d1 = 1.432788
            d2 = 0.189269
            d3 = 0.001308
            
            t = math.sqrt(-2 * math.log(min(p, 1-p)))
            z = t - ((c2 * t + c1) * t + c0) / (((d3 * t + d2) * t + d1) * t + 1)
            
            if p < 0.5:
                z = -z
                
            return round(avg + (z * avg * cv), 1)

        for age in target_ages:
            # 216개월(18세) 이후는 18세 데이터 사용
            lookup_age = min(age, 216)
            standard_months = sorted(GIRLS_GROWTH_STANDARD.keys())
            closest_m = min(standard_months, key=lambda x: abs(x - lookup_age))
            avg_h, avg_w = GIRLS_GROWTH_STANDARD[closest_m]
            
            # 예측값 계산 (현재 백분위 유지 가정)
            # calculate_percentile에서 사용한 CV(변동계수)와 동일하게 적용
            pred_h = get_value_from_percentile(h_percentile, avg_h, 0.035)
            pred_w = get_value_from_percentile(w_percentile, avg_w, 0.11)
            
            predictions.append({
                "age": age // 12,
                "months": age,
                "height": pred_h,
                "weight": pred_w
            })
            
        return jsonify({"status": "success", "predictions": predictions})
    except Exception as e:
        print(f"예측 에러: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- AI 분석 및 설정 API ---

@app.route('/api/analyze-meal', methods=['POST'])
def analyze_meal():
    try:
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "이미지 파일이 없습니다."}), 400
        
        image_file = request.files['image']
        image_data = image_file.read()
        
        # Gemini 모델 설정
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 프롬프트 구성
        prompt = """
        이 사진은 아기가 먹을 이유식이나 유아식입니다. 
        이 음식의 메뉴 이름(menu)과 대략적인 중량(weight, g단위)을 추정해서 JSON 형식으로 알려주세요.
        이유는 간단히 한국어로 설명해주세요(reason).
        
        JSON 포맷:
        {
            "menu": "메뉴이름",
            "weight": 100,
            "reason": "이유 설명"
        }
        """
        
        parts = [
            {"mime_type": "image/jpeg", "data": image_data},
            {"text": prompt}
        ]
        
        response = model.generate_content(parts)
        result_text = response.text
        
        # JSON 파싱 (코드 블록 제거)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
            
        result_json = json.loads(result_text)
        
        return jsonify({
            "status": "success",
            "menu": result_json.get("menu", "알 수 없음"),
            "weight": result_json.get("weight", 0),
            "reason": result_json.get("reason", "")
        })
        
    except Exception as e:
        print(f"Gemini 분석 에러: {e}")
        return jsonify({"status": "error", "message": f"분석 실패: {str(e)}"}), 500

    try:
        if 'image' not in request.files:
            return jsonify({"status": "error", "message": "이미지 파일이 없습니다."}), 400
        
        image_file = request.files['image']
        image_data = image_file.read()
        
        # Gemini 모델 설정 (Vision 모델 사용)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = """
        이 사진 속 음식이 무엇인지 분석하고, 아이(유아)가 먹을 만한 양으로 대략적인 중량(g)을 예측해줘.
        형식은 반드시 JSON으로만 답변해줘.
        {
          "menu": "음식 이름 (예: 소고기 짜장면)",
          "weight": "숫자만 (예: 150)",
          "reason": "예측 이유 간략히"
        }
        """
        
        # 이미지 전송 및 분석
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        
        # JSON 응답 파싱
        try:
            # AI 응답에서 JSON 블록 추출
            content = response.text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(content)
            return jsonify({
                "status": "success",
                "analysis": analysis
            })
        except Exception as e:
            print(f"JSON 파싱 실패: {e}")
            return jsonify({"status": "error", "message": "AI 응답을 분석할 수 없습니다."}), 500
            
    except Exception as e:
        print(f"이미지 분석 실패: {e}")
        return jsonify({"status": "error", "message": f"분석 중 오류 발생: {e}"}), 500

# --- 생활 기록 (기저귀/수면/재고) API ---

@app.route('/api/diaper', methods=['POST'])
def record_diaper():
    data = request.json
    # data: { type: 'pee'|'poop'|'both', diaperType: 'day'|'night', date: '...' }
    
    new_record = {
        "id": str(uuid.uuid4()),
        "date": data.get('date') or datetime.utcnow().isoformat() + 'Z',
        "type": data.get('type'),
        "diaper_type": data.get('diaperType', 'day'),
        "memo": data.get('memo', '')
    }
    
    try:
        # 1. 기저귀 기록 저장
        supabase.table('diaper_logs').insert(new_record).execute()
        
        # 2. 재고 차감 (자동)
        inventory_key = f"diaper_{new_record['diaper_type']}"
        
        # 현재 재고 확인
        inv_res = supabase.table('inventory').select('*').eq('item_key', inventory_key).execute()
        current_qty = 0
        
        if inv_res.data:
            current_qty = inv_res.data[0]['quantity']
            # 재고 차감 업데이트
            supabase.table('inventory').update({"quantity": max(0, current_qty - 1)}).eq('item_key', inventory_key).execute()
        else:
            # 재고 데이터가 없으면 초기화 (0에서 -1은 안되니 0 유지 혹은 초기값 설정 필요. 여기선 생성 안함)
            pass
            
        return jsonify({"status": "success", "message": "기저귀 기록 및 재고 차감 완료", "record": new_record})
    except Exception as e:
        return jsonify({"status": "error", "message": f"기록 실패: {e}"}), 500

@app.route('/api/diaper', methods=['GET'])
def get_diaper_logs():
    try:
        # 최근 100개만 조회 (필요시 날짜 필터링 추가 가능)
        res = supabase.table('diaper_logs').select('*').order('date', desc=True).limit(100).execute()
        return jsonify({"status": "success", "logs": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/diaper/delete', methods=['POST'])
def delete_diaper():
    record_id = request.json.get('id')
    try:
        # 1. 삭제할 기록 조회 (재고 복원을 위해)
        record_res = supabase.table('diaper_logs').select('*').eq('id', record_id).execute()
        
        if not record_res.data:
            return jsonify({"status": "error", "message": "삭제할 기록을 찾을 수 없습니다."}), 404
        
        deleted_record = record_res.data[0]
        diaper_type = deleted_record.get('diaper_type', 'day')
        
        # 2. 기록 삭제
        supabase.table('diaper_logs').delete().eq('id', record_id).execute()
        
        # 3. 재고 복원 (삭제된 기록의 타입에 맞춰 +1)
        inventory_key = f"diaper_{diaper_type}"
        inv_res = supabase.table('inventory').select('*').eq('item_key', inventory_key).execute()
        
        if inv_res.data:
            current_qty = inv_res.data[0]['quantity']
            supabase.table('inventory').update({"quantity": current_qty + 1}).eq('item_key', inventory_key).execute()
        
        cache_invalidate('load_data')  # 캐시 무효화
        return jsonify({"status": "success", "message": "삭제되었습니다. (재고 +1 복원)"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/quick/diaper/<type>', methods=['GET'])
def quick_record_diaper_legacy(type):
    """기존 단축어 호환용 (기본값: 낮 기저귀)"""
    return quick_record_diaper_detail('day', type)

@app.route('/quick/diaper/<dtype>/<atype>', methods=['GET'])
def quick_record_diaper_detail(dtype, atype):
    """URL 접속만으로 기저귀 기록 (GET 요청) - 바로가기 버튼용
    dtype: day, night
    atype: pee, poop
    """
    if dtype not in ['day', 'night'] or atype not in ['pee', 'poop']:
        return "잘못된 요청입니다. (예: /quick/diaper/day/poop)", 400
    
    try:
        # 시간 설정 (현재 시간)
        now_iso = datetime.utcnow().isoformat() + 'Z'
        
        # 1. 기록 저장
        new_record = {
            "id": str(uuid.uuid4()),
            "date": now_iso,
            "type": atype,
            "diaper_type": dtype, 
            "memo": "퀵 바로가기 기록"
        }
        supabase.table('diaper_logs').insert(new_record).execute()
        
        # 2. 재고 차감 (선택된 기저귀 타입 기준)
        inventory_key = f"diaper_{dtype}"
        inv_res = supabase.table('inventory').select('*').eq('item_key', inventory_key).execute()
        if inv_res.data:
            current_qty = inv_res.data[0]['quantity']
            supabase.table('inventory').update({"quantity": max(0, current_qty - 1)}).eq('item_key', inventory_key).execute()
            
        cache_invalidate('load_data')
        
        # 3. 사용자 피드백 페이지 (자동 리다이렉트)
        type_kr = "소변" if atype == "pee" else "대변"
        dtype_kr = "낮" if dtype == "day" else "밤"
        
        bg_color = '#e1f5fe' if atype == 'pee' else '#fff3e0'
        if dtype == 'night':
            bg_color = '#e8eaf6' if atype == 'pee' else '#efebe9' # 밤일 때 조금 더 어둡거나 다른 톤
            
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{dtype_kr} 기저귀 {type_kr} 기록!</title>
            <style>
                body {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    background: {bg_color};
                    font-family: sans-serif;
                    text-align: center;
                }}
                .icon {{ font-size: 5rem; margin-bottom: 20px; animation: pop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
                h1 {{ color: #333; margin-bottom: 10px; }}
                p {{ color: #666; }}
                @keyframes pop {{ from {{ transform: scale(0); }} to {{ transform: scale(1); }} }}
            </style>
            <script>
                setTimeout(function() {{
                    window.location.href = '/';
                }}, 1500); // 1.5초 후 메인으로 이동
            </script>
        </head>
        <body>
            <div class="icon">{'💧' if atype == 'pee' else '💩'}</div>
            <h1>{dtype_kr} 기저귀 {type_kr} 기록!</h1>
            <p>잠시 후 메인 화면으로 이동합니다...</p>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"기록 실패: {e}", 500

@app.route('/api/sleep', methods=['POST'])
def record_sleep():
    data = request.json
    # data: { action: 'start'|'end', type: 'nap'|'night_sleep', time: '...' }
    
    try:
        if data['action'] == 'start':
            # 수면 시작: 새로운 레코드 생성 (end_time is null)
            new_record = {
                "id": str(uuid.uuid4()),
                "start_time": data.get('time') or datetime.utcnow().isoformat() + 'Z',
                "type": data.get('type'),
                "memo": data.get('memo', '')
            }
            supabase.table('sleep_logs').insert(new_record).execute()
            return jsonify({"status": "success", "message": "수면 시작 기록", "record": new_record})
            
        elif data['action'] == 'end':
            # 수면 종료: 가장 최근의 진행중인(end_time이 없는) 해당 타입 수면을 찾아 업데이트
            # 진행중인 수면 찾기
            res = supabase.table('sleep_logs').select('*')\
                .is_('end_time', 'null')\
                .eq('type', data.get('type'))\
                .order('start_time', desc=True)\
                .limit(1).execute()
                
            if res.data:
                record_id = res.data[0]['id']
                end_time = data.get('time') or datetime.utcnow().isoformat() + 'Z'
                supabase.table('sleep_logs').update({"end_time": end_time}).eq('id', record_id).execute()
                return jsonify({"status": "success", "message": "수면 종료 기록"})
            else:
                return jsonify({"status": "error", "message": "진행 중인 수면 기록을 찾을 수 없습니다."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"수면 기록 실패: {e}"}), 500

@app.route('/api/sleep', methods=['GET'])
def get_sleep_logs():
    try:
        res = supabase.table('sleep_logs').select('*').order('start_time', desc=True).limit(50).execute()
        return jsonify({"status": "success", "logs": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/vaccinations/toggle', methods=['POST'])
def toggle_vaccination():
    vaccine_title = request.json.get('title')
    if not vaccine_title:
        return jsonify({"status": "error", "message": "제목이 없습니다."}), 400
    
    try:
        # 현재 설정 가져오기
        res = supabase.table('settings').select('*').limit(1).execute()
        if not res.data:
            # 설정이 없으면 생성
            new_settings = {
                "id": str(uuid.uuid4()),
                "completed_vaccinations": [vaccine_title]
            }
            supabase.table('settings').insert(new_settings).execute()
            return jsonify({"status": "success", "completed": True})
        
        settings = res.data[0]
        # 별도 컬럼 대신 기존 JSONB 필드(diaper_pack_sizes)를 설정 저장소로 활용
        diaper_settings = settings.get('diaper_pack_sizes', {})
        if not isinstance(diaper_settings, dict):
            diaper_settings = {}
            
        completed = diaper_settings.get('completed_vaccinations', [])
        
        if vaccine_title in completed:
            completed.remove(vaccine_title)
            is_completed = False
        else:
            completed.append(vaccine_title)
            is_completed = True
            
        diaper_settings['completed_vaccinations'] = completed
        supabase.table('settings').update({"diaper_pack_sizes": diaper_settings}).eq('id', settings['id']).execute()
        cache_invalidate('load_data') # 캐시 갱신
        
        return jsonify({"status": "success", "completed": is_completed})
    except Exception as e:
        print(f"Vaccination toggle 에러: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sleep/analysis', methods=['GET'])
def analyze_sleep():
    try:
        # 최근 30일 데이터 조회 (데이터 부족 문제를 해결하기 위해 분석 기간 확장)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        
        # Debug: Log query params
        with open('sleep_debug.txt', 'w', encoding='utf-8') as f:
            f.write(f"Querying from: {thirty_days_ago}\n")

        res = supabase.table('sleep_logs').select('*')\
            .gte('start_time', thirty_days_ago)\
            .order('start_time', desc=True).execute()
        
        logs = res.data
        
        # Debug: Log results
        with open('sleep_debug.txt', 'a', encoding='utf-8') as f:
            f.write(f"Logs retrieval status: {len(logs) if logs else 0} records found.\n")
            if logs:
                for log in logs:
                    f.write(f"LOG: {log}\n")

        if not logs:
            return jsonify({"status": "success", "analysis": None})

        # 데이터 분류
        naps = [l for l in logs if l['type'] == 'nap' and l.get('end_time')]
        night_sleeps = [l for l in logs if l['type'] == 'night_sleep' and l.get('end_time')]

        def calculate_avg(records):
            if not records: return None
            total_duration = 0
            start_hour_minutes = []
            end_hour_minutes = []
            
            for r in records:
                try:
                    # '2026-02-12T12:36:31.999+00:00' 또는 '2026-02-12 12:36:31' 등 다양한 형식 대응
                    s_str = r['start_time'].replace('Z', '').replace(' ', 'T')
                    e_str = r['end_time'].replace('Z', '').replace(' ', 'T')
                    
                    # 오프셋(+00:00 등) 제거하여 순수 시간만 추출 (UTC 기준이므로)
                    s_str = s_str.split('+')[0].split('-')
                    # 위 방식은 날짜의 -와 겹칠 수 있으므로 정교하게:
                    s_base = r['start_time'].split('.')[0].replace('T', ' ').replace('Z', '')
                    e_base = r['end_time'].split('.')[0].replace('T', ' ').replace('Z', '')
                    
                    start_utc = datetime.strptime(s_base[:19], '%Y-%m-%d %H:%M:%S')
                    end_utc = datetime.strptime(e_base[:19], '%Y-%m-%d %H:%M:%S')
                    
                    # Duration (minutes)
                    duration = (end_utc - start_utc).total_seconds() / 60
                    if duration <= 0: continue 
                    total_duration += duration
                    
                    # KST 변환 (UTC + 9)
                    start_kst = start_utc + timedelta(hours=9)
                    end_kst = end_utc + timedelta(hours=9)
                    
                    start_mins = start_kst.hour * 60 + start_kst.minute
                    start_hour_minutes.append(start_mins)
                    
                    end_mins = end_kst.hour * 60 + end_kst.minute
                    if end_mins < start_mins:
                        end_mins += 1440
                    end_hour_minutes.append(end_mins)
                except Exception as ex:
                    print(f"Record parsing error: {ex}")
                    continue
            
            if not start_hour_minutes: return None
            
            count = len(start_hour_minutes)
            avg_duration = total_duration / count
            avg_start_mins = sum(start_hour_minutes) / count
            avg_end_mins = sum(end_hour_minutes) / count
            
            avg_end_mins %= 1440
            
            return {
                "avg_start": f"{int(avg_start_mins // 60):02d}:{int(avg_start_mins % 60):02d}",
                "avg_end": f"{int(avg_end_mins // 60):02d}:{int(avg_end_mins % 60):02d}",
                "avg_duration_min": round(avg_duration),
                "avg_duration_hours": round(avg_duration / 60, 1)
            }

        nap_stats = calculate_avg(naps)
        night_stats = calculate_avg(night_sleeps)
        
        # 다음 수면 예측 (KST 기준)
        now_kr = datetime.utcnow() + timedelta(hours=9)
        current_hour = now_kr.hour
        next_type = 'nap' if 6 <= current_hour < 18 else 'night'

        return jsonify({
            "status": "success",
            "analysis": {
                "nap": nap_stats,
                "night": night_stats,
                "next_prediction": next_type
            },
            "debug": {
                "raw_logs": len(logs),
                "processed_naps": len(naps),
                "processed_nights": len(night_sleeps)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"분석 중 오류 발생: {str(e)}"}), 500

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        # 1. 현재 재고 조회
        inv_res = supabase.table('inventory').select('*').execute()
        inventory = {item['item_key']: item for item in inv_res.data}
        
        # 2. 사용량 분석 및 예측
        analysis = {}
        for key in ['diaper_day', 'diaper_night']:
            d_type = key.split('_')[1] # day or night
            # 최근 7일간 해당 타입 기저귀 사용량 조회
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            logs_res = supabase.table('diaper_logs').select('id', 'date')\
                .eq('diaper_type', d_type)\
                .gte('date', seven_days_ago).execute()
            
            if logs_res.data:
                # 첫 기록 날짜와 오늘 날짜 사이의 일수 계산 (최대 7일)
                dates = []
                for log in logs_res.data:
                    d_str = log['date'].replace('Z', '')
                    if '+' in d_str: d_str = d_str.split('+')[0] # Remove offset for naive comparison
                    dates.append(datetime.fromisoformat(d_str))
                
                earliest_date = min(dates)
                delta_days = (datetime.utcnow() - earliest_date).days + 1
                divisor = min(max(delta_days, 1), 7)
                
                count = len(logs_res.data)
                daily_avg = count / float(divisor)
            else:
                daily_avg = 0
            
            current_qty = inventory.get(key, {}).get('quantity', 0)
            
            days_left = 999
            if daily_avg > 0:
                days_left = int(current_qty / daily_avg)
            
            # 구매 예정일
            purchase_date = (datetime.now() + timedelta(days=days_left)).strftime('%Y-%m-%d') if days_left < 365 else "충분함"
            
            analysis[key] = {
                "daily_avg": round(daily_avg, 1),
                "days_left": days_left,
                "purchase_date": purchase_date
            }
            
        return jsonify({"status": "success", "inventory": list(inventory.values()), "analysis": analysis})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/inventory/add', methods=['POST'])
def add_inventory():
    data = request.json
    item_key = data.get('item_key')
    amount = int(data.get('amount', 0))
    is_pack = data.get('is_pack', False) # True면 팩 단위, False면 낱개 단위
    
    try:
        res = supabase.table('inventory').select('*').eq('item_key', item_key).execute()
        if res.data:
            current = res.data[0]
            pack_size = current.get('pack_size', 1) 
            
            final_add = amount * pack_size if is_pack else amount
            
            new_qty = current['quantity'] + final_add
            supabase.table('inventory').update({"quantity": new_qty}).eq('item_key', item_key).execute()
            
            msg = f"{amount}팩({final_add}개) 추가됨" if is_pack else f"{amount}개 조정됨"
            return jsonify({"status": "success", "message": f"재고가 업데이트되었습니다. ({msg}, 현재: {new_qty}개)"})
        else:
            return jsonify({"status": "error", "message": "상품을 찾을 수 없습니다."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'POST':
        new_settings = request.json
        api_key = new_settings.get('gemini_api_key', '')
        
        # Supabase에 설정 저장 시도
        try:
            # 단일 행 설정을 위해 ID 1번 혹은 특정 UUID 사용 (여기선 기존 방식 유지하되 정리)
            current = supabase.table('settings').select('*').limit(1).execute()
            
            if current.data:
                sid = current.data[0]['id']
                supabase.table('settings').update({
                    "gemini_api_key": api_key,
                    "updated_at": datetime.utcnow().isoformat() + 'Z'
                }).eq('id', sid).execute()
            else:
                supabase.table('settings').insert({
                    "id": str(uuid.uuid4()),
                    "gemini_api_key": api_key,
                    "updated_at": datetime.utcnow().isoformat() + 'Z'
                }).execute()
            
            # 런타임 설정 업데이트
            global GEMINI_API_KEY
            GEMINI_API_KEY = api_key
            configure_gemini(api_key)
            
            cache_invalidate('load_data')
            return jsonify({"status": "success", "message": "설정이 저장되었습니다."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"설정 저장 실패: {e}"}), 500
    else:
        # GET 요청 시 현재 설정 반환
        try:
            settings_res = supabase.table('settings').select('*').limit(1).execute()
            db_settings = settings_res.data[0] if settings_res.data else {}
            
            # 기저귀 팩 사이즈 정보도 함께 반환
            inv_res = supabase.table('inventory').select('item_key', 'pack_size').execute()
            pack_sizes = {item['item_key']: item['pack_size'] for item in inv_res.data}
            db_settings['diaper_pack_sizes'] = pack_sizes
            
            return jsonify(db_settings)
        except Exception as e:
            # Fallback
            return jsonify({})

@app.route('/api/inventory/settings', methods=['POST'])
def update_inventory_settings():
    data = request.json
    try:
        # 낮 기저귀 설정
        if 'diaper_day_pack' in data:
            pack_size = int(data['diaper_day_pack'])
            supabase.table('inventory').update({"pack_size": pack_size}).eq('item_key', 'diaper_day').execute()
        
        # 밤 기저귀 설정
        if 'diaper_night_pack' in data:
            pack_size = int(data['diaper_night_pack'])
            supabase.table('inventory').update({"pack_size": pack_size}).eq('item_key', 'diaper_night').execute()
            
        cache_invalidate('load_data')
        return jsonify({"status": "success", "message": "기저귀 팩 설정이 저장되었습니다."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/timeline', methods=['GET'])
def get_timeline():
    """특정 날짜의 모든 기록(식단, 기저귀, 수면)을 통합 조회합니다."""
    date_str = request.args.get('date') # YYYY-MM-DD
    if not date_str:
        return jsonify({"status": "error", "message": "날짜가 지정되지 않았습니다."}), 400
        
    try:
        # 타임존 누락 방지를 위해 조회 범위를 전후 12시간씩 더 넓게 설정 (KST 고려)
        query_start = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(hours=12)).isoformat() + 'Z'
        query_end = (datetime.strptime(date_str, '%Y-%m-%d') + timedelta(hours=36)).isoformat() + 'Z'
        
        # 병렬 쿼리 실행
        def fetch_meals():
            return supabase.table('meals').select('*').gte('date', query_start).lte('date', query_end).execute()
        def fetch_diapers():
            return supabase.table('diaper_logs').select('*').gte('date', query_start).lte('date', query_end).execute()
        def fetch_sleeps():
            # 특정 날짜의 수면 + 현재 진행 중인 수면(end_time IS NULL) 합집합 조회
            # OR 조건이나 여러 쿼리를 조합할 수 있지만, 여기서는 진행중인 것을 항상 가져오기 위해 별도 쿼리 병합
            normal_sleeps = supabase.table('sleep_logs').select('*').gte('start_time', query_start).lte('start_time', query_end).execute().data
            active_sleeps = supabase.table('sleep_logs').select('*').is_('end_time', 'null').execute().data
            
            # 중복 제거 (ID 기준)
            combined_sleeps = {s['id']: s for s in (normal_sleeps + active_sleeps)}
            return list(combined_sleeps.values())
            
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_meals = executor.submit(fetch_meals)
            future_diapers = executor.submit(fetch_diapers)
            future_sleeps = executor.submit(lambda: fetch_sleeps())
            
            results = {
                'meals': future_meals.result().data,
                'diapers': future_diapers.result().data,
                'sleeps': future_sleeps.result()
            }
            
        # 데이터 병합 및 규격화
        combined = []
        for m in results['meals']:
            combined.append({**m, "category": "meal", "date": m['date']})
        for d in results['diapers']:
            combined.append({**d, "category": "diaper", "date": d['date']})
        for s in results['sleeps']:
            combined.append({**s, "category": "sleep", "date": s['start_time']})
            
        # 공통 정렬 (오름차순: 오전 -> 오후)
        combined.sort(key=lambda x: x['date'])
        
        return jsonify({"status": "success", "logs": combined})
    except Exception as e:
        print(f"Timeline 조회 에러: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/records/update-time', methods=['POST'])
def update_record_time():
    """기록의 시간을 수정합니다."""
    data = request.json
    category = data.get('category')
    record_id = data.get('id')
    new_date = data.get('new_date') # ISO-8601 string with 'Z'
    new_end_date = data.get('new_end_date') # Optional: for sleep records
    
    if not all([category, record_id, new_date]):
        return jsonify({"status": "error", "message": "필수 정보가 누락되었습니다."}), 400
        
    try:
        table_map = {
            'meal': ('meals', 'date'),
            'diaper': ('diaper_logs', 'date'),
            'sleep': ('sleep_logs', 'start_time')
        }
        
        if category not in table_map:
            return jsonify({"status": "error", "message": "잘못된 카테고리입니다."}), 400
            
        table_name, col_name = table_map[category]
        update_data = {col_name: new_date}
        
        # 수면 기록이고 종료 시간이 제공된 경우 추가 업데이트
        if category == 'sleep' and new_end_date:
            update_data['end_time'] = new_end_date
            
        supabase.table(table_name).update(update_data).eq('id', record_id).execute()
        
        cache_invalidate('load_data')
        return jsonify({"status": "success", "message": "시간이 수정되었습니다."})
    except Exception as e:
        print(f"시간 수정 에러: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/recommend', methods=['GET'])
def recommend_meal():
    data = load_data()
    user = data.get('user', {})
    months = user.get('months', 12)
    meals = data.get('meals', [])
    target = user.get('target_nutrition', {"calories": 1000})
    likes = user.get('likes', [])
    dislikes = user.get('dislikes', [])
    
    # 5단계 세분화 식단 데이터베이스 (본문 동일 생략 - 실제 수정 시 유지)
    STAGE_DETAILS = {
        "early": {
            "menus": [
                {"breakfast": "쌀미음", "lunch": "청경채미음", "dinner": "애호박미음", "snack": "사과퓨레"},
                {"breakfast": "찹쌀미음", "lunch": "감자미음", "dinner": "브로콜리미음", "snack": "배퓨레"},
                {"breakfast": "쌀미음", "lunch": "양배추미음", "dinner": "단호박미음", "snack": "바나나퓨레"},
                {"breakfast": "찹쌀미음", "lunch": "오이미음", "dinner": "고구마미음", "snack": "사과배퓨레"},
                {"breakfast": "쌀미음", "lunch": "비트미음", "dinner": "청경채미음", "snack": "거른 자두"}
            ],
            "tip": "알레르기 반응을 살피며 새로운 재료를 하나씩 시작해보세요."
        },
        "middle": {
            "menus": [
                {"breakfast": "소고기 오이죽", "lunch": "닭고기 양파죽", "dinner": "대구살 무죽", "snack": "바나나 요거트"},
                {"breakfast": "연두부 채소죽", "lunch": "소고기 표고버섯죽", "dinner": "고구마 사과죽", "snack": "아기치즈"},
                {"breakfast": "닭고기 브로콜리죽", "lunch": "소고기 미역죽", "dinner": "노른자 채소죽", "snack": "매쉬드 포테이토"},
                {"breakfast": "소고기 청경채죽", "lunch": "대구살 애호박죽", "dinner": "닭고기 당근죽", "snack": "요구르트"},
                {"breakfast": "한우 유근피죽", "lunch": "닭안심 시금치죽", "dinner": "소고기 두부죽", "snack": "배 퓨레"}
            ],
            "tip": "철분 보충을 위해 매끼 소고기나 닭고기를 포함하는 것이 좋아요."
        },
        "late": {
            "menus": [
                {"breakfast": "소고기 가지 진밥", "lunch": "대구살 시금치 진밥", "dinner": "닭고기 단호박 진밥", "snack": "삶은 계란"},
                {"breakfast": "전복 채소 진밥", "lunch": "계란 채소 진밥", "dinner": "소고기 브로콜리 진밥", "snack": "블루베리"},
                {"breakfast": "닭고기 고구마 진밥", "lunch": "소고기 무 진밥", "dinner": "생선살 채소 진밥", "snack": "플레인 요거트"},
                {"breakfast": "소고기 송이버섯 진밥", "lunch": "닭안심 채소 진밥", "dinner": "대구살 아욱 진밥", "snack": "아기치즈"},
                {"breakfast": "한우 콩나물 진밥", "lunch": "소고기 미역 진밥", "dinner": "닭고기 근대 진밥", "snack": "거른 사과"}
            ],
            "tip": "핑거 푸드를 통해 스스로 먹는 즐거움을 가르쳐줄 시기예요."
        },
        "completion": {
            "menus": [
                {"breakfast": "해물 볶음밥", "lunch": "소고기 미역국 진밥", "dinner": "두부 스테이크 & 찐 채소", "snack": "찐 감자"},
                {"breakfast": "닭다리살 채소 볶음밥", "lunch": "대구전 & 시금치 무침", "dinner": "야채 치즈 오므라이스", "snack": "아기용 우유"},
                {"breakfast": "소고기 주먹밥", "lunch": "닭살 감자국 & 밥", "dinner": "가자미 구이 & 나물", "snack": "바나나"},
                {"breakfast": "계란 볶음밥", "lunch": "소고기 무국 & 밥", "dinner": "동그랑땡 & 채소볶음", "snack": "사과"},
                {"breakfast": "새우 애호박 볶음밥", "lunch": "한우 아욱국 & 밥", "dinner": "닭안심 구이 & 야채", "snack": "블루베리 요거트"}
            ],
            "tip": "간을 최소화하고 다양한 식감을 경험하게 해주세요."
        },
        "toddler": {
            "menus": [
                {"breakfast": "불고기 덮밥", "lunch": "곰탕 & 생선구이", "dinner": "닭안심 간장구이 & 밥", "snack": "제철 과일"},
                {"breakfast": "새우 볶음밥", "lunch": "계란국 & 계란말이", "dinner": "소고기 무국 & 두부조림", "snack": "견과류 한알"},
                {"breakfast": "치즈 오므라이스", "lunch": "닭칼국수 (순하게)", "dinner": "함박 스테이크 & 찐채소", "snack": "우유 1컵"},
                {"breakfast": "잡곡밥 & 감자국", "lunch": "소고기 비빔밥 (간장)", "dinner": "돼지고기 수육 & 배추나물", "snack": "요거트 볼"},
                {"breakfast": "생선살 볶음밥", "lunch": "아기 카레 & 밥", "dinner": "소고기 된장국 & 야채전", "snack": "고구마 말랭이"},
                {"breakfast": "전복 유치비빔밥", "lunch": "한우 배추국 & 생선조림", "dinner": "닭곰탕 & 두부부침", "snack": "사과 칩"},
                {"breakfast": "야채 송송 주먹밥", "lunch": "잔치국수 (저염)", "dinner": "너비아니 & 콩나물무침", "snack": "치즈 한장"}
            ],
            "tip": "세 끼 식사와 간식의 영양 밸런스를 맞춰 성장을 도와주세요."
        }
    }

    if months < 7: stage = "early"
    elif months < 10: stage = "middle"
    elif months < 13: stage = "late"
    elif months < 16: stage = "completion"
    else: stage = "toddler"
    
    def process_preferences(menu_name):
        clean_menu = str(menu_name).replace(" ", "")
        for d in dislikes:
            clean_bad = str(d).replace(" ", "").strip()
            if clean_bad and clean_bad in clean_menu:
                return f"⚠️ {menu_name} (기호 외)"
        for l in likes:
            clean_good = str(l).replace(" ", "").strip()
            if clean_good and clean_good in clean_menu:
                return f"🌟 {menu_name} (선호!)"
        return menu_name

    def has_any_dislike(menu_set):
        for val in menu_set.values():
            clean_val = str(val).replace(" ", "")
            for d in dislikes:
                clean_bad = str(d).replace(" ", "").strip()
                if clean_bad and clean_bad in clean_val:
                    return True
        return False

    valid_menus = [m for m in STAGE_DETAILS[stage]["menus"] if not has_any_dislike(m)]
    if not valid_menus:
        selected_set = STAGE_DETAILS[stage]["menus"][0].copy()
        tip = f"⚠️ 싫어하는 음식을 제외한 식단을 찾기 어렵습니다. 기본 추천 식단을 보여드려요."
    else:
        selected_set = random.choice(valid_menus).copy()
        tip = STAGE_DETAILS[stage]["tip"]

    for key in ['breakfast', 'lunch', 'dinner', 'snack']:
        selected_set[key] = process_preferences(selected_set[key])

    # 최근 데이터 분석 (Pandas 없이 구현)
    tendency_msg = "유나의 성장 단계에 딱 맞는 하루 식단을 준비했어요."
    if meals:
        try:
            last_week = datetime.now() - timedelta(days=7)
            recent_meals = []
            for m in meals:
                # ISO 형식과 일반 형식을 모두 지원하도록 유연하게 파싱
                date_str = m['date'].replace('T', ' ').split('+')[0].split('.')[0]
                try:
                    meal_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    if meal_date > last_week:
                        recent_meals.append(m)
                except:
                    continue
            
            if recent_meals:
                total_cal = sum(float(m.get('calories', 0)) for m in recent_meals)
                avg_cal = total_cal / 7
                cal_rate = (avg_cal / target.get('calories', 1000)) * 100
                tendency_msg = f"최근 1주일간 유나는 목표 칼로리의 {cal_rate:.1f}%를 섭취 중이에요."
        except Exception as e:
            print(f"추천 분석 에러: {e}")

    return jsonify({
        "recommendation": selected_set,
        "tip": tip,
        "tendency": tendency_msg,
        "months": months,
        "stage_name": stage
    })

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("\n" + "="*50)
    print(f"[Server] Yuna Nutrition Tracker Started!")
    print(f"URL: http://localhost:5000")
    print(f"Mobile: http://{local_ip}:5000")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
