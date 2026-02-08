@echo off
chcp 65001
echo ==========================================
echo 차유나 영양 관리 앱 만들기 (EXE 변환)
echo ==========================================

echo [1/2] 필수 도구 설치 중...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [오류] 라이브러리 설치 실패. Python이 설치되어 있는지 확인해주세요.
    pause
    exit /b
)

echo [2/2] 실행 파일(EXE) 생성 중...
python build_exe.py
if %errorlevel% neq 0 (
    echo [오류] 빌드 실패. output을 확인해주세요.
    pause
    exit /b
)

echo.
echo ==========================================
echo [완료] dist 폴더 안에 실행 파일이 생성되었습니다!
echo ==========================================
pause
