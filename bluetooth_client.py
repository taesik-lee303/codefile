import bluetooth
import time

def scan_devices():
    print("블루투스 장치 검색 중...")
    devices = bluetooth.discover_devices(lookup_names=True)
    
    for addr, name in devices:
        print(f"발견된 장치: {name} - {addr}")
        if "PicoWH" in name:
            return addr
    return None

def connect_to_pico():
    pico_addr = scan_devices()
    
    if pico_addr:
        try:
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            sock.connect((pico_addr, 1))
            print(f"Pico WH에 연결됨: {pico_addr}")
            return sock
        except Exception as e:
            print(f"연결 실패: {e}")
    else:
        print("Pico WH를 찾을 수 없습니다")
    return None

# 연결 시도
connection = connect_to_pico()
