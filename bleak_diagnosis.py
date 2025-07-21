# bleak_diagnosis.py
import sys
import os

print("=== 완전한 Bleak 진단 ===")

# 1. Python 환경 정보
print(f"Python 버전: {sys.version}")
print(f"Python 실행 경로: {sys.executable}")
print(f"가상환경: {os.environ.get('VIRTUAL_ENV', '없음')}")

# 2. 설치된 패키지 확인
print("\n=== 설치된 패키지 확인 ===")
import subprocess
try:
    result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                          capture_output=True, text=True)
    lines = result.stdout.split('\n')
    bleak_lines = [line for line in lines if 'bleak' in line.lower()]
    
    if bleak_lines:
        print("Bleak 관련 패키지:")
        for line in bleak_lines:
            print(f"  {line}")
    else:
        print("❌ pip list에서 bleak를 찾을 수 없음!")
except Exception as e:
    print(f"pip list 실행 실패: {e}")

# 3. bleak 모듈 임포트 테스트
print("\n=== Bleak 임포트 테스트 ===")
try:
    import bleak
    print(f"✅ bleak 임포트 성공")
    print(f"bleak 위치: {bleak.__file__}")
    
    # 버전 정보 (모든 방법 시도)
    version_attrs = ['__version__', 'VERSION', 'version']
    for attr in version_attrs:
        if hasattr(bleak, attr):
            version = getattr(bleak, attr)
            print(f"버전 ({attr}): {version}")
            break
    else:
        print("⚠️ 버전 정보를 찾을 수 없음")
        
except ImportError as e:
    print(f"❌ bleak 임포트 실패: {e}")
    exit(1)

# 4. BleakClient 상세 분석
print("\n=== BleakClient 분석 ===")
try:
    from bleak import BleakClient
    print("✅ BleakClient 임포트 성공")
    
    # 모든 메서드와 속성
    all_attrs = dir(BleakClient)
    public_attrs = [attr for attr in all_attrs if not attr.startswith('_')]
    
    print(f"총 공개 메서드/속성: {len(public_attrs)}")
    
    # 중요 메서드들 확인
    important_methods = [
        'connect', 'disconnect', 'is_connected',
        'get_services', 'services', 
        'read_gatt_char', 'write_gatt_char'
    ]
    
    print("\n중요 메서드 존재 여부:")
    for method in important_methods:
        exists = hasattr(BleakClient, method)
        status = "✅" if exists else "❌"
        print(f"  {method}: {status}")
    
    # get_services가 없다면 대안 찾기
    if not hasattr(BleakClient, 'get_services'):
        print("\n❌ get_services가 없습니다!")
        print("서비스 관련 대안 찾는 중...")
        
        service_attrs = [attr for attr in public_attrs if 'service' in attr.lower()]
        print(f"서비스 관련 속성들: {service_attrs}")
        
        gatt_attrs = [attr for attr in public_attrs if 'gatt' in attr.lower()]
        print(f"GATT 관련 속성들: {gatt_attrs}")
    
    # 전체 메서드 목록
    print(f"\n전체 공개 메서드/속성 목록:")
    for attr in sorted(public_attrs):
        print(f"  - {attr}")
        
except ImportError as e:
    print(f"❌ BleakClient 임포트 실패: {e}")

# 5. 실제 객체 생성 테스트
print("\n=== BleakClient 객체 생성 테스트 ===")
try:
    client = BleakClient("00:00:00:00:00:00")  # 더미 주소
    print("✅ BleakClient 객체 생성 성공")
    
    # 생성된 객체의 메서드 확인
    obj_attrs = [attr for attr in dir(client) if not attr.startswith('_')]
    
    if hasattr(client, 'get_services'):
        print("✅ 객체에 get_services 메서드 있음")
    else:
        print("❌ 객체에 get_services 메서드 없음")
        print("객체의 서비스 관련 메서드:")
        service_methods = [attr for attr in obj_attrs if 'service' in attr.lower()]
        for method in service_methods:
            print(f"  - {method}")
            
except Exception as e:
    print(f"❌ BleakClient 객체 생성 실패: {e}")
