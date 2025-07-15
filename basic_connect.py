# basic_connect.py
import asyncio
from bleak import BleakClient

async def basic_connect_test(address):
    print(f"=== 기본 연결 테스트 ===")
    print(f"주소: {address}")
    
    client = None
    try:
        # 1. 클라이언트 생성
        print("1. BleakClient 생성 중...")
        client = BleakClient(address, timeout=20.0)
        
        # 2. 연결 시도
        print("2. 연결 시도 중...")
        await client.connect()
        
        # 3. 연결 상태 확인
        print("3. 연결 상태 확인...")
        if client.is_connected:
            print("✅ 연결 성공!")
            
            # 4. 기본 정보만 확인 (get_services 사용하지 않음)
            print("4. 기본 정보:")
            print(f"   주소: {client.address}")
            print(f"   연결됨: {client.is_connected}")
            
            # 5. 연결 유지 테스트
            print("5. 연결 유지 테스트 (10초)...")
            for i in range(10):
                await asyncio.sleep(1)
                if client.is_connected:
                    print(f"   {i+1}/10 - 연결 유지됨")
                else:
                    print(f"   {i+1}/10 - 연결 끊어짐!")
                    break
            
            print("✅ 기본 연결 테스트 완료!")
        else:
            print("❌ 연결되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        
    finally:
        # 6. 연결 해제
        if client:
            try:
                await client.disconnect()
                print("🔌 연결 해제 완료")
            except Exception as e:
                print(f"연결 해제 중 오류: {e}")

# 사용법
if __name__ == "__main__":
    # 여기에 실제 Pico 주소 입력
    PICO_ADDRESS = "XX:XX:XX:XX:XX:XX"  # 실제 주소로 교체
    
    if PICO_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("❌ PICO_ADDRESS를 실제 주소로 교체하세요!")
    else:
        asyncio.run(basic_connect_test(PICO_ADDRESS))
