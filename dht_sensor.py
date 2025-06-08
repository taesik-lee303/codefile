#!/usr/bin/env python3
"""
온습도 센서(DHT11/DHT22) 데이터 수집 및 MQTT 전송
GPIO 22번 핀 사용
"""

import RPi.GPIO as GPIO
import time
import json
from datetime import datetime
from collections import deque
import numpy as np
import threading
from mqtt_sensor_sender import MQTTSensorSender
import mqtt_config

# DHT 센서 라이브러리 임포트 시도
try:
    import Adafruit_DHT
    DHT_AVAILABLE = True
except ImportError:
    print("Adafruit_DHT 라이브러리를 찾을 수 없습니다. 모의 데이터를 사용합니다.")
    DHT_AVAILABLE = False

# GPIO 설정
DHT_PIN = 22  # 온습도 센서 GPIO 핀
DHT_TYPE = Adafruit_DHT.DHT22  # DHT22 센서 (DHT11은 Adafruit_DHT.DHT11)

# 데이터 수집 설정
SAMPLE_INTERVAL = 2.0  # 2초 간격으로 샘플링 (DHT 센서는 빠른 샘플링에 제한이 있음)
AVERAGE_INTERVAL = 5.0  # 5초 평균

class DHTSensor:
    def __init__(self):
        # 데이터 버퍼 (5초 = 약 2-3개 샘플)
        self.temp_buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL) + 1)
        self.humidity_buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL) + 1)
        
        # MQTT 전송기 초기화
        self.mqtt_sender = MQTTSensorSender(
            broker_host=mqtt_config.MQTT_CONFIG["broker_host"],
            broker_port=mqtt_config.MQTT_CONFIG["broker_port"],
            client_id=f"dht_sensor_{int(time.time())}",
            topic_prefix=mqtt_config.MQTT_CONFIG["topic_prefix"]
        )
        
        # 실행 제어
        self.running = False
        self.thread = None
    
    def read_sensor(self):
        """온습도 센서 값 읽기"""
        if not DHT_AVAILABLE:
            # 모의 데이터 생성
            humidity = 50.0 + np.random.normal(0, 5)
            temperature = 25.0 + np.random.normal(0, 2)
            return humidity, temperature
        
        try:
            humidity, temperature = Adafruit_DHT.read_retry(DHT_TYPE, DHT_PIN)
            return humidity, temperature
        except Exception as e:
            print(f"온습도 센서 읽기 오류: {e}")
            return None, None
    
    def collect_data(self):
        """데이터 수집 및 전송 루프"""
        last_average_time = time.time()
        
        while self.running:
            try:
                # 센서 값 읽기
                humidity, temperature = self.read_sensor()
                
                if humidity is not None and temperature is not None:
                    # 유효한 값만 버퍼에 추가
                    if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                        self.humidity_buffer.append(humidity)
                        self.temp_buffer.append(temperature)
                
                # 5초마다 평균 계산 및 전송
                current_time = time.time()
                if current_time - last_average_time >= AVERAGE_INTERVAL:
                    self.calculate_and_send_average()
                    last_average_time = current_time
                
                # 샘플링 간격 대기
                time.sleep(SAMPLE_INTERVAL)
                
            except Exception as e:
                print(f"데이터 수집 오류: {e}")
                time.sleep(1)
    
    def calculate_and_send_average(self):
        """5초 평균 계산 및 MQTT 전송"""
        # 온도 평균 계산 및 전송
        if self.temp_buffer:
            avg_temp = np.mean(list(self.temp_buffer))
            
            # 온도 데이터 생성
            temp_data = {
                "type": "temperature",
                "timestamp": datetime.now().isoformat(),
                "data": round(avg_temp, 1),
                "unit": "°C",
                "samples": len(self.temp_buffer)
            }
            
            # MQTT로 전송
            if self.mqtt_sender.connected:
                topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/temperature"
                self.mqtt_sender.publish_message(topic, temp_data)
                print(f"평균 온도: {round(avg_temp, 1)}°C (샘플: {len(self.temp_buffer)}개)")
        
        # 습도 평균 계산 및 전송
        if self.humidity_buffer:
            avg_humidity = np.mean(list(self.humidity_buffer))
            
            # 습도 데이터 생성
            humidity_data = {
                "type": "humidity",
                "timestamp": datetime.now().isoformat(),
                "data": round(avg_humidity, 1),
                "unit": "%",
                "samples": len(self.humidity_buffer)
            }
            
            # MQTT로 전송
            if self.mqtt_sender.connected:
                topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/humidity"
                self.mqtt_sender.publish_message(topic, humidity_data)
                print(f"평균 습도: {round(avg_humidity, 1)}% (샘플: {len(self.humidity_buffer)}개)")
        
        # 버퍼 초기화
        self.temp_buffer.clear()
        self.humidity_buffer.clear()
    
    def start(self):
        """센서 모니터링 시작"""
        if self.running:
            print("이미 실행 중입니다.")
            return False
        
        # MQTT 연결
        if not self.mqtt_sender.connect():
            print("MQTT 연결 실패")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self.collect_data)
        self.thread.daemon = True
        self.thread.start()
        
        sensor_type = "DHT22" if DHT_TYPE == Adafruit_DHT.DHT22 else "DHT11"
        print(f"온습도 센서({sensor_type}) 모니터링 시작 (GPIO {DHT_PIN})")
        if not DHT_AVAILABLE:
            print("경고: 모의 데이터를 사용합니다!")
        return True
    
    def stop(self):
        """센서 모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        # MQTT 연결 해제
        self.mqtt_sender.disconnect()
        print("온습도 센서 모니터링 중지")


if __name__ == "__main__":
    try:
        sensor = DHTSensor()
        if sensor.start():
            print("온습도 센서 모니터링 중... Ctrl+C로 종료")
            
            # 메인 스레드는 대기
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n사용자에 의해 종료됨")
    finally:
        if 'sensor' in locals():
            sensor.stop()
