import asyncio
from bleak import BleakScanner

class DeviceInfo:
    def __init__(self, device, advertisement_data):
        self.device = device
        self.advertisement_data = advertisement_data

detected_devices = []

def detection_callback(device, advertisement_data):
    """실시간으로 장치를 감지할 때 호출되는 콜백"""
    device_info = DeviceInfo(device, advertisement_data)
    detected_devices.append(device_info)
    
    device_name = device.name or "Unknown"
    print(f"발견: {device_name}")
    print(f"  주소: {device.address}")
    print(f"  신호강도: {advertisement_data.rssi} dBm")
    
    # Pico 장치인지 확인
    if any(keyword in device_name.lower() for keyword in ['pico', 'rpi', 'raspberry']):
        print("  ✅ Pico 장치 가능성!")
    
    print("-" * 40)

async def scan_with_rssi():
    global detected_devices
    detected_devices = []  # 리스트 초기화
    
    print("RSSI 정보와 함께 BLE 스캔 시작...")
    print("10초간 스캔합니다...")
    
    scanner = BleakScanner(detection_callback)
    
    try:
        await scanner.start()
        await asyncio.sleep(10.0)  # 10초간 스캔
        await scanner.stop()
        
        print(f"\n스캔 완료! 총 {len(detected_devices)}개 장치 발견")
        
        # Pico 장치 필터링
        pico_devices = []
        for device_info in detected_devices:
            device_name = device_info.device.name or ""
            if any(keyword in device_name.lower() for keyword in ['pico', 'rpi', 'raspberry']):
                pico_devices.append(device_info)
        
        if pico_devices:
            print(f"\n🎯 Pico 후보 장치 {len(pico_devices)}개:")
            for device_info in pico_devices:
                print(f"  {device_info.device.name} - {device_info.device.address}")
                print(f"  신호강도: {device_info.advertisement_data.rssi} dBm")
        
        return pico_devices
        
    except Exception as e:
        print(f"스캔 오류: {e}")
        await scanner.stop()
        return []

if __name__ == "__main__":
    asyncio.run(scan_with_rssi())
