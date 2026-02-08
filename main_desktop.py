import webbrowser
import threading
import sys
import os
import time
from app import app

def start_flask():
    # Flask 서버 시작 (0.0.0.0으로 설정하여 외부 접속 허용)
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

if __name__ == '__main__':
    # 1. Flask 서버를 별도 스레드에서 시작
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # 2. 서버가 시작될 시간을 잠시 대기
    time.sleep(1)

    # 3. 기본 웹 브라우저로 접속
    print("브라우저를 통해 '차유나 영양 관리'를 실행합니다...")
    webbrowser.open('http://127.0.0.1:5001')

    # 4. 메인 스레드 유지
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("프로그램을 종료합니다.")

