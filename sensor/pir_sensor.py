#!/usr/bin/env python3
"""
PIR 센서 모듈
GPIO를 통해 PIR 센서의 움직임 감지 신호를 읽어옵니다.
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

class PIRSensor:
    def __init__(self, pin=18):
        """
        PIR 센서 초기화
        Args:
            pin (int): PIR 센서가 연결된 GPIO 핀 번호
        """
        self.pin = pin
        self.setup_gpio()
        
    def setup_gpio(self):
        """GPIO 설정"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        print(f"PIR 센서가 GPIO {self.pin}에 설정되었습니다.")
        
    def read_sensor(self):
        """
        PIR 센서 값 읽기
        Returns:
            dict: 센서 데이터 (motion_detected, timestamp)
        """
        try:
            motion_detected = GPIO.input(self.pin)
            timestamp = datetime.now().isoformat()
            
            sensor_data = {
                'sensor_type': 'PIR',
                'motion_detected': bool(motion_detected),
                'timestamp': timestamp,
                'pin': self.pin
            }
            
            return sensor_data
            
        except Exception as e:
            print(f"PIR 센서 읽기 오류: {e}")
            return None
    
    def cleanup(self):
        """GPIO 정리"""
        GPIO.cleanup()
        print("PIR 센서 GPIO 정리 완료")

# 테스트용 메인 함수
if __name__ == "__main__":
    pir = PIRSensor(pin=18)
    
    try:
        print("PIR 센서 테스트 시작... (Ctrl+C로 종료)")
        while True:
            data = pir.read_sensor()
            if data:
                print(f"PIR 데이터: {data}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        pir.cleanup()