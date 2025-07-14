import asyncio
from bleak import BleakScanner

async def find_pico_devices():
    print("BLE 장치 검색 중...")
    
    # 기본 스캔 (가장 안전한 방법)
    devices = await BleakScanner.discover(timeout=10.0)
    
    if not devices:
        print("❌ 장치를 찾지 못했습니다.")
        return []
    
    print(f"총 {len(devices)}개의 BLE 장치 발견:")
    print("=" * 50)
    
    pico_devices = []
    
    for device in devices:
        device_name = device.name or "Unknown"
        print(f"장치명: {device_name}")
        print(f"주소: {device.address}")
        
        # Pico 관련 키워드로 필터링
        if any(keyword in device_name.lower() for keyword in ['pico', 'rpi', 'raspberry', 'esp']):
            pico_devices.append(device)
            print("✅ 잠재적 Pico 장치!")
        
        print("-" * 30)
    
    if pico_devices:
        print(f"\n🎯 Pico 후보 장치 {len(pico_devices)}개 발견!")
    else:
        print("\n❌ Pico 장치를 찾지 못했습니다.")
    
    return pico_devices

if __name__ == "__main__":
    asyncio.run(find_pico_devices())
