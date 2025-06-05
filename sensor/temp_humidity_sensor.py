#!/usr/bin/env python3
"""
온습도 센서 모듈 (DHT22/DHT11)
Adafruit DHT 라이브러리를 사용하여 온도와 습도를 측정합니다.
"""

import time
from datetime import datetime
try:
    import Adafruit_DHT
except ImportError:
    print("Adafruit_DHT 라이브러리가 설치되지 않았습니다.")
    print("설치 명령어: pip install Adafruit-DHT")

class TempHumiditySensor:
    def __init__(self, sensor_type='DHT22', pin=4):
        """
        온습도 센서 초기화
        Args:
            sensor_type (str): 센서 타입 ('DHT22' 또는 'DHT11')
            pin (int): 센서가 연결된 GPIO 핀 번호
        """
        self.pin = pin
        
        # 센서 타입 설정
        if sensor_type.upper() == 'DHT22':
            self.sensor = Adafruit_DHT.DHT22
        elif sensor_type.upper() == 'DHT11':
            self.sensor = Adafruit_DHT.DHT11
        else:
            raise ValueError("지원되지 않는 센서 타입입니다. 'DHT22' 또는 'DHT11'을 사용하세요.")
        
        self.sensor_type = sensor_type.upper()
        print(f"{self.sensor_type} 센서가 GPIO {self.pin}에 설정되었습니다.")
        
    def read_sensor(self):
        """
        온습도 센서 값 읽기
        Returns:
            dict: 센서 데이터 (temperature, humidity, timestamp)
        """
        try:
            humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)
            timestamp = datetime.now().isoformat()
            
            if humidity is not None and temperature is not None:
                sensor_data = {
                    'sensor_type': 'TempHumidity',
                    'temperature': round(temperature, 2),
                    'humidity': round(humidity, 2),
                    'timestamp': timestamp,
                    'pin': self.pin,
                    'sensor_model': self.sensor_type
                }
                return sensor_data
            else:
                print("온습도 센서에서 데이터를 읽을 수 없습니다.")
                return None
                
        except Exception as e:
            print(f"온습도 센서 읽기 오류: {e}")
            return None
    
    def read_multiple_samples(self, samples=3, delay=2):
        """
        여러 번 측정하여 평균값 계산
        Args:
            samples (int): 측정 횟수
            delay (int): 측정 간격 (초)
        Returns:
            dict: 평균 센서 데이터
        """
        try:
            temp_readings = []
            humidity_readings = []
            
            for i in range(samples):
                humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.pin)
                if humidity is not None and temperature is not None:
                    temp_readings.append(temperature)
                    humidity_readings.append(humidity)
                
                if i < samples - 1:  # 마지막 측정이 아니면 대기
                    time.sleep(delay)
            
            if temp_readings and humidity_readings:
                avg_temp = sum(temp_readings) / len(temp_readings)
                avg_humidity = sum(humidity_readings) / len(humidity_readings)
                timestamp = datetime.now().isoformat()
                
                sensor_data = {
                    'sensor_type': 'TempHumidity_Avg',
                    'temperature': round(avg_temp, 2),
                    'humidity': round(avg_humidity, 2),
                    'samples_count': len(temp_readings),
                    'timestamp': timestamp,
                    'pin': self.pin,
                    'sensor_model': self.sensor_type
                }
                return sensor_data
            else:
                print("유효한 온습도 데이터를 얻을 수 없습니다.")
                return None
                
        except Exception as e:
            print(f"온습도 센서 다중 샘플 읽기 오류: {e}")
            return None

# 테스트용 메인 함수
if __name__ == "__main__":
    # DHT22 센서 사용 (DHT11 사용시 'DHT11'로 변경)
    temp_sensor = TempHumiditySensor(sensor_type='DHT22', pin=4)
    
    try:
        print("온습도 센서 테스트 시작... (Ctrl+C로 종료)")
        while True:
            # 단일 측정
            data = temp_sensor.read_sensor()
            if data:
                print(f"온습도 데이터: {data}")
            
            time.sleep(5)
            
            # 평균 측정 (3회)
            avg_data = temp_sensor.read_multiple_samples(samples=3, delay=1)
            if avg_data:
                print(f"평균 온습도: {avg_data}")
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n테스트 종료")