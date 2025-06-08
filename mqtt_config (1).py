#!/usr/bin/env python3
"""
MQTT 설정 파일
"""

# MQTT 브로커 설정
MQTT_CONFIG = {
    "broker_host": "localhost",  # MQTT 브로커 주소 (실제 환경에 맞게 변경)
    "broker_port": 1883,         # MQTT 브로커 포트
    "username": None,            # 인증 필요시 사용자명
    "password": None,            # 인증 필요시 비밀번호
    "topic_prefix": "sensors",   # 토픽 접두사
    "qos": 0,                    # QoS 레벨 (0, 1, 2)
    "retain": False              # 메시지 보존 여부
}

# 센서별 설정
SENSOR_CONFIG = {
    "infrared": {
        "pin": 17,
        "sample_interval": 0.1,  # 100ms
        "average_interval": 5.0  # 5초
    },
    "sound": {
        "pin": 27,
        "sample_interval": 0.1,  # 100ms
        "average_interval": 5.0  # 5초
    },
    "dht": {
        "pin": 22,
        "type": "DHT22",         # DHT11 또는 DHT22
        "sample_interval": 2.0,  # 2초 (DHT 센서는 빠른 샘플링에 제한이 있음)
        "average_interval": 5.0  # 5초
    }
}

# 메시지 형식 예제
MESSAGE_EXAMPLES = {
    "temperature": {
        "type": "temperature",
        "timestamp": "2023-01-01T12:00:00.000Z",
        "data": 25.5,
        "unit": "°C",
        "samples": 3
    },
    "humidity": {
        "type": "humidity",
        "timestamp": "2023-01-01T12:00:00.000Z",
        "data": 45.2,
        "unit": "%",
        "samples": 3
    },
    "infrared": {
        "type": "infrared",
        "timestamp": "2023-01-01T12:00:00.000Z",
        "data": 65.0,
        "unit": "%",
        "raw_count": 32,
        "total_samples": 50
    },
    "sound": {
        "type": "sound",
        "timestamp": "2023-01-01T12:00:00.000Z",
        "data": 42.5,
        "unit": "level",
        "events_per_second": 3.2,
        "total_events": 16
    }
}

# 설정 로드 메시지
print(f"MQTT 설정 로드됨: {MQTT_CONFIG['broker_host']}:{MQTT_CONFIG['broker_port']}")
print(f"토픽 접두사: {MQTT_CONFIG['topic_prefix']}")
