#!/usr/bin/env python3
"""
메인 센서 컨트롤러
PIR, 소음, 온습도 센서를 통합 관리하고 MQTT 브로커로 데이터를 전송합니다.
"""

import time
import json
import threading
from datetime import datetime
import paho.mqtt.client as mqtt

# 센서 모듈 import
from pir_sensor import PIRSensor
from sound_sensor import SoundSensor
from temp_humidity_sensor import TempHumiditySensor

class SensorController:
    def __init__(self, mqtt_broker="localhost", mqtt_port=1883):
        """
        센서 컨트롤러 초기화
        Args:
            mqtt_broker (str): MQTT 브로커 주소
            mqtt_port (int): MQTT 브로커 포트
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        
        # 센서 초기화
        try:
            self.pir_sensor = PIRSensor(pin=18)
            self.sound_sensor = SoundSensor(pin=24)
            self.temp_humidity_sensor = TempHumiditySensor(sensor_type='DHT22', pin=4)
            print("모든 센서가 성공적으로 초기화되었습니다.")
        except Exception as e:
            print(f"센서 초기화 오류: {e}")
            raise
        
        # MQTT 클라이언트 초기화
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_publish = self.on_mqtt_publish
        
        # 실행 제어 플래그
        self.running = False
        
        # MQTT 토픽 설정
        self.topics = {
            'pir': 'sensors/pir/motion',
            'sound': 'sensors/sound/detection',
            'sound_level': 'sensors/sound/level',
            'temperature': 'sensors/environment/temperature',
            'humidity': 'sensors/environment/humidity',
            'temp_humidity': 'sensors/environment/temp_humidity'
        }
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            print("MQTT 브로커에 성공적으로 연결되었습니다.")
        else:
            print(f"MQTT 브로커 연결 실패: {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        print("MQTT 브로커 연결이 해제되었습니다.")
    
    def on_mqtt_publish(self, client, userdata, mid):
        """MQTT 발행 콜백"""
        pass  # 필요시 로깅 추가
    
    def connect_mqtt(self):
        """MQTT 브로커 연결"""
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT 연결 오류: {e}")
            return False
    
    def disconnect_mqtt(self):
        """MQTT 브로커 연결 해제"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def publish_sensor_data(self, topic, data):
        """센서 데이터를 MQTT로 발행"""
        try:
            json_data = json.dumps(data, indent=2)
            result = self.mqtt_client.publish(topic, json_data)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"데이터 발행 성공 - 토픽: {topic}")
                print(f"데이터: {json_data}")
            else:
                print(f"데이터 발행 실패 - 토픽: {topic}, 오류코드: {result.rc}")
                
        except Exception as e:
            print(f"MQTT 발행 오류: {e}")
    
    def read_pir_sensor(self):
        """PIR 센서 읽기 스레드"""
        while self.running:
            try:
                pir_data = self.pir_sensor.read_sensor()
                if pir_data:
                    self.publish_sensor_data(self.topics['pir'], pir_data)
                    
                    # 움직임 감지 시 추가 로그
                    if pir_data['motion_detected']:
                        print(f"[PIR] 움직임 감지됨! - {pir_data['timestamp']}")
                
                time.sleep(1)  # 1초마다 체크
                
            except Exception as e:
                print(f"PIR 센서 읽기 오류: {e}")
                time.sleep(5)
    
    def read_sound_sensor(self):
        """소음 센서 읽기 스레드"""
        while self.running:
            try:
                # 즉시 소음 감지
                sound_data = self.sound_sensor.read_sensor()
                if sound_data:
                    self.publish_sensor_data(self.topics['sound'], sound_data)
                    
                    if sound_data['sound_detected']:
                        print(f"[Sound] 소음 감지됨! - {sound_data['timestamp']}")
                
                # 소음 레벨 측정 (5초간)
                sound_level_data = self.sound_sensor.get_sound_level_over_time(duration=3)
                if sound_level_data:
                    self.publish_sensor_data(self.topics['sound_level'], sound_level_data)
                    print(f"[Sound Level] {sound_level_data['sound_percentage']}% - {sound_level_data['timestamp']}")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"소음 센서 읽기 오류: {e}")
                time.sleep(5)
    
    def read_temp_humidity_sensor(self):
        """온습도 센서 읽기 스레드"""
        while self.running:
            try:
                temp_humidity_data = self.temp_humidity_sensor.read_sensor()
                if temp_humidity_data:
                    self.publish_sensor_data(self.topics['temp_humidity'], temp_humidity_data)
                    print(f"[Temp/Humidity] {temp_humidity_data['temperature']}°C, {temp_humidity_data['humidity']}% - {temp_humidity_data['timestamp']}")
                
                time.sleep(30)  # 30초마다 측정
                
            except Exception as e:
                print(f"온습도 센서 읽기 오류: {e}")
                time.sleep(10)
    
    def start_monitoring(self):
        """센서 모니터링 시작"""
        if not self.connect_mqtt():
            print("MQTT 연결 실패로 모니터링을 시작할 수 없습니다.")
            return False
        
        self.running = True
        
        # 각 센서별 스레드 시작
        threads = [
            threading.Thread(target=self.read_pir_sensor, daemon=True),
            threading.Thread(target=self.read_sound_sensor, daemon=True),
            threading.Thread(target=self.read_temp_humidity_sensor, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        print("센서 모니터링이 시작되었습니다.")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        return True
    
    def stop_monitoring(self):
        """센서 모니터링 중지"""
        print("센서 모니터링을 중지합니다...")
        self.running = False
        
        # MQTT 연결 해제
        self.disconnect_mqtt()
        
        # GPIO 정리
        try:
            self.pir_sensor.cleanup()
            self.sound_sensor.cleanup()
        except:
            pass
        
        print("센서 모니터링이 중지되었습니다.")

def main():
    """메인 함수"""
    # MQTT 브로커 설정 (로컬 브로커 사용)
    controller = SensorController(mqtt_broker="localhost", mqtt_port=1883)
    
    try:
        if controller.start_monitoring():
            # 무한 루프로 프로그램 유지
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n프로그램 종료 신호 수신...")
    
    finally:
        controller.stop_monitoring()

if __name__ == "__main__":
    main()