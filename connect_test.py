# connect_test.py
import asyncio
from bleak import BleakClient, BleakScanner

async def connect_to_pico():
    print("=== Pico WH 연결 테스트 ===")
    
    # 1. 먼저 Pico 장치 찾기
    print("1. 장치 검색 중...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    pico_address = None
    for device in devices:
        name = device.name or ""
        if any(keyword in name.lower() for keyword in ['pico', 'mypico']) or \
           len([d for d in devices if d.name]) < 3:  # 이름이 있는 장치가 적으면 Unknown도 시도
            print(f"   후보 장치: {name or 'Unknown'} - {device.address}")
            pico_address = device.address
            break
    
    if not pico_address:
        print("❌ Pico 장치를 찾지 못했습니다.")
        return
    
    print(f"2. 연결 시도: {pico_address}")
    
    # 2. 연결 시도
    try:
        async with BleakClient(pico_address) as client:
            print(f"✅ 연결 성공!")
            print(f"   연결 상태: {client.is_connected}")
            
            # 3. 기본 정보 확인
            print("3. 장치 정보:")
            try:
                device_name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                print(f"   장치명: {device_name.decode()}")
            except:
                print("   장치명: 읽을 수 없음")
            
            # 4. 서비스 목록 확인
            print("4. 사용 가능한 서비스:")
            services = await client.get_services()
            for service in services:
                print(f"   서비스: {service.uuid}")
            
            # 5. 연결 유지 테스트
            print("5. 연결 유지 테스트 (10초)...")
            for i in range(10):
                await asyncio.sleep(1)
                if client.is_connected:
                    print(f"   연결 상태: OK ({i+1}/10)")
                else:
                    print("   연결 끊어짐!")
                    break
                    
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        print("   Pico WH가 연결을 받을 준비가 되었는지 확인하세요.")

if __name__ == "__main__":
    asyncio.run(connect_to_pico())
