# modern_bleak_connect.py
import asyncio
from bleak import BleakClient

async def modern_connect(address):
    print(f"=== Bleak 1.0.1 최신 API 연결 ===")
    print(f"주소: {address}")
    
    client = None
    try:
        # 1. 연결
        print("1. 연결 시도 중...")
        client = BleakClient(address, timeout=20.0)
        await client.connect()
        
        if client.is_connected:
            print("✅ 연결 성공!")
            
            # 2. 기본 정보
            print("2. 장치 정보:")
            print(f"   주소: {client.address}")
            print(f"   MTU 크기: {client.mtu_size}")
            
            # 3. 서비스 정보 (최신 API - services 속성 직접 사용)
            print("3. 서비스 검색 중...")
            
            # 연결 후 잠시 대기 (서비스 검색 시간)
            await asyncio.sleep(2)
            
            if client.services:
                print(f"✅ {len(client.services)} 개의 서비스 발견:")
                
                for service in client.services:
                    print(f"   📋 서비스: {service.uuid}")
                    print(f"      설명: {service.description}")
                    
                    # 특성(Characteristics) 정보
                    if service.characteristics:
                        for char in service.characteristics:
                            print(f"      🔧 특성: {char.uuid}")
                            print(f"         속성: {char.properties}")
                            
                            # 디스크립터 정보
                            if char.descriptors:
                                for desc in char.descriptors:
                                    print(f"         📝 디스크립터: {desc.uuid}")
            else:
                print("⚠️ 서비스를 찾을 수 없습니다.")
            
            # 4. 연결 안정성 및 기능 테스트
            print("4. 연결 기능 테스트:")
            
            # 페어링 시도 (선택사항)
            try:
                print("   페어링 시도 중...")
                await client.pair()
                print("   ✅ 페어링 성공")
            except Exception as e:
                print(f"   ⚠️ 페어링 실패 (정상일 수 있음): {e}")
            
            # 연결 유지 테스트
            print("   연결 안정성 테스트 (20초):")
            stable_count = 0
            for i in range(20):
                await asyncio.sleep(1)
                if client.is_connected:
                    stable_count += 1
                    if i % 4 == 0:
                        print(f"     {i+1}/20 - 연결 안정 ({stable_count}초)")
                else:
                    print(f"     ❌ {i+1}초에 연결 끊어짐!")
                    break
            
            # 결과 평가
            if stable_count >= 18:
                print("   ✅ 연결 매우 안정적!")
            elif stable_count >= 12:
                print("   ⚠️ 연결 보통 안정적")
            else:
                print("   ❌ 연결 불안정")
                
        else:
            print("❌ 연결되지 않음")
            
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 5. 정리
        if client:
            try:
                if client.is_connected:
                    await client.disconnect()
                    print("🔌 연결 해제 완료")
            except Exception as e:
                print(f"연결 해제 중 오류: {e}")

if __name__ == "__main__":
    address = input("Pico WH 주소를 입력하세요: ").strip()
    
    if len(address) == 17 and address.count(':') == 5:
        asyncio.run(modern_connect(address))
    else:
        print("❌ 올바른 형식: AA:BB:CC:DD:EE:FF")
