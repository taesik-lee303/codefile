#!/usr/bin/env python3
"""
디지털 소음 센서 모듈
GPIO를 통해 디지털 소음 센서의 신호를 읽어옵니다.
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

class SoundSensor:
    def __init__(self, pin=24):
        """
        디지털 소음 센서 초기화
        Args:
            pin (int): 소음 센서가 연결된 GPIO 핀 번호
        """
        self.pin = pin
        self.setup_gpio()
        
    def setup_gpio(self):
        """GPIO 설정"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        print(f"디지털 소음 센서가 GPIO {self.pin}에 설정되었습니다.")
        
    def read_sensor(self):
        """
        디지털 소음 센서 값 읽기
        Returns:
            dict: 센서 데이터 (sound_detected, timestamp)
        """
        try:
            sound_detected = GPIO.input(self.pin)
            timestamp = datetime.now().isoformat()
            
            sensor_data = {
                'sensor_type': 'Sound',
                'sound_detected': bool(sound_detected),
                'timestamp': timestamp,
                'pin': self.pin
            }
            
            return sensor_data
            
        except Exception as e:
            print(f"소음 센서 읽기 오류: {e}")
            return None
    
    def get_sound_level_over_time(self, duration=5, interval=0.1):
        """
        일정 시간 동안 소음 감지 빈도 측정
        Args:
            duration (int): 측정 시간 (초)
            interval (float): 측정 간격 (초)
        Returns:
            dict: 소음 레벨 정보
        """
        try:
            detections = 0
            total_samples = int(duration / interval)
            
            for _ in range(total_samples):
                if GPIO.input(self.pin):
                    detections += 1
                time.sleep(interval)
            
            sound_percentage = (detections / total_samples) * 100
            timestamp = datetime.now().isoformat()
            
            sensor_data = {
                'sensor_type': 'Sound_Level',
                'sound_percentage': round(sound_percentage, 2),
                'detections': detections,
                'total_samples': total_samples,
                'duration': duration,
                'timestamp': timestamp,
                'pin': self.pin
            }
            
            return sensor_data
            
        except Exception as e:
            print(f"소음 레벨 측정 오류: {e}")
            return None
    
    def cleanup(self):
        """GPIO 정리"""
        GPIO.cleanup()
        print("소음 센서 GPIO 정리 완료")

# 테스트용 메인 함수
if __name__ == "__main__":
    sound = SoundSensor(pin=24)
    
    try:
        print("디지털 소음 센서 테스트 시작... (Ctrl+C로 종료)")
        while True:
            # 즉시 감지
            data = sound.read_sensor()
            if data:
                print(f"소음 감지: {data}")
            
            # 5초간 소음 레벨 측정
            level_data = sound.get_sound_level_over_time(duration=2)
            if level_data:
                print(f"소음 레벨: {level_data}")
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        sound.cleanup()