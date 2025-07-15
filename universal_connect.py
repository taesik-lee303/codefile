# universal_connect.py
import asyncio
from bleak import BleakClient
import sys

async def universal_connect(address):
    print(f"=== 범용 연결 테스트 ===")
    print(f"Python 버전: {sys.version}")
    
    try:
        import bleak
        print(f"Bleak 버전: {bleak.__version__}")
    except:
        print("Bleak 버전 확인 실패")
    
    client = None
    try:
        print(f"\n🎯 연결 대상: {address}")
        
        # 기본 연결 시도
        client = BleakClient(address)
        print("연결 중...")
        
        await client.connect()
        
        if client.is_connected:
            print("✅ 연결 성공!")
            
            # 버전에 관계없이 안전한 정보 확인
            print(f"주소: {client.address}")
            
            # services 메서드가 있는지 확인 후 사용
            if hasattr(client, 'get_services'):
                print("get_services 메서드 사용 가능")
                try:
                    services = await client.get_services()
                    print(f"서비스 개수: {len(services)}")
                except Exception as e:
                    print(f"서비스 조회 실패: {e}")
            elif hasattr(client, 'services'):
                print("services 속성 사용")
                try:
                    services = client.services
                    if services:
                        print(f"서비스 개수: {len(services)}")
                    else:
                        print("서비스 정보 없음")
                except Exception as e:
                    print(f"서비스 조회 실패: {e}")
            else:
                print("서비스 조회 메서드를 찾을 수 없음")
            
            # 연결 유지 테스트
            print("\n연결 유지 테스트 (15초)...")
            for i in range(15):
                await asyncio.sleep(1)
                if client.is_connected:
                    if i % 3 == 0:
                        print(f"  연결 상태: 정상 ({i+1}/15)")
                else:
                    print(f"  ❌ {i+1}초에 연결 끊어짐!")
                    break
            
            if client.is_connected:
                print("✅ 연결 안정성 테스트 통과!")
            
        else:
            print("❌ 연결 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        
    finally:
        if client and client.is_connected:
            try:
                await client.disconnect()
                print("🔌 연결 해제")
            except:
                pass

if __name__ == "__main__":
    # 실제 Pico 주소 입력
    address = input("Pico WH 주소를 입력하세요 (예: AA:BB:CC:DD:EE:FF): ").strip()
    
    if address and len(address) == 17:
        asyncio.run(universal_connect(address))
    else:
        print("❌ 올바른 주소 형식을 입력하세요 (AA:BB:CC:DD:EE:FF)")
