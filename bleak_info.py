# bleak_info.py
import sys
import bleak

print("=== Bleak 설치 정보 ===")

# 1. 기본 정보
print(f"Python 버전: {sys.version}")
print(f"Bleak 모듈 위치: {bleak.__file__}")

# 2. 버전 확인 (여러 방법 시도)
version_found = False

# 방법 1: __version__ 속성
try:
    print(f"Bleak 버전 (__version__): {bleak.__version__}")
    version_found = True
except AttributeError:
    print("❌ __version__ 속성 없음")

# 방법 2: VERSION 속성
try:
    print(f"Bleak 버전 (VERSION): {bleak.VERSION}")
    version_found = True
except AttributeError:
    print("❌ VERSION 속성 없음")

# 방법 3: pip로 확인
if not version_found:
    print("pip로 버전 확인 중...")
    import subprocess
    try:
        result = subprocess.run(['pip', 'show', 'bleak'], 
                              capture_output=True, text=True)
        print("Pip show 결과:")
        print(result.stdout)
    except Exception as e:
        print(f"pip show 실패: {e}")

# 3. BleakClient 기본 기능 확인
print("\n=== BleakClient 기능 확인 ===")
from bleak import BleakClient

# 중요 메서드들 확인
important_methods = [
    'connect', 'disconnect', 'is_connected', 
    'get_services', 'services', 'read_gatt_char'
]

for method in important_methods:
    exists = hasattr(BleakClient, method)
    status = "✅" if exists else "❌"
    print(f"  {method}: {status}")

# 4. 모든 가용 메서드 출력
print(f"\n=== 사용 가능한 모든 메서드 ===")
all_methods = [attr for attr in dir(BleakClient) if not attr.startswith('_')]
for method in sorted(all_methods):
    print(f"  - {method}")
