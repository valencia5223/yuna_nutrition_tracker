from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta
import uuid
import socket
import random

app = Flask(__name__)

# 데이터 파일 경로
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
    "소고기": {"calories": 250, "carbs": 0, "protein": 26, "fat": 15},
    "닭고기": {"calories": 165, "carbs": 0, "protein": 31, "fat": 3.6},
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
    
    # 유아식 메뉴
    "볶음밥": {"calories": 180, "carbs": 30, "protein": 5, "fat": 4.5},
    "불고기": {"calories": 200, "carbs": 8, "protein": 18, "fat": 10},
    # 유아식 메뉴 (1회 제공량 기준 현실화)
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
    
    # 간식 및 기타
    "사과": {"calories": 30, "carbs": 8, "protein": 0.2, "fat": 0.1}, # 아기 섭취량 기준
    "배": {"calories": 35, "carbs": 9, "protein": 0.2, "fat": 0.1},
    "바나나": {"calories": 50, "carbs": 12, "protein": 0.6, "fat": 0.2},
    "요거트": {"calories": 50, "carbs": 4, "protein": 3, "fat": 2.5},
    "치즈": {"calories": 60, "carbs": 0.5, "protein": 4, "fat": 5}, # 아기 치즈 1장
    "우유": {"calories": 65, "carbs": 5, "protein": 3.3, "fat": 3.5},
    "블루베리": {"calories": 30, "carbs": 7, "protein": 0.4, "fat": 0.2},
    "퓨레": {"calories": 40, "carbs": 10, "protein": 0.3, "fat": 0.1},
    
    # 기본 식재료 (아기 1회 섭취분량 고려)
    "밥": {"calories": 150, "carbs": 33, "protein": 3, "fat": 0.5}, # 아기 공기 기준
    "잡곡밥": {"calories": 160, "carbs": 34, "protein": 4, "fat": 1},
    "소고기": {"calories": 100, "carbs": 0, "protein": 12, "fat": 6}, # 50g 기준
    "닭고기": {"calories": 80, "carbs": 0, "protein": 15, "fat": 2},
}

def calculate_nutrition(menu_name, months=12, amount="보통"):
    import re
    result = {"calories": 0, "carbs": 0, "protein": 0, "fat": 0}
    
    # 중량 정보 추출 (예: 100g, 50그람, 50그램 등)
    weight_match = re.search(r'(\d+)\s*(g|그람|그램)', menu_name)
    input_weight = None
    if weight_match:
        input_weight = float(weight_match.group(1))
    
    # 섭취량 보정 계수 (중량이 입력된 경우 중량 비율로 대체)
    if input_weight is not None:
        # 기준 중량을 100g으로 잡고 비율 계산 (예: 50g 입력 시 0.5배)
        amount_multiplier = input_weight / 100.0
    else:
        amount_multiplier = {"조금": 0.6, "보통": 1.0, "많이": 1.4}.get(amount, 1.0)
    
    # 개월수별 성장 단계 가중치 (성인 기준 데이터를 아기 섭취량으로 변환하는 핵심 계수)
    if months < 7: stage_multiplier = 0.4
    elif months < 10: stage_multiplier = 0.5
    elif months < 13: stage_multiplier = 0.6
    elif months < 24: stage_multiplier = 0.7
    else: stage_multiplier = 0.8
    
    # 중량이 직접 입력된 경우, 이미 절대적인 양을 의미하므로 성장 단계 가중치 영향을 줄임 (또는 제거 고려)
    # 여기서는 중량 입력 시 더 직관적인 결과(입력값 반영)를 위해 stage_multiplier를 1.0으로 보정 (중량 우선)
    if input_weight is not None:
        stage_multiplier = 1.0
    
    menus = [m.strip() for m in menu_name.replace(',', ' ').split()]
    found_any = False
    for menu in menus:
        # 중량 텍스트 자체(예: 100g)는 영양소 검색에서 제외
        if weight_match and weight_match.group(0) in menu:
            continue
            
        for key, value in FOOD_NUTRITION_DATA.items():
            if key in menu:
                result["calories"] += value["calories"]
                result["carbs"] += value["carbs"]
                result["protein"] += value["protein"]
                result["fat"] += value["fat"]
                found_any = True
                break
    
    if not found_any:
        # 데이터가 없는 경우 기본 한 끼 권장량 (100g 기준 기본값)
        result = {"calories": 150, "carbs": 25, "protein": 8, "fat": 4}
    
    # 최종 보정
    for key in result:
        result[key] = round(result[key] * stage_multiplier * amount_multiplier, 1)
        
    return result

def load_data():
    if not os.path.exists(DATA_FILE):
        # 초기 데이터 생성
        initial_data = {
            "user": {
                "name": "차유나",
                "months": 12,
                "likes": [],
                "dislikes": [],
                "target_nutrition": {
                    "calories": 1000,
                    "carbs": 130,
                    "protein": 25,
                    "fat": 30
                }
            },
            "meals": []
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
        return initial_data
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 기존 데이터에 필드가 없는 경우 안전하게 추가
        if 'likes' not in data['user']:
            data['user']['likes'] = []
        if 'dislikes' not in data['user']:
            data['user']['dislikes'] = []
        if 'birth_date' not in data['user']:
            data['user']['birth_date'] = "2024-07-19"
        if 'gender' not in data['user']:
            data['user']['gender'] = "여아"
            
        # 레거시 데이터 ID 자동 보정
        needs_save = False
        for meal in data.get('meals', []):
            if 'id' not in meal:
                meal['id'] = str(uuid.uuid4())
                needs_save = True
        
        # 성장 기록 필드 추가
        if 'growth' not in data:
            data['growth'] = []
            needs_save = True
            
        if needs_save:
            save_data(data)
            
        return data

# 한국 여아 성장 표준 데이터 (2017 소아청소년 성장도표 50백분위수)
# {개월수: [평균키, 평균몸무게]}
GIRLS_GROWTH_STANDARD = {
    0: [49.1, 3.3], 1: [53.7, 4.3], 2: [57.1, 5.2], 3: [59.8, 5.9], 
    4: [62.1, 6.5], 5: [64.0, 7.0], 6: [65.7, 7.4], 7: [67.3, 7.8], 
    8: [68.7, 8.1], 9: [70.1, 8.4], 10: [71.5, 8.7], 11: [72.8, 8.9], 
    12: [74.0, 9.1], 13: [75.2, 9.4], 14: [76.4, 9.6], 15: [77.5, 9.8], 
    16: [78.6, 10.0], 17: [79.7, 10.2], 18: [80.7, 10.4], 19: [81.7, 10.5], 
    20: [82.7, 10.7], 21: [83.7, 10.9], 22: [84.6, 11.1], 23: [85.5, 11.2], 
    24: [86.4, 11.4], 30: [91.3, 12.7], 36: [95.4, 13.9]
}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    data = load_data()
    return jsonify(data)

@app.route('/api/user/update', methods=['POST'])
def update_user():
    update_info = request.json
    data = load_data()
    
    # 개월수 업데이트
    if 'months' in update_info:
        data['user']['months'] = int(update_info['months'])
        
        # 개월수에 따른 목표 영양소 자동 조정 (대략적 기준)
        m = data['user']['months']
        if m < 6:
            data['user']['target_nutrition'] = {"calories": 600, "carbs": 70, "protein": 15, "fat": 25}
        elif m < 12:
            data['user']['target_nutrition'] = {"calories": 800, "carbs": 100, "protein": 20, "fat": 30}
        elif m < 24:
            data['user']['target_nutrition'] = {"calories": 1000, "carbs": 130, "protein": 25, "fat": 35}
        else:
            data['user']['target_nutrition'] = {"calories": 1300, "carbs": 170, "protein": 35, "fat": 40}

    save_data(data)
    return jsonify({"status": "success", "message": "프로필이 업데이트되었습니다.", "user": data['user']})

@app.route('/api/record', methods=['POST'])
def record_meal():
    new_meal = request.json
    menu_name = new_meal.get('menuName', '')
    amount = new_meal.get('amount', '보통')
    
    data = load_data()
    user_months = data['user'].get('months', 12)
    
    # 고유 ID 부여 (삭제용)
    new_meal['id'] = str(uuid.uuid4())
    
    # 영양소가 비어있거나 0인 경우 자동 계산 시도
    has_nutrition = all(new_meal.get(key, 0) > 0 for key in ['calories', 'carbs', 'protein', 'fat'])
    
    status_msg = "식단이 기록되었습니다."
    if not has_nutrition:
        # 개월수와 섭취량을 반영한 정밀 계산
        auto_nutrition = calculate_nutrition(menu_name, user_months, amount)
        new_meal.update(auto_nutrition)
        status_msg = f"'{menu_name}'({amount})을(를) 분석하여 기록했습니다."

    # 날짜 정보 추가
    new_meal['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    data['meals'].append(new_meal)
    save_data(data)
    
    return jsonify({"status": "success", "message": status_msg, "data": new_meal})

@app.route('/api/delete', methods=['POST'])
def delete_meal():
    meal_id = request.json.get('id')
    data = load_data()
    
    original_count = len(data['meals'])
    data['meals'] = [m for m in data['meals'] if m.get('id') != meal_id]
    
    if len(data['meals']) < original_count:
        save_data(data)
        return jsonify({"status": "success", "message": "기록이 삭제되었습니다."})
    else:
        return jsonify({"status": "error", "message": "삭제할 기록을 찾지 못했습니다."}), 404

@app.route('/api/growth', methods=['POST'])
def record_growth():
    growth_data = request.json
    height = float(growth_data.get('height', 0))
    weight = float(growth_data.get('weight', 0))
    months = int(growth_data.get('months', 12))
    
    data = load_data()
    
    # 한국 여아 평균 데이터와 비교 (Z-Score 기반 백분위 추정)
    def calculate_percentile(value, avg, cv):
        if avg <= 0: return 50
        z = (value - avg) / (avg * cv)
        # Z-score to Percentile approximation (simplified)
        import math
        percentile = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100
        return round(max(1, min(99, percentile)), 1)

    standard_months = sorted(GIRLS_GROWTH_STANDARD.keys())
    closest_m = min(standard_months, key=lambda x: abs(x - months))
    avg_h, avg_w = GIRLS_GROWTH_STANDARD[closest_m]
    
    # 키 백분위 (CV 약 3.5%) / 몸무게 백분위 (CV 약 11%)
    h_percentile = calculate_percentile(height, avg_h, 0.035)
    w_percentile = calculate_percentile(weight, avg_w, 0.11)
    
    status_msg = f"기록 완료! {months}개월 기준 [키: 백분위 {h_percentile} (상위 {round(100-h_percentile, 1)}%)] | [몸무게: 백분위 {w_percentile} (상위 {round(100-w_percentile, 1)}%)]"
    
    new_record = {
        "id": str(uuid.uuid4()),
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "months": months,
        "height": height,
        "weight": weight,
        "h_percentile": h_percentile,
        "w_percentile": w_percentile
    }
    
    data['growth'].append(new_record)
    save_data(data)
    
    return jsonify({"status": "success", "message": status_msg, "record": new_record})

@app.route('/api/growth/history', methods=['GET'])
def get_growth_history():
    data = load_data()
    # 날짜순 정렬
    history = sorted(data.get('growth', []), key=lambda x: x['date'])
    return jsonify({"status": "success", "history": history})

@app.route('/api/growth/delete', methods=['POST'])
def delete_growth():
    record_id = request.json.get('id')
    data = load_data()
    
    original_count = len(data.get('growth', []))
    data['growth'] = [g for g in data.get('growth', []) if g.get('id') != record_id]
    
    if len(data['growth']) < original_count:
        save_data(data)
        return jsonify({"status": "success", "message": "성장 기록이 삭제되었습니다."})
    else:
        return jsonify({"status": "error", "message": "삭제할 기록을 찾지 못했습니다."}), 404

@app.route('/api/user/preferences', methods=['POST'])
def update_preferences():
    preferences = request.json
    data = load_data()
    data['user']['likes'] = preferences.get('likes', [])
    data['user']['dislikes'] = preferences.get('dislikes', [])
    save_data(data)
    return jsonify({"status": "success", "message": "음식 취향이 저장되었습니다."})

@app.route('/api/recommend', methods=['GET'])
def recommend_meal():
    data = load_data()
    months = data['user'].get('months', 12)
    meals = data.get('meals', [])
    target = data['user']['target_nutrition']
    likes = data['user'].get('likes', [])
    dislikes = data['user'].get('dislikes', [])
    
    # 5단계 세분화 식단 데이터베이스 (대폭 확장)
    STAGE_DETAILS = {
        "early": {
            "menus": [
                {"breakfast": "쌀미음", "lunch": "청경채미음", "dinner": "애호박미음", "snack": "사과퓨레"},
                {"breakfast": "찹쌀미음", "lunch": "감자미음", "dinner": "브로콜리미음", "snack": "배퓨레"},
                {"breakfast": "쌀미음", "lunch": "양배추미음", "dinner": "단호박미음", "snack": "바나나퓨레"},
                {"breakfast": "찹쌀미음", "lunch": "오이미음", "dinner": "청경채미음", "snack": "배퓨레"}
            ],
            "tip": "알레르기 반응을 살피며 새로운 재료를 하나씩 시작해보세요."
        },
        "middle": {
            "menus": [
                {"breakfast": "소고기 오이죽", "lunch": "닭고기 양파죽", "dinner": "대구살 무죽", "snack": "바나나 요거트"},
                {"breakfast": "연부두 채소죽", "lunch": "소고기 표고버섯죽", "dinner": "고구마 사과죽", "snack": "치즈"},
                {"breakfast": "닭고기 브로콜리죽", "lunch": "소고기 미역죽", "dinner": "노른자 채소죽", "snack": "사과"},
                {"breakfast": "소고기 청경채죽", "lunch": "대구살 애호박죽", "dinner": "닭고기 당근죽", "snack": "배"}
            ],
            "tip": "철분 보충을 위해 매끼 소고기나 닭고기를 포함하는 것이 좋아요."
        },
        "late": {
            "menus": [
                {"breakfast": "소고기 가지 진밥", "lunch": "대구살 시금치 진밥", "dinner": "닭고기 단호박 진밥", "snack": "삶은 계란"},
                {"breakfast": "전복 채소 진밥", "lunch": "계란 채소 진밥", "dinner": "소고기 브로콜리 진밥", "snack": "블루베리"},
                {"breakfast": "닭고기 고구마 진밥", "lunch": "소고기 무 진밥", "dinner": "생선살 채소 진밥", "snack": "요거트"},
                {"breakfast": "중기 볶음밥", "lunch": "닭안심 채소 진밥", "dinner": "소고기 버섯 진밥", "snack": "치즈"}
            ],
            "tip": "핑거 푸드를 통해 스스로 먹는 즐거움을 가르쳐줄 시기예요."
        },
        "completion": {
            "menus": [
                {"breakfast": "해물 볶음밥", "lunch": "소고기 미역국 진밥", "dinner": "두부 스테이크", "snack": "찐 감자"},
                {"breakfast": "닭다리살 채소 볶음밥", "lunch": "대구전과 시금치 무침", "dinner": "야채 치즈 오므라이스", "snack": "우유"},
                {"breakfast": "소고기 주먹밥", "lunch": "닭살 감자국과 아기밥", "dinner": "생선구이와 나물", "snack": "바나나"},
                {"breakfast": "계란 볶음밥", "lunch": "소고기 무국과 아기밥", "dinner": "동그랑땡과 채소볶음", "snack": "사과"}
            ],
            "tip": "간을 최소화하고 다양한 식감을 경험하게 해주세요."
        },
        "toddler": {
            "menus": [
                {"breakfast": "불고기 덮밥", "lunch": "곰탕과 생선구이", "dinner": "닭안심 구이와 밥", "snack": "제철 과일"},
                {"breakfast": "새우 볶음밥", "lunch": "계란국과 계란말이", "dinner": "소고기 무국과 두부조림", "snack": "견과류"},
                {"breakfast": "오므라이스", "lunch": "닭칼국수", "dinner": "스테이크와 찐채소", "snack": "우유"},
                {"breakfast": "잡곡밥과 감자국", "lunch": "비빔밥 (맵지 않게)", "dinner": "수육과 배추나물", "snack": "요거트"},
                {"breakfast": "생선살 볶음밥", "lunch": "아기 카레", "dinner": "된장국", "snack": "과일퓨레"}
            ],
            "tip": "세 끼 식사와 간식의 영양 밸런스를 맞춰 성장을 도와주세요."
        }
    }

    if months < 7: stage = "early"
    elif months < 10: stage = "middle"
    elif months < 13: stage = "late"
    elif months < 16: stage = "completion"
    else: stage = "toddler"
    
    # 싫어하는 음식 및 좋아하는 음식 통합 처리 함수
    def process_preferences(menu_name):
        clean_menu = str(menu_name).replace(" ", "")
        
        # 1. 싫어하는 음식 체크 (최우선)
        for d in dislikes:
            clean_bad = str(d).replace(" ", "").strip()
            if clean_bad and clean_bad in clean_menu:
                return f"⚠️ {menu_name} (기호 외)"
        
        # 2. 좋아하는 음식 체크
        for l in likes:
            clean_good = str(l).replace(" ", "").strip()
            if clean_good and clean_good in clean_menu:
                return f"🌟 {menu_name} (선호!)"
        
        return menu_name

    # 싫어하는 음식이 "하나라도" 포함된 세트인지 확인하는 함수
    def has_any_dislike(menu_set):
        for val in menu_set.values():
            clean_val = str(val).replace(" ", "")
            for d in dislikes:
                clean_bad = str(d).replace(" ", "").strip()
                if clean_bad and clean_bad in clean_val:
                    return True
        return False

    # 필터링 적용
    valid_menus = [m for m in STAGE_DETAILS[stage]["menus"] if not has_any_dislike(m)]
    
    if not valid_menus:
        # 모든 메뉴가 기호에 맞지 않을 때의 폴백: 가장 첫 번째 메뉴를 선택하되 ⚠️ 표시 유지
        selected_set = STAGE_DETAILS[stage]["menus"][0].copy()
        tip = f"⚠️ 현재 등록하신 '싫어하는 음식'을 모두 제외한 식단을 찾기 어렵습니다. 식재료를 조금 조절해 보시는 건 어떨까요? (기본 추천 식단을 먼저 보여드려요)"
    else:
        selected_set = random.choice(valid_menus).copy()
        tip = STAGE_DETAILS[stage]["tip"]

    # 최종 명칭 변환 (🌟 또는 ⚠️ 표시 적용)
    for key in ['breakfast', 'lunch', 'dinner', 'snack']:
        selected_set[key] = process_preferences(selected_set[key])

    # 최근 데이터 분석
    df = pd.DataFrame(meals)
    tendency_msg = "유나의 성장 단계에 딱 맞는 하루 식단을 준비했어요."
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        last_week = datetime.now() - timedelta(days=7)
        recent_df = df[df['date'] > last_week]
        if not recent_df.empty:
            avg_cal = recent_df['calories'].sum() / 7
            cal_rate = (avg_cal / target['calories']) * 100
            tendency_msg = f"최근 1주일간 유나는 목표 칼로리의 {cal_rate:.1f}%를 섭취 중이에요."

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
    print(f"🚀 유나의 식단 관리 서버가 가동되었습니다!")
    print(f"🔗 PC 접속 주소: http://localhost:5000")
    print(f"📱 모바일 접속 주소: http://{local_ip}:5000")
    print("💡 스마트폰과 PC가 같은 Wi-Fi에 연결되어 있어야 합니다.")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
