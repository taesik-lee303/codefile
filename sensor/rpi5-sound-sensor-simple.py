#!/usr/bin/env python3
"""
소음 센서 - 라즈베리파이 5 전용
GPIO 27번 핀 사용
"""

import time
import json
from datetime import datetime
from collections import deque
import numpy as np
import threading
import gpiod

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
SOUND_PIN = 27
CHIP_NAME = 'gpiochip4'  # 라즈베리파이 5

# 데이터 수집 설정
SAMPLE_INTERVAL = 0.1  # 100ms
AVERAGE_INTERVAL = 5.0  # 5초 평균

class SoundSensorRPi5:
    def __init__(self, pin=SOUND_PIN):
        self.pin = pin
        self.chip = gpiod.Chip(CHIP_NAME)
        self.line = self.chip.get_line(self.pin)
        
        # GPIO 설정
        config = gpiod.line_request()
        config.consumer = "sound_sensor"
        config.request_type = gpiod.line_request.DIRECTION_INPUT
        self.line.request(config)
        
        print(f"✓ 소음 센서 초기화 (GPIO {self.pin})")
        
        # 데이터 버퍼
        self.buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL))
        self.event_counter = 0
        self.last_reset_time = time.time()
        
        # MQTT 설정
        self.mqtt_sender = None
        if USE_MQTT:
            self.mqtt_sender = MQTTSensorSender(
                broker_host=mqtt_config.MQTT_CONFIG["broker_host"],
                broker_port=mqtt_config.MQTT_CONFIG["broker_port"],
                client_id=f"sound_sensor_{int(time.time())}",
                topic_prefix=mqtt_config.MQTT_CONFIG["topic_prefix"]
            )
        
        self.running = False
        self.thread = None
    
    def read_sensor(self):
        """센서 값 읽기"""
        return self.line.get_value()
    
    def collect_data(self):
        """데이터 수집 루프"""
        last_average_time = time.time()
        
        while self.running:
            try:
                value = self.read_sensor()
                self.buffer.append(value)
                
                if value == 1:  # 소음 감지
                    self.event_counter += 1
                
                # 5초마다 평균 계산
                current_time = time.time()
                if current_time - last_average_time >= AVERAGE_INTERVAL:
                    self.calculate_and_send_average()
                    last_average_time = current_time
                
                time.sleep(SAMPLE_INTERVAL)
                
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(1)
    
    def calculate_and_send_average(self):
        """5초 평균 계산 및 출력/전송"""
        if not self.buffer:
            return
        
        # 평균 계산
        detection_count = sum(self.buffer)
        total_samples = len(self.buffer)
        detection_ratio = detection_count / total_samples if total_samples > 0 else 0
        noise_level = round(detection_ratio * 100, 1)
        
        # 초당 이벤트
        current_time = time.time()
        elapsed_time = current_time - self.last_reset_time
        events_per_second = round(self.event_counter / elapsed_time, 2) if elapsed_time > 0 else 0
        
        # 터미널 출력
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 소음 센서 데이터")
        print(f"{'='*50}")
        print(f"소음 레벨: {noise_level}%")
        print(f"감지 횟수: {detection_count}/{total_samples}")
        print(f"총 이벤트: {self.event_counter}개")
        print(f"초당 이벤트: {events_per_second}/초")
        print(f"{'='*50}")
        
        # MQTT 전송
        if USE_MQTT and self.mqtt_sender and self.mqtt_sender.connected:
            sensor_data = {
                "type": "sound",
                "timestamp": datetime.now().isoformat(),
                "data": noise_level,
                "unit": "level",
                "events_per_second": events_per_second,
                "total_events": self.event_counter
            }
            topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/sound"
            self.mqtt_sender.publish_message(topic, sensor_data)
            print("✓ MQTT 전송 완료")
        
        # 버퍼 초기화
        self.buffer.clear()
        self.event_counter = 0
        self.last_reset_time = current_time
    
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
        
        print(f"🚀 소음 센서 모니터링 시작")
        return True
    
    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if USE_MQTT and self.mqtt_sender:
            self.mqtt_sender.disconnect()
        
        self.line.release()
        self.chip.close()
        print("🛑 모니터링 중지")


if __name__ == "__main__":
    sensor = SoundSensorRPi5()
    
    try:
        sensor.start()
        print("\n모니터링 중... Ctrl+C로 종료\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n종료 중...")
    finally:
        sensor.stop()
