#!/usr/bin/env python3
"""
센서 데이터 MQTT 전송 클래스
"""

import json
import time
from datetime import datetime
import threading

# MQTT 라이브러리
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("경고: paho-mqtt 라이브러리를 찾을 수 없습니다. MQTT 기능이 비활성화됩니다.")

class MQTTSensorSender:
    def __init__(self, broker_host="localhost", broker_port=1883, 
                 client_id="sensor", topic_prefix="sensors",
                 username=None, password=None):
        """
        MQTT 센서 데이터 전송기 초기화
        
        Args:
            broker_host: MQTT 브로커 호스트
            broker_port: MQTT 브로커 포트
            client_id: MQTT 클라이언트 ID
            topic_prefix: 토픽 접두사
            username: MQTT 인증 사용자명 (선택)
            password: MQTT 인증 비밀번호 (선택)
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.topic_prefix = topic_prefix
        self.username = username
        self.password = password
        
        # MQTT 사용 가능 여부 확인
        if not MQTT_AVAILABLE:
            self.enabled = False
            self.connected = False
            return
        
        self.enabled = True
        self.connected = False
        
        # MQTT 클라이언트 설정
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        # 인증 정보 설정
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            self.connected = True
            print(f"✓ MQTT 연결 성공: {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            print(f"✗ MQTT 연결 실패 (코드: {rc})")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        self.connected = False
        if rc != 0:
            print(f"✗ MQTT 연결이 예기치 않게 종료됨 (코드: {rc})")
        else:
            print("✓ MQTT 연결 해제됨")
    
    def on_publish(self, client, userdata, mid):
        """MQTT 발행 콜백"""
        pass
    
    def connect(self):
        """MQTT 브로커에 연결"""
        if not self.enabled:
            print("MQTT 기능이 비활성화되어 있습니다.")
            return False
            
        try:
            print(f"🔄 MQTT 브로커 연결 중: {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 연결 대기 (최대 5초)
            wait_time = 0
            while not self.connected and wait_time < 5:
                time.sleep(0.1)
                wait_time += 0.1
            
            return self.connected
        except Exception as e:
            print(f"✗ MQTT 연결 오류: {e}")
            return False
    
    def disconnect(self):
        """MQTT 브로커 연결 해제"""
        if self.enabled and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    def publish_message(self, topic, data, qos=0, retain=False):
        """
        MQTT 메시지 발행
        
        Args:
            topic: 메시지 토픽
            data: 전송할 데이터 (dict)
            qos: QoS 레벨 (0, 1, 2)
            retain: 메시지 보존 여부
        """
        if not self.enabled or not self.connected:
            return False
        
        try:
            # 타임스탬프가 없으면 추가
            if isinstance(data, dict) and "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()
            
            # JSON 변환
            payload = json.dumps(data)
            
            # 발행
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            return result.rc == 0
        except Exception as e:
            print(f"✗ 메시지 발행 오류: {e}")
            return False


# 테스트 코드
if __name__ == "__main__":
    # MQTT 설정
    import mqtt_config
    
    sender = MQTTSensorSender(
        broker_host=mqtt_config.MQTT_CONFIG["broker_host"],
        broker_port=mqtt_config.MQTT_CONFIG["broker_port"],
        client_id="test_sender",
        topic_prefix=mqtt_config.MQTT_CONFIG["topic_prefix"]
    )
    
    if sender.connect():
        print("MQTT 연결 성공")
        
        # 테스트 메시지 전송
        test_data = {
            "type": "test",
            "timestamp": datetime.now().isoformat(),
            "data": 42,
            "unit": "test_unit"
        }
        
        topic = f"{mqtt_config.MQTT_CONFIG['topic_prefix']}/test"
        if sender.publish_message(topic, test_data):
            print(f"테스트 메시지 전송 성공: {test_data}")
        else:
            print("테스트 메시지 전송 실패")
        
        # 연결 해제
        time.sleep(1)  # 메시지 전송 대기
        sender.disconnect()
    else:
        print("MQTT 연결 실패")
