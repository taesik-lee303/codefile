#!/usr/bin/env python3
"""
적외선 센서 데이터 수집 및 MQTT 전송
GPIO 17번 핀 사용 - 라즈베리파이 5 호환
"""

import time
import json
from datetime import datetime
from collections import deque
import numpy as np
import threading

# GPIO 라이브러리 선택 (라즈베리파이 5 호환)
GPIO_LIB = None
IS_RASPBERRY_PI = False

# gpiod 라이브러리 시도 (라즈베리파이 5 권장)
try:
    import gpiod
    GPIO_LIB = "gpiod"
    IS_RASPBERRY_PI = True
    print("✓ gpiod 라이브러리 사용 (라즈베리파이 5 호환)")
except ImportError:
    # RPi.GPIO 시도 (이전 버전 호환)
    try:
        import RPi.GPIO as GPIO
        GPIO_LIB = "RPi.GPIO"
        IS_RASPBERRY_PI = True
        print("✓ RPi.GPIO 라이브러리 사용 (이전 라즈베리파이 호환)")
    except ImportError:
        print("⚠️ GPIO 라이브러리를 찾을 수 없습니다. Mock 모드로 실행합니다.")
        IS_RASPBERRY_PI = False

from mqtt_sensor_sender import MQTTSensorSender
import mqtt_config

# GPIO 설정
INFRARED_PIN = 17  # 적외선 센서 GPIO 핀

# 데이터 수집 설정
SAMPLE_INTERVAL = 0.1  # 100ms 간격으로 샘플링
AVERAGE_INTERVAL = 5.0  # 5초 평균

class InfraredSensor:
    def __init__(self):
        self.chip = None
        self.line = None
        self.is_pi = IS_RASPBERRY_PI  # 클래스 변수로 복사
        self.gpio_lib = GPIO_LIB
        
        # GPIO 초기화
        if self.is_pi:
            try:
                if self.gpio_lib == "gpiod":
                    # gpiod 초기화 (라즈베리파이 5)
                    try:
                        self.chip = gpiod.Chip('gpiochip4')  # 라즈베리파이 5
                    except:
                        self.chip = gpiod.Chip('gpiochip0')  # 이전 버전 fallback
                    
                    self.line = self.chip.get_line(INFRARED_PIN)
                    self.line.request(consumer="infrared_sensor", type=gpiod.LINE_REQ_DIR_IN)
                    print(f"✓ gpiod로 적외선 센서 초기화 완료 (GPIO {INFRARED_PIN})")
                    
                elif self.gpio_lib == "RPi.GPIO":
                    # RPi.GPIO 초기화
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(INFRARED_PIN, GPIO.IN)
                    print(f"✓ RPi.GPIO로 적외선 센서 초기화 완료 (GPIO {INFRARED_PIN})")
                    
            except Exception as e:
                print(f"✗ GPIO 초기화 실패: {e}")
                print("⚠️ Mock 모드로 전환합니다.")
                self.is_pi = False
                if self.chip:
                    self.chip.close()
        else:
            print(f"🔧 Mock 모드: 적외선 센서 시뮬레이션 (GPIO {INFRARED_PIN})")
        
        # 데이터 버퍼 (5초 = 50개 샘플)
        self.buffer = deque(maxlen=int(AVERAGE_INTERVAL / SAMPLE_INTERVAL))
        
        # MQTT 전송기 초기화
        self.mqtt_sender = MQTTSensorSender(
            broker_host=mqtt_config.MQTT_CONFIG["broker_host"],
            broker_port=mqtt_config.MQTT_CONFIG["broker_port"],
            client_id=f"infrared_sensor_{int(time.time())}",
            topic_prefix=mqtt_config.MQTT_CONFIG["topic_prefix"]
        )
        
        # 실행 제어
        self.running = False
        self.thread = None
    
    def read_sensor(self):
        """적외선 센서 값 읽기"""
        if not self.is_pi:
            # Mock 데이터
            import random
            return random.choice([0, 0, 0, 1])  # 25% 확률로 감지
            
        try:
            if self.gpio_lib == "gpiod":
                value = self.line.get_value()
            elif self.gpio_lib == "RPi.GPIO":
                value = GPIO.input(INFRARED_PIN)
            return value
        except Exception as e:
            print(f"✗ 적외선 센서 읽기 오류: {e}")
            return None
    
    def collect_data(self):
        """데이터 수집 및 전송 루프"""
        last_average_time = time.time()
        
        while self.running:
            try:
                # 센서 값 읽기
                value = self.read_sensor()
                if value is not None:
                    self.buffer.append(value)
                
                # 5초마다 평균 계산 및 전송
                current_time = time.time()
                if current_time - last_average_time >= AVERAGE_INTERVAL:
                    self.calculate_and_send_average()
                    last_average_time = current_time
                
                # 샘플링 간격 대기
                time.sleep(SAMPLE_INTERVAL)
                
            except Exception as e:
                print(f"✗ 데이터 수집 오류: {e}")
                time.sleep(1)
    
    def calculate_and_send_average(self):
        """5초 평균 계산 및 MQTT 전송"""
        if not self.buffer:
            return
        
        # 평균 계산 (0: 감지 없음, 1: 감지)
        detection_count = sum(self.buffer)
        total_samples = len(self.buffer)
        detection_ratio = detection_count / total_samples if total_samples > 0 else 0
        
        # 감지 비율을 백분율로 변환
        detection_percent = round(detection_ratio * 100, 1)
        
        # 센서 데이터 생성
        sensor_data = {
            "type": "infrared",
            "timestamp": datetime.now().isoformat(),
            "data": detection_percent,
            "unit": "%",
            "raw_count": detection_count,
            "total_samples": total_samples,
            "device_mode": "real" if self.is_pi else "mock",
            "gpio_lib": self.gpio_lib if self.is_pi else "none"
        }
        
        # MQTT로 전송
        if self.mqtt_sender.connected:
            topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/infrared"
            self.mqtt_sender.publish_message(topic, sensor_data)
            mode_text = f" ({self.gpio_lib})" if self.is_pi else " (Mock)"
            print(f"📡 적외선 감지율{mode_text}: {detection_percent}% ({detection_count}/{total_samples})")
        
        # 버퍼 초기화
        self.buffer.clear()
    
    def start(self):
        """센서 모니터링 시작"""
        if self.running:
            print("⚠️ 이미 실행 중입니다.")
            return False
        
        # MQTT 연결
        if not self.mqtt_sender.connect():
            print("✗ MQTT 연결 실패")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self.collect_data)
        self.thread.daemon = True
        self.thread.start()
        
        lib_text = self.gpio_lib if self.is_pi else "Mock"
        print(f"🚀 적외선 센서 모니터링 시작 ({lib_text}, GPIO {INFRARED_PIN})")
        return True
    
    def stop(self):
        """센서 모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        # MQTT 연결 해제
        self.mqtt_sender.disconnect()
        
        # GPIO 정리
        if self.is_pi:
            try:
                if self.gpio_lib == "gpiod" and self.line:
                    self.line.release()
                    if self.chip:
                        self.chip.close()
                elif self.gpio_lib == "RPi.GPIO":
                    GPIO.cleanup(INFRARED_PIN)
            except:
                pass
        print("🛑 적외선 센서 모니터링 중지")


if __name__ == "__main__":
    try:
        sensor = InfraredSensor()
        if sensor.start():
            print("🔍 적외선 센서 모니터링 중... Ctrl+C로 종료")
            
            # 메인 스레드는 대기
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 종료됨")
    finally:
        if 'sensor' in locals():
            sensor.stop()
