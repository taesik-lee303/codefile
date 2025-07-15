# connect_direct.py
import asyncio
from bleak import BleakClient

async def connect_to_address(address):
    print(f"=== 직접 연결 테스트 ===")
    print(f"주소: {address}")
    
    try:
        print("연결 시도 중...")
        async with BleakClient(address, timeout=20.0) as client:
            print("✅ 연결 성공!")
            print(f"연결 상태: {client.is_connected}")
            
            # 장치 정보 수집
            print("\n📋 장치 정보:")
            print(f"주소: {client.address}")
            
            # 서비스 확인
            print("\n🔧 서비스 목록:")
            services = await client.get_services()
            if services:
                for service in services:
                    print(f"  - {service.uuid}")
                    for char in service.characteristics:
                        print(f"    └ 특성: {char.uuid}")
            else:
                print("  서비스를 찾을 수 없습니다.")
            
            # 연결 유지 테스트
            print("\n⏱️ 연결 유지 테스트 (15초)...")
            for i in range(15):
                await asyncio.sleep(1)
                if client.is_connected:
                    print(f"  연결 상태: 정상 ({i+1}/15)")
                else:
                    print("  ❌ 연결이 끊어졌습니다!")
                    break
                    
            print("연결 테스트 완료!")
            
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        print("가능한 원인:")
        print("  - Pico WH가 연결 모드가 아님")
        print("  - 주소가 잘못됨")
        print("  - 거리가 너무 멀음")

# 사용법: scan_test.py에서 찾은 주소를 여기에 입력
if __name__ == "__main__":
    # 여기에 scan_test.py에서 찾은 Pico의 주소를 입력하세요
    PICO_ADDRESS = "XX:XX:XX:XX:XX:XX"  # 실제 주소로 교체
    
    if PICO_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("❌ PICO_ADDRESS를 실제 주소로 교체하세요!")
        print("scan_test.py를 다시 실행해서 주소를 확인하세요.")
    else:
        asyncio.run(connect_to_address(PICO_ADDRESS))
