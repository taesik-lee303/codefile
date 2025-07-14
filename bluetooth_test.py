import asyncio
from bleak import BleakScanner

async def find_pico_devices():
    print("Raspberry Pi Pico W 장치 검색 중...")
    
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    pico_devices = []
    
    for device, adv_data in devices.items():
        device_name = device.name or ""
        
        # Pico 관련 키워드로 필터링
        if any(keyword in device_name.lower() for keyword in ['pico', 'rpi', 'raspberry']):
            pico_devices.append((device, adv_data))
            print(f"✅ Pico 장치 발견!")
            print(f"   이름: {device_name}")
            print(f"   주소: {device.address}")
            print(f"   신호강도: {adv_data.rssi} dBm")
            print("-" * 30)
    
    if not pico_devices:
        print("❌ Pico 장치를 찾지 못했습니다.")
        print("\n모든 발견된 장치:")
        for device, adv_data in devices.items():
            print(f"  {device.name or 'Unknown'} - {device.address}")
    
    return pico_devices

if __name__ == "__main__":
    asyncio.run(find_pico_devices())
