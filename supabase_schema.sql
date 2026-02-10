-- 사용자 프로필 테이블 생성
CREATE TABLE IF NOT EXISTS user_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT DEFAULT '차유나',
    birth_date DATE DEFAULT '2024-07-19',
    likes JSONB DEFAULT '[]',
    dislikes JSONB DEFAULT '[]',
    target_nutrition JSONB DEFAULT '{"calories": 1000, "carbs": 130, "protein": 25, "fat": 30}',
    gender TEXT DEFAULT '여아',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 단일 사용자 시스템이므로 초기 데이터 삽입
INSERT INTO user_profile (id, name) VALUES ('00000000-0000-0000-0000-000000000000', '차유나')
ON CONFLICT (id) DO NOTHING;

-- 식단 기록 테이블 생성
CREATE TABLE IF NOT EXISTS meals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    meal_type TEXT,
    menu_name TEXT,
    amount TEXT,
    calories FLOAT,
    carbs FLOAT,
    protein FLOAT,
    fat FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 성장 기록 테이블 생성
CREATE TABLE IF NOT EXISTS growth (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    months INTEGER,
    height FLOAT,
    weight FLOAT,
    h_percentile FLOAT,
    w_percentile FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 설정 테이블 생성 (새로 추가됨)
CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gemini_api_key TEXT,
    diaper_pack_sizes JSONB DEFAULT '{"diaper_day": 50, "diaper_night": 30}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS (Row Level Security) 설정 - 간단한 개인화 앱이므로 비활성화하거나 전체 허용
ALTER TABLE user_profile DISABLE ROW LEVEL SECURITY;
ALTER TABLE meals DISABLE ROW LEVEL SECURITY;
ALTER TABLE growth DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings DISABLE ROW LEVEL SECURITY;
