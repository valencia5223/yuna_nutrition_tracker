import webbrowser
import threading
import sys
import os
import time

try:
    from app import app
except ImportError as e:
    print(f"\n[오류] 필수 라이브러리가 설치되지 않았습니다: {e}")
    print("터미널에서 'pip install -r requirements.txt'를 실행해 주세요.")
    input("\n계속하려면 엔터키를 누르세요...")
    sys.exit(1)

def start_flask():
    try:
        # Flask 서버 시작 (포트는 5001 사용)
        app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"\n[오류] 서버 시작 실패: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 차유나 영양 관리 데스크탑 버전을 실행합니다.")
    print("=" * 50)

    # 1. Flask 서버를 별도 스레드에서 시작
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # 2. 서버가 시작될 시간을 잠시 대기
    print("서버 준비 중...")
    time.sleep(2)

    # 3. 기본 웹 브라우저로 접속
    url = 'http://127.0.0.1:5001'
    print(f"🔗 접속 주소: {url}")
    print("브라우저를 실행합니다...")
    webbrowser.open(url)

    # 4. 메인 스레드 유지
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")

