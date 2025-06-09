#!/usr/bin/env python3
"""
DHT22 온습도 센서 - 라즈베리파이 5 전용
GPIO 22번 핀 사용
"""

import time
import json
from datetime import datetime
from collections import deque
import numpy as np
import threading
import pigpio
import DHT22

# MQTT 옵션
USE_MQTT = True  # False로 설정하면 터미널 출력만

if USE_MQTT:
    try:
        from mqtt_sensor_sender import MQTTSensorSender
        import mqtt_config
    except ImportError:
        print("MQTT 모듈 없음 - 터미널 출력만 사용")
        USE_MQTT = False

# GPIO 설정
DHT_PIN = 22

# 데이터 수집 설정
SAMPLE_INTERVAL = 2.0  # 2초 (DHT 센서 제한)
AVERAGE_INTERVAL = 5.0  # 5초 평균

class DHTSensorRPi5:
    def __init__(self, pin=DHT_PIN):
        self.pin = pin
        self.pi = pigpio.pi()
        self.dht_device = DHT22.sensor(self.pi, self.pin)
        print(f"✓ DHT22 센서 초기화 (GPIO {self.pin})")

        self.temp_buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL) + 1)
        self.humidity_buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL) + 1)

        self.mqtt_sender = None
        if USE_MQTT:
            self.mqtt_sender = MQTTSensorSender(
                broker_host=mqtt_config.MQTT_CONFIG["broker_host"],
                broker_port=mqtt_config.MQTT_CONFIG["broker_port"],
                client_id=f"dht_sensor_{int(time.time())}",
                topic_prefix=mqtt_config.MQTT_CONFIG["topic_prefix"]
            )

        self.running = False
        self.thread = None
    
    def read_sensor(self):
        try:
            self.dht_device.trigger()
            time.sleep(0.2)  # 트리거 후 대기
            temperature = self.dht_device.temperature()
            humidity = self.dht_device.humidity()
            return temperature, humidity
        except Exception as e:
            print(f"센서 오류: {e}")
            return None, None

    
    def collect_data(self):
        """데이터 수집 루프"""
        last_average_time = time.time()
        
        while self.running:
            try:
                temperature, humidity = self.read_sensor()
                
                if temperature is not None and humidity is not None:
                    # 유효한 값만 저장
                    if -40 <= temperature <= 80 and 0 <= humidity <= 100:
                        self.temp_buffer.append(temperature)
                        self.humidity_buffer.append(humidity)
                        
                        # 즉시 값 출력
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                              f"현재: {temperature:.1f}°C, {humidity:.1f}%")
                
                # 5초마다 평균 계산
                current_time = time.time()
                if current_time - last_average_time >= AVERAGE_INTERVAL:
                    self.calculate_and_send_average()
                    last_average_time = current_time
                
                time.sleep(SAMPLE_INTERVAL)
                
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(2)
    
    def calculate_and_send_average(self):
        """5초 평균 계산 및 출력/전송"""
        # 터미널 출력
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 온습도 센서 5초 평균")
        print(f"{'='*50}")
        
        # 온도 평균
        if self.temp_buffer:
            avg_temp = np.mean(list(self.temp_buffer))
            min_temp = np.min(list(self.temp_buffer))
            max_temp = np.max(list(self.temp_buffer))
            print(f"온도: {avg_temp:.1f}°C (최소: {min_temp:.1f}, 최대: {max_temp:.1f})")
            
            # MQTT 전송
            if USE_MQTT and self.mqtt_sender and self.mqtt_sender.connected:
                temp_data = {
                    "type": "temperature",
                    "timestamp": datetime.now().isoformat(),
                    "data": round(avg_temp, 1),
                    "unit": "°C",
                    "samples": len(self.temp_buffer)
                }
                topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/temperature"
                self.mqtt_sender.publish_message(topic, temp_data)
        
        # 습도 평균
        if self.humidity_buffer:
            avg_humidity = np.mean(list(self.humidity_buffer))
            min_humidity = np.min(list(self.humidity_buffer))
            max_humidity = np.max(list(self.humidity_buffer))
            print(f"습도: {avg_humidity:.1f}% (최소: {min_humidity:.1f}, 최대: {max_humidity:.1f})")
            
            # MQTT 전송
            if USE_MQTT and self.mqtt_sender and self.mqtt_sender.connected:
                humidity_data = {
                    "type": "humidity",
                    "timestamp": datetime.now().isoformat(),
                    "data": round(avg_humidity, 1),
                    "unit": "%",
                    "samples": len(self.humidity_buffer)
                }
                topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/humidity"
                self.mqtt_sender.publish_message(topic, humidity_data)
        
        print(f"샘플 수: 온도 {len(self.temp_buffer)}개, 습도 {len(self.humidity_buffer)}개")
        
        if USE_MQTT and self.mqtt_sender and self.mqtt_sender.connected:
            print("✓ MQTT 전송 완료")
        
        print(f"{'='*50}")
        
        # 버퍼 초기화
        self.temp_buffer.clear()
        self.humidity_buffer.clear()
    
    def start(self):
        """모니터링 시작"""
        if self.running:
            return False
        
        # MQTT 연결 (옵션)
        if USE_MQTT and self.mqtt_sender:
            if self.mqtt_sender.connect():
                print("✓ MQTT 연결됨")
            else:
                print("⚠️ MQTT 연결 실패 - 터미널 출력만 사용")
        
        self.running = True
        self.thread = threading.Thread(target=self.collect_data)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"🚀 온습도 센서 모니터링 시작")
        return True
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

        if USE_MQTT and self.mqtt_sender:
            self.mqtt_sender.disconnect()

        self.dht_device.cancel()
        self.pi.stop()
        print("🛑 모니터링 중지")



if __name__ == "__main__":
    # 필요한 라이브러리 설치 안내
    print("필요한 라이브러리:")
    print("sudo apt-get update")
    print("sudo apt-get install python3-libgpiod")
    print("pip3 install adafruit-circuitpython-dht")
    print("")
    
    sensor = DHTSensorRPi5()
    
    try:
        sensor.start()
        print("\n모니터링 중... Ctrl+C로 종료\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n종료 중...")
    finally:
        sensor.stop()
