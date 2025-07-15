# bleak_test.py
import bleak
import inspect

print("=== Bleak 라이브러리 정보 ===")
print(f"버전: {bleak.__version__}")
print(f"설치 위치: {bleak.__file__}")

print("\n=== BleakClient 사용 가능한 메서드 ===")
from bleak import BleakClient

# BleakClient의 모든 메서드 확인
methods = [method for method in dir(BleakClient) if not method.startswith('_')]
for method in sorted(methods):
    print(f"  - {method}")

# 특정 메서드 존재 확인
important_methods = ['connect', 'disconnect', 'is_connected', 'get_services']
print(f"\n=== 중요 메서드 존재 확인 ===")
for method in important_methods:
    exists = hasattr(BleakClient, method)
    print(f"  {method}: {'✅' if exists else '❌'}")

# get_services가 없다면 대안 찾기
if not hasattr(BleakClient, 'get_services'):
    print(f"\n❌ get_services 메서드가 없습니다!")
    print("대안 메서드 찾는 중...")
    
    # services 관련 메서드 찾기
    service_methods = [m for m in methods if 'service' in m.lower()]
    if service_methods:
        print("서비스 관련 메서드:")
        for method in service_methods:
            print(f"  - {method}")
    else:
        print("서비스 관련 메서드를 찾을 수 없습니다.")
