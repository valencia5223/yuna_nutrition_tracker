@echo off
chcp 65001
echo ==========================================
echo 차유나 영양 관리 앱 실행 중...
echo ==========================================

:: 라이브러리 설치 확인 (없으면 설치)
python -c "import webview" 2>NUL
if %errorlevel% neq 0 (
    echo [필수 파일 설치 중... 잠시만 기다려주세요]
    python -m pip install -r requirements.txt
)

:: 데스크톱 앱 실행
:: pythonw를 사용하면 검은색 콘솔 창 없이 실행되지만, 
:: 혹시 모를 에러 확인을 위해 우선 python으로 실행합니다.
python main_desktop.py
if %errorlevel% neq 0 (
    echo [오류 발생] 실행 중 문제가 생겼습니다.
    pause
)
