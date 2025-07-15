# scan_test.py
import asyncio
from bleak import BleakScanner

async def scan_devices():
    print("=== BLE 장치 스캔 시작 ===")
    print("10초간 스캔합니다...")
    
    devices = await BleakScanner.discover(timeout=10.0)
    
    print(f"\n📱 발견된 장치: {len(devices)}개")
    print("=" * 50)
    
    if devices:
        for i, device in enumerate(devices, 1):
            print(f"{i}. 주소: {device.address}")
            print(f"   이름: {device.name or 'Unknown'}")
            print("-" * 30)
    else:
        print("❌ 장치를 찾지 못했습니다.")
    
    return devices

if __name__ == "__main__":
    print("Ctrl+C로 중지할 수 있습니다.")
    try:
        asyncio.run(scan_devices())
    except KeyboardInterrupt:
        print("\n스캔 중지됨")
