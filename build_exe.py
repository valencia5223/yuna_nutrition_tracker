import subprocess
import os
import sys
import shutil

def build_exe():
    project_name = "yuna_nutrition_tracker"
    entry_point = "main_desktop.py"
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={project_name}",
        "--add-data=templates;templates",
        "--add-data=static;static",
        "--add-data=data.json;.",  # data.json 포함 (없으면 생성되겠지만 초기 포함)
        "--hidden-import=pandas",
        "--hidden-import=flask",
        "--hidden-import=webview",
        entry_point
    ]
    
    # data.json이 없으면 빈 파일 생성 (빌드 에러 방지)
    if not os.path.exists('data.json'):
        with open('data.json', 'w') as f:
            f.write('{}')

    print(f"Building {project_name}.exe...")
    try:
        subprocess.run(cmd, check=True)
        print("Build complete. Check the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
    except FileNotFoundError:
        print("PyInstaller not found. Please install it with: pip install pyinstaller")

if __name__ == "__main__":
    # 기존 build/dist 삭제
    if os.path.exists('build'): shutil.rmtree('build')
    if os.path.exists('dist'): shutil.rmtree('dist')
    
    build_exe()
