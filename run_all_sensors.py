#!/usr/bin/env python3
"""
모든 센서 동시에 실행
"""

import time
import threading
import signal
import sys

# 센서 클래스 임포트
from infrared_sensor import InfraredSensor
from sound_sensor import SoundSensor
from dht_sensor import DHTSensor

# 센서 인스턴스 생성
sensors = {
    "infrared": InfraredSensor(),
    "sound": SoundSensor(),
    "dht": DHTSensor()
}

# 종료 핸들러
def signal_handler(sig, frame):
    print("\n모든 센서 종료 중...")
    for name, sensor in sensors.items():
        print(f"{name} 센서 종료 중...")
        sensor.stop()
    sys.exit(0)

# 메인 함수
def main():
    print("=== 다중 센서 모니터링 시스템 ===")
    print("GPIO 17: 적외선 센서")
    print("GPIO 27: 소음 센서")
    print("GPIO 22: 온습도 센서")
    print("==============================")
    
    # 모든 센서 시작
    for name, sensor in sensors.items():
        print(f"{name} 센서 시작 중...")
        if not sensor.start():
            print(f"{name} 센서 시작 실패!")
    
    # 종료 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("\n모든 센서가 실행 중입니다. Ctrl+C로 종료하세요.")
    
    # 메인 스레드는 대기
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
