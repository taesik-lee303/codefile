# pi5_ble_central.py
import asyncio
import subprocess
from picamera2 import Picamera2
from bleak import BleakClient

# 1) Pico WH의 MAC 주소 (MicroPython에서 설정한 값과 동일)
PICO_ADDR = "88:A2:9E:02:3B:94"
# 2) Pico WH가 노티파이하는 특성 UUID
CHAR_UUID = "12345678-1234-5678-1234-56789abcdef1"

async def notification_handler(_, data):
    msg = data.decode().strip()
    print(f"[BLE] Received: {msg}")

    if msg == "START":
        await turn_on_peripherals()
    elif msg == "SHUTDOWN":
        await shutdown_pi()

async def turn_on_peripherals():
    print("[ACTION] Turning on camera, mic, speaker, display...")
    # Display (HDMI) 켜기
    subprocess.run(["sudo", "tvservice", "-p"], check=True)
    # Audio unmute
    subprocess.run(["amixer", "set", "Master", "unmute"], check=True)
    # Camera preview 시작
    pc = Picamera2()
    pc.start_preview()
    # (필요 시) mic/speaker 테스트용 명령어 추가 가능
    print("[OK] Peripherals are ON")

async def shutdown_pi():
    print("[ACTION] Noise below threshold for 20s → shutting down...")
    # 안전 종료
    subprocess.run(["sudo", "poweroff"], check=True)

async def main():
    print(f"[BLE] Connecting to {PICO_ADDR} ...")
    async with BleakClient(PICO_ADDR) as client:
        await client.start_notify(CHAR_UUID, notification_handler)
        print("[BLE] Notification handler registered. Waiting...")
        # 무한 대기
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
