#!/usr/bin/env python3
"""
Raspberry Pi AI Camera를 사용한 얼굴 트래킹 + 생체신호 측정 + MQTT 전송 시스템
라즈베리파이 5 호환 버전 (gpiod 라이브러리 우선 사용)
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import sys
import threading
from collections import deque
import json
from datetime import datetime

# MQTT 라이브러리
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Warning: paho-mqtt not installed. MQTT functionality disabled.")

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

# 기존 모듈 import
try:
    if IS_RASPBERRY_PI:
        from servo_face_tracker_pi import FaceTracker, PIDController
    else:
        from servo_face_tracker_test import FaceTracker, PIDController
except ImportError:
    print("Warning: servo_face_tracker module not found")
    # 기본 FaceTracker 클래스 정의
    class FaceTracker:
        pass
    class PIDController:
        pass

# rPPG 모듈 import
try:
    from rppg_addon import rPPGProcessor
    from stress_analyzer import StressAnalyzer
    from spo2_estimator import SpO2Estimator
    BIOMETRICS_AVAILABLE = True
except ImportError:
    print("Warning: Biometrics modules not found - using mock classes")
    BIOMETRICS_AVAILABLE = False
    
    # Mock 클래스들
    class rPPGProcessor:
        def __init__(self, fps=30): pass
        def process_frame(self, frame, bbox): pass
        def get_heart_rate(self): return 0, 0
        def reset(self): pass
        def draw_roi(self, frame): pass
        def draw_heart_rate(self, frame, x=0, y=0): pass
        def draw_signal_plot(self, frame, x=0, y=0): pass
    
    class StressAnalyzer:
        def __init__(self): pass
        def update_heart_rate(self, hr): pass
        def get_stress_data(self): return {'stress_index': 0}
        def reset(self): pass
        def draw_stress_info(self, frame, x=0, y=0): pass
    
    class SpO2Estimator:
        def __init__(self, fps=30): pass
        def process_frame(self, frame, bbox): pass
        def get_spo2_data(self): return {'spo2': 0}
        def reset(self): pass
        def draw_spo2_info(self, frame, x=0, y=0): pass


class MQTTBiometricsSender:
    """MQTT 생체신호 전송기"""
    
    def __init__(self, broker_host="localhost", broker_port=1883, 
                 client_id="biometrics_sensor", topic_prefix="biometrics"):
        """
        MQTT 생체신호 전송기 초기화
        
        Args:
            broker_host: MQTT 브로커 호스트
            broker_port: MQTT 브로커 포트
            client_id: MQTT 클라이언트 ID
            topic_prefix: 토픽 접두사
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.topic_prefix = topic_prefix
        
        # MQTT 사용 가능 여부 확인
        if not MQTT_AVAILABLE:
            self.enabled = False
            return
        
        self.enabled = True
        
        # MQTT 클라이언트 설정
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        
        # 연결 상태
        self.connected = False
        
        # 데이터 버퍼 (최근 값들의 평균을 위해)
        self.hr_buffer = deque(maxlen=30)  # 1초 평균 (30fps 기준)
        self.stress_buffer = deque(maxlen=30)
        self.spo2_buffer = deque(maxlen=30)
        
        # 전송 간격 (초)
        self.send_interval = 5.0
        self.last_send_time = 0
        
        # 스레드 제어
        self.running = False
        self.send_thread = None
        
    def on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            self.connected = True
            print(f"✓ MQTT Connected to {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False
            print(f"✗ MQTT Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        self.connected = False
        print("✗ MQTT Disconnected")
    
    def on_publish(self, client, userdata, mid):
        """MQTT 발행 콜백"""
        print(f"📤 Message published (mid: {mid})")
    
    def connect(self):
        """MQTT 브로커에 연결"""
        if not self.enabled:
            return False
            
        try:
            print(f"🔄 Connecting to MQTT broker {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 연결 대기 (최대 5초)
            wait_time = 0
            while not self.connected and wait_time < 5:
                time.sleep(0.1)
                wait_time += 0.1
            
            return self.connected
        except Exception as e:
            print(f"✗ MQTT connection error: {e}")
            return False
    
    def disconnect(self):
        """MQTT 브로커 연결 해제"""
        self.running = False
        if self.send_thread:
            self.send_thread.join()
        
        if self.enabled and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
        print("✓ MQTT Disconnected")
    
    def add_biometric_data(self, heart_rate=None, stress_index=None, spo2=None):
        """
        생체신호 데이터 추가
        
        Args:
            heart_rate: 심박수 (BPM)
            stress_index: 스트레스 지수 (%)
            spo2: 산소포화도 (%)
        """
        if not self.enabled:
            return
            
        if heart_rate is not None and 40 <= heart_rate <= 180:
            self.hr_buffer.append(heart_rate)
        
        if stress_index is not None and stress_index > 0:
            self.stress_buffer.append(stress_index)
        
        if spo2 is not None and 85 <= spo2 <= 100:
            self.spo2_buffer.append(spo2)
    
    def get_averaged_data(self):
        """버퍼된 데이터의 평균값 계산"""
        avg_hr = np.mean(list(self.hr_buffer)) if self.hr_buffer else None
        avg_stress = np.mean(list(self.stress_buffer)) if self.stress_buffer else None
        avg_spo2 = np.mean(list(self.spo2_buffer)) if self.spo2_buffer else None
        
        return avg_hr, avg_stress, avg_spo2
    
    def create_sensor_message(self, sensor_type, value, unit=""):
        """센서 메시지 생성"""
        return {
            "type": sensor_type,
            "timestamp": datetime.now().isoformat(),
            "data": value if value is not None else "-",
            "unit": unit,
            "device_id": self.client_id,
            "gpio_lib": GPIO_LIB if IS_RASPBERRY_PI else "none"
        }
    
    def send_biometrics(self):
        """생체신호 데이터를 MQTT로 전송"""
        if not self.enabled or not self.connected:
            return
        
        avg_hr, avg_stress, avg_spo2 = self.get_averaged_data()
        
        # 심박수 전송
        if avg_hr is not None:
            hr_message = self.create_sensor_message("heart_rate", round(avg_hr, 1), "BPM")
            topic = f"{self.topic_prefix}/heart_rate"
            self.client.publish(topic, json.dumps(hr_message))
            print(f"📤 Heart Rate: {avg_hr:.1f} BPM")
        
        # 스트레스 지수 전송
        if avg_stress is not None:
            stress_message = self.create_sensor_message("stress_index", round(avg_stress, 1), "%")
            topic = f"{self.topic_prefix}/stress"
            self.client.publish(topic, json.dumps(stress_message))
            print(f"📤 Stress Index: {avg_stress:.1f}%")
        
        # 산소포화도 전송
        if avg_spo2 is not None:
            spo2_message = self.create_sensor_message("spo2", round(avg_spo2, 1), "%")
            topic = f"{self.topic_prefix}/spo2"
            self.client.publish(topic, json.dumps(spo2_message))
            print(f"📤 SpO2: {avg_spo2:.1f}%")
        
        # 통합 메시지 전송
        combined_message = {
            "type": "biometrics_combined",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "heart_rate": round(avg_hr, 1) if avg_hr is not None else "-",
                "stress_index": round(avg_stress, 1) if avg_stress is not None else "-",
                "spo2": round(avg_spo2, 1) if avg_spo2 is not None else "-"
            },
            "units": {
                "heart_rate": "BPM",
                "stress_index": "%",
                "spo2": "%"
            },
            "device_id": self.client_id,
            "gpio_lib": GPIO_LIB if IS_RASPBERRY_PI else "none"
        }
        
        combined_topic = f"{self.topic_prefix}/combined"
        self.client.publish(combined_topic, json.dumps(combined_message))
        print(f"📤 Combined biometrics sent")
        
        # 버퍼 초기화
        self.hr_buffer.clear()
        self.stress_buffer.clear()
        self.spo2_buffer.clear()
    
    def send_loop(self):
        """주기적 전송 루프"""
        while self.running:
            current_time = time.time()
            
            if current_time - self.last_send_time >= self.send_interval:
                try:
                    self.send_biometrics()
                    self.last_send_time = current_time
                except Exception as e:
                    print(f"✗ Send error: {e}")
            
            time.sleep(0.1)
    
    def start_sending(self):
        """전송 시작"""
        if not self.enabled or not self.connected:
            return False
        
        self.running = True
        self.send_thread = threading.Thread(target=self.send_loop, daemon=True)
        self.send_thread.start()
        print(f"✓ MQTT sending started (interval: {self.send_interval}s)")
        return True
    
    def stop_sending(self):
        """전송 중지"""
        self.running = False
        if self.send_thread:
            self.send_thread.join()
        print("✓ MQTT sending stopped")


class AICamera:
    """Picamera2를 OpenCV VideoCapture 인터페이스로 래핑"""
    
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.picam2 = None
        self.started = False
        
    def start(self):
        """카메라 시작"""
        try:
            self.picam2 = Picamera2()
            
            # AI 카메라 최적 설정
            config = self.picam2.create_preview_configuration(
                main={
                    "size": (self.width, self.height),
                    "format": "RGB888"
                },
                controls={
                    "FrameRate": self.fps,
                    "AeEnable": True,
                    "AwbEnable": True,
                    "NoiseReductionMode": 1
                }
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.started = True
            
            # 카메라 안정화 대기
            time.sleep(2)
            print(f"✓ AI Camera started: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            return False
    
    def read(self):
        """프레임 읽기 (VideoCapture 호환)"""
        if not self.started:
            return False, None
            
        try:
            frame = self.picam2.capture_array()
            # RGB를 BGR로 변환 (OpenCV 호환성)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame_bgr
        except:
            return False, None
    
    def release(self):
        """카메라 해제"""
        if self.picam2 and self.started:
            try:
                self.picam2.stop()
                self.started = False
            except:
                pass
    
    def isOpened(self):
        """카메라 상태 확인"""
        return self.started
    
    def set(self, prop, value):
        """OpenCV set 메서드 호환 (무시)"""
        pass
    
    def get_metadata(self):
        """AI 카메라 메타데이터 가져오기"""
        if self.picam2 and self.started:
            return self.picam2.capture_metadata()
        return {}


class PIRSensorGPIOD:
    """라즈베리파이 5 호환 PIR 센서 클래스"""
    
    def __init__(self, pin=17):
        self.pin = pin
        self.chip = None
        self.line = None
        self.enabled = False
        
        if IS_RASPBERRY_PI:
            try:
                if GPIO_LIB == "gpiod":
                    # gpiod 초기화 (라즈베리파이 5)
                    try:
                        self.chip = gpiod.Chip('gpiochip4')  # 라즈베리파이 5
                    except:
                        self.chip = gpiod.Chip('gpiochip0')  # 이전 버전 fallback
                    
                    self.line = self.chip.get_line(self.pin)
                    self.line.request(consumer="pir_sensor", type=gpiod.LINE_REQ_DIR_IN)
                    self.enabled = True
                    print(f"✓ gpiod로 PIR 센서 초기화 완료 (GPIO {self.pin})")
                    
                elif GPIO_LIB == "RPi.GPIO":
                    # RPi.GPIO 초기화
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    self.enabled = True
                    print(f"✓ RPi.GPIO로 PIR 센서 초기화 완료 (GPIO {self.pin})")
                    
            except Exception as e:
                print(f"✗ PIR 센서 초기화 실패: {e}")
                self.enabled = False
        else:
            print(f"🔧 Mock 모드: PIR 센서 시뮬레이션 (GPIO {self.pin})")
    
    def read(self):
        """PIR 센서 값 읽기"""
        if not self.enabled:
            # Mock 데이터
            import random
            return random.choice([0, 0, 0, 1])  # 25% 확률로 감지
            
        try:
            if GPIO_LIB == "gpiod":
                return self.line.get_value()
            elif GPIO_LIB == "RPi.GPIO":
                return GPIO.input(self.pin)
        except Exception as e:
            print(f"✗ PIR 센서 읽기 오류: {e}")
            return 0
    
    def cleanup(self):
        """PIR 센서 정리"""
        if self.enabled and IS_RASPBERRY_PI:
            try:
                if GPIO_LIB == "gpiod" and self.line:
                    self.line.release()
                    if self.chip:
                        self.chip.close()
                elif GPIO_LIB == "RPi.GPIO":
                    GPIO.cleanup(self.pin)
            except:
                pass


class FaceTrackerWithAIMQTT(FaceTracker):
    """AI 카메라를 사용한 얼굴 트래킹 + 생체신호 측정 + MQTT 전송 (라즈베리파이 5 호환)"""
    
    def __init__(self, pir_pin=17, start_off=False, 
                 mqtt_broker="localhost", mqtt_port=1883, 
                 mqtt_topic="healthcare/biometrics"):
        # 실행 제어
        self.running = True
        
        # PIR 센서 설정 (라즈베리파이 5 호환)
        self.pir_sensor = PIRSensorGPIOD(pir_pin) if pir_pin else None
        self.pir_enabled = self.pir_sensor is not None and self.pir_sensor.enabled
        self.camera_active = not (start_off and self.pir_enabled)
        self.pir_detection_start = None
        self.pir_no_detection_start = None
        self.pir_lock = threading.Lock()
        
        if self.pir_enabled:
            print("📡 Camera control: 10s detection ON, 30s no detection OFF")
            # PIR 모니터링 스레드 시작
            self.pir_thread = threading.Thread(target=self.monitor_pir_sensor, daemon=True)
            self.pir_thread.start()
        
        # AI 카메라로 초기화
        self.cap = AICamera(width=640, height=480, fps=30)
        if self.camera_active:
            if not self.cap.start():
                print("✗ Failed to start AI Camera")
                sys.exit(1)
        else:
            print("📷 Camera initialized but not started (waiting for motion)")
        
        # 서보모터 초기화
        if IS_RASPBERRY_PI:
            try:
                from adafruit_servokit import ServoKit
                self.kit = ServoKit(channels=16)
                print("✓ Servo motors initialized")
            except:
                self.kit = None
                print("⚠️ Servo motors not available")
        else:
            self.kit = None
        
        # 서보 설정
        self.pan_channel = 0
        self.tilt_channel = 1
        self.current_pan = 90
        self.current_tilt = 90
        self.last_face_center = None
        
        if self.kit:
            self.kit.servo[self.pan_channel].angle = 90
            self.kit.servo[self.tilt_channel].angle = 90
        
        # PID 컨트롤러
        self.pan_pid = PIDController(kp=0.08, ki=0.001, kd=0.002)
        self.tilt_pid = PIDController(kp=0.08, ki=0.001, kd=0.002)
        
        # 얼굴 감지기
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # 생체 신호 프로세서들
        self.rppg = rPPGProcessor(fps=30)
        self.stress_analyzer = StressAnalyzer()
        self.spo2_estimator = SpO2Estimator(fps=30)
        
        # 기능 활성화 여부
        self.rppg_enabled = True
        self.stress_enabled = True
        self.spo2_enabled = True
        
        # 디버그 모드
        self.debug_mode = False
        
        # 5초 평균 계산용 버퍼
        self.hr_buffer = deque(maxlen=150)
        self.stress_buffer = deque(maxlen=150)
        self.spo2_buffer = deque(maxlen=150)
        self.last_avg_time = time.time()
        
        # AI 기능 활성화
        self.ai_enhanced = True
        
        # MQTT 전송기 초기화
        self.mqtt_sender = MQTTBiometricsSender(
            broker_host=mqtt_broker,
            broker_port=mqtt_port,
            client_id=f"ai_camera_{int(time.time())}",
            topic_prefix=mqtt_topic
        )
        
        # MQTT 연결
        self.mqtt_enabled = self.mqtt_sender.connect()
        if self.mqtt_enabled:
            self.mqtt_sender.start_sending()
            print("✓ MQTT biometrics sender initialized")
        else:
            print("⚠️ MQTT connection failed - continuing without MQTT")
        
        print("\n" + "="*70)
        print("🏥 Raspberry Pi AI Camera System with MQTT (Pi 5 Compatible)")
        print("="*70)
        print("Features:")
        print("- Face Tracking with AI Camera")
        print("- Heart Rate (rPPG)")
        print("- Stress Index (HRV)")
        print("- SpO2 Estimation")
        print("- MQTT Biometrics Transmission")
        print(f"- MQTT Broker: {mqtt_broker}:{mqtt_port}")
        print(f"- MQTT Topic: {mqtt_topic}")
        print(f"- GPIO Library: {GPIO_LIB if IS_RASPBERRY_PI else 'Mock'}")
        print("\nControls:")
        print("'q' - Quit")
        print("'r' - Reset servos to center")
        print("'s' - Toggle auto search")
        print("'h' - Toggle heart rate")
        print("'t' - Toggle stress")
        print("'o' - Toggle SpO2")
        print("'d' - Toggle debug mode")
        print("'a' - Toggle AI enhancement")
        print("'m' - Toggle MQTT transmission")
        print("="*70 + "\n")
    
    def monitor_pir_sensor(self):
        """PIR 센서 모니터링 스레드"""
        print("📡 PIR sensor monitoring started...")
        
        # Mock 모드용 변수
        mock_motion_counter = 0
        mock_motion_state = 0
        
        while self.running if hasattr(self, 'running') else True:
            try:
                if self.pir_enabled:
                    if IS_RASPBERRY_PI:
                        pir_state = self.pir_sensor.read()
                    else:
                        # Mock 모드: 주기적으로 motion 시뮬레이션
                        mock_motion_counter += 1
                        if mock_motion_counter < 200:  # 20초 동안 motion 없음
                            mock_motion_state = 0
                        elif mock_motion_counter < 300:  # 10초 동안 motion
                            mock_motion_state = 1
                        else:
                            mock_motion_counter = 0  # 리셋
                        pir_state = mock_motion_state
                
                current_time = time.time()
                
                with self.pir_lock:
                    if pir_state == 1:  # 움직임 감지
                        if self.pir_detection_start is None:
                            self.pir_detection_start = current_time
                            print(f"[PIR] Motion detected at {time.strftime('%H:%M:%S')}")
                        
                        # 10초 이상 감지되면 카메라 켜기
                        if not self.camera_active and (current_time - self.pir_detection_start) >= 10:
                            print("[PIR] 10s motion detected - Turning camera ON")
                            self.turn_camera_on()
                            
                        # 움직임이 있으면 no detection 타이머 리셋
                        self.pir_no_detection_start = None
                        
                    else:  # 움직임 없음
                        if self.pir_no_detection_start is None:
                            self.pir_no_detection_start = current_time
                            if self.camera_active:
                                print(f"[PIR] No motion started at {time.strftime('%H:%M:%S')}")
                        
                        # 30초 이상 움직임 없으면 카메라 끄기
                        if self.camera_active and (current_time - self.pir_no_detection_start) >= 30:
                            print("[PIR] 30s no motion - Turning camera OFF")
                            self.turn_camera_off()
                            
                        # 움직임이 없으면 detection 타이머 리셋
                        self.pir_detection_start = None
                
                time.sleep(0.1)  # 100ms 간격으로 체크
                
            except Exception as e:
                print(f"✗ PIR monitoring error: {e}")
                time.sleep(1)
    
    def turn_camera_on(self):
        """카메라 켜기"""
        with self.pir_lock:
            if not self.camera_active:
                try:
                    # AICamera 재시작
                    if not self.cap.started:
                        self.cap = AICamera(width=640, height=480, fps=30)
                        self.cap.start()
                    
                    self.camera_active = True
                    print("✓ Camera turned ON")
                    
                    # 생체신호 프로세서 재초기화
                    self.rppg.reset()
                    self.stress_analyzer.reset()
                    self.spo2_estimator.reset()
                    
                except Exception as e:
                    print(f"✗ Failed to turn camera on: {e}")
    
    def turn_camera_off(self):
        """카메라 끄기"""
        with self.pir_lock:
            if self.camera_active:
                try:
                    self.cap.release()
                    self.camera_active = False
                    print("✓ Camera turned OFF (Power saving mode)")
                    
                    # 버퍼 초기화
                    self.hr_buffer.clear()
                    self.stress_buffer.clear()
                    self.spo2_buffer.clear()
                    
                except Exception as e:
                    print(f"✗ Failed to turn camera off: {e}")
    
    def detect_face(self, frame):
        """얼굴 감지 (AI 향상 옵션)"""
        # AI 카메라 메타데이터 확인
        if self.ai_enhanced and hasattr(self.cap, 'get_metadata'):
            metadata = self.cap.get_metadata()
            
            # AI 감지 결과가 있으면 사용
            if 'AI.FaceDetection' in metadata:
                faces = metadata['AI.FaceDetection']
                if len(faces) > 0:
                    # AI 감지 결과를 OpenCV 형식으로 변환
                    face = faces[0]
                    x, y, w, h = face['bbox']
                    return (int(x), int(y), int(w), int(h))
        
        # 기본 Haar Cascade 감지
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        
        if len(faces) > 0:
            return max(faces, key=lambda f: f[2] * f[3])
        return None
    
    def calculate_error(self, face_bbox, frame_shape):
        """중심점 오차 계산"""
        x, y, w, h = face_bbox
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # 스무딩 적용
        smoothing = 0.7
        if self.last_face_center is not None:
            face_center_x = smoothing * self.last_face_center[0] + (1-smoothing) * face_center_x
            face_center_y = smoothing * self.last_face_center[1] + (1-smoothing) * face_center_y
        
        self.last_face_center = (face_center_x, face_center_y)
        
        frame_center_x = frame_shape[1] // 2
        frame_center_y = frame_shape[0] // 2
        
        error_x = (face_center_x - frame_center_x) / (frame_shape[1] // 2)
        error_y = (face_center_y - frame_center_y) / (frame_shape[0] // 2)
        
        return error_x, error_y
    
    def update_servo_position(self, error_x, error_y):
        """서보 위치 업데이트"""
        if not self.kit:
            return
        
        # 데드존
        if abs(error_x) < 0.05:
            error_x = 0
        if abs(error_y) < 0.05:
            error_y = 0
        
        # PID 제어
        pan_adjustment = self.pan_pid.update(error_x)
        tilt_adjustment = self.tilt_pid.update(error_y)
        
        # 조정값을 각도로 변환
        pan_adjustment = np.clip(pan_adjustment * 30, -5, 5)
        tilt_adjustment = np.clip(tilt_adjustment * 30, -5, 5)
        
        # 새 각도 계산
        self.current_pan -= pan_adjustment
        self.current_tilt += tilt_adjustment
        
        # 각도 제한
        self.current_pan = np.clip(self.current_pan, 10, 170)
        self.current_tilt = np.clip(self.current_tilt, 30, 120)
        
        # 서보 이동
        try:
            self.kit.servo[self.pan_channel].angle = self.current_pan
            self.kit.servo[self.tilt_channel].angle = self.current_tilt
        except:
            pass
    
    def auto_search(self):
        """자동 탐색 모드"""
        if not hasattr(self, 'search_direction'):
            self.search_direction = 1
            self.search_speed = 2
        
        self.current_pan += self.search_direction * self.search_speed
        
        if self.current_pan >= 160 or self.current_pan <= 20:
            self.search_direction *= -1
            self.current_tilt = 90 + np.random.randint(-20, 20)
            self.current_tilt = np.clip(self.current_tilt, 30, 120)
        
        if self.kit:
            self.kit.servo[self.pan_channel].angle = self.current_pan
            self.kit.servo[self.tilt_channel].angle = self.current_tilt
    
    def draw_clean_biometrics(self, frame):
        """생체 신호 표시"""
        panel_height = 160
        panel_y = 10
        cv2.rectangle(frame, (10, panel_y), (380, panel_y + panel_height), 
                     (0, 0, 0), -1)
        cv2.rectangle(frame, (10, panel_y), (380, panel_y + panel_height), 
                     (100, 100, 100), 2)
        
        # 심박수
        if self.rppg_enabled:
            hr, _ = self.rppg.get_heart_rate()
            if hr > 0 and 40 < hr < 180:
                cv2.putText(frame, f"HR: {hr:.0f} BPM", 
                           (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "HR: ---", 
                           (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # 스트레스
        if self.stress_enabled:
            stress_data = self.stress_analyzer.get_stress_data()
            if stress_data['stress_index'] > 0:
                color = (0, 128, 255) if stress_data['stress_index'] >= 60 else \
                        (0, 255, 255) if stress_data['stress_index'] >= 40 else (0, 255, 0)
                cv2.putText(frame, f"Stress: {stress_data['stress_index']:.0f}%", 
                           (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                cv2.putText(frame, "Stress: ---", 
                           (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # SpO2
        if self.spo2_enabled:
            spo2_data = self.spo2_estimator.get_spo2_data()
            if spo2_data['spo2'] > 0 and 85 <= spo2_data['spo2'] <= 100:
                color = (0, 255, 0) if spo2_data['spo2'] >= 95 else \
                        (0, 255, 255) if spo2_data['spo2'] >= 90 else (0, 0, 255)
                cv2.putText(frame, f"SpO2: {spo2_data['spo2']:.0f}%", 
                           (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                cv2.putText(frame, "SpO2: ---", 
                           (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # MQTT 상태
        mqtt_color = (0, 255, 0) if self.mqtt_enabled and self.mqtt_sender.connected else (0, 0, 255)
        mqtt_text = "MQTT: ON" if self.mqtt_enabled and self.mqtt_sender.connected else "MQTT: OFF"
        cv2.putText(frame, mqtt_text, (30, panel_y + 125), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, mqtt_color, 2)
        
        # GPIO 라이브러리 표시
        gpio_text = f"GPIO: {GPIO_LIB}" if IS_RASPBERRY_PI else "GPIO: Mock"
        cv2.putText(frame, gpio_text, (30, panel_y + 145), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # AI 상태
        if self.ai_enhanced:
            cv2.putText(frame, "AI", (330, panel_y + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    def calculate_and_print_averages(self):
        """5초 평균 계산 및 출력"""
        current_time = time.time()
        
        if current_time - self.last_avg_time >= 5.0:
            valid_hr = [h for h in self.hr_buffer if 40 < h < 180]
            valid_stress = [s for s in self.stress_buffer if s > 0]
            valid_spo2 = [o for o in self.spo2_buffer if 85 <= o <= 100]
            
            avg_hr = np.mean(valid_hr) if valid_hr else 0
            avg_stress = np.mean(valid_stress) if valid_stress else 0
            avg_spo2 = np.mean(valid_spo2) if valid_spo2 else 0
            
            print("\n" + "="*50)
            print(f"[{time.strftime('%H:%M:%S')}] 5-second Average Biometrics")
            print("="*50)
            
            if avg_hr > 0:
                print(f"💓 Heart Rate:  {avg_hr:.1f} BPM")
            else:
                print("💓 Heart Rate:  Measuring...")
            
            if avg_stress > 0:
                print(f"😰 Stress:      {avg_stress:.0f}%")
            else:
                print("😰 Stress:      Measuring...")
            
            if avg_spo2 > 0:
                print(f"🫁 SpO2:        {avg_spo2:.1f}%")
            else:
                print("🫁 SpO2:        Measuring...")
            
            print("="*50)
            
            self.hr_buffer.clear()
            self.stress_buffer.clear()
            self.spo2_buffer.clear()
            self.last_avg_time = current_time
    
    def process_biometrics_with_mqtt(self, frame, face_bbox):
        """생체신호 처리 및 MQTT 전송"""
        if face_bbox is None:
            return
        
        # 기존 생체신호 처리
        heart_rate = None
        stress_index = None
        spo2_value = None
        
        # 1. rPPG 처리 (심박수)
        if self.rppg_enabled:
            self.rppg.process_frame(frame, face_bbox)
            hr, _ = self.rppg.get_heart_rate()
            if hr > 0 and 40 < hr < 180:
                heart_rate = hr
                self.hr_buffer.append(hr)
                
                # 스트레스 분석기에 심박수 전달
                if self.stress_enabled:
                    self.stress_analyzer.update_heart_rate(hr)
        
        # 2. SpO2 처리
        if self.spo2_enabled:
            self.spo2_estimator.process_frame(frame, face_bbox)
            spo2_data = self.spo2_estimator.get_spo2_data()
            if spo2_data['spo2'] > 0 and 85 <= spo2_data['spo2'] <= 100:
                spo2_value = spo2_data['spo2']
                self.spo2_buffer.append(spo2_value)
        
        # 3. 스트레스 처리
        if self.stress_enabled:
            stress_data = self.stress_analyzer.get_stress_data()
            if stress_data['stress_index'] > 0:
                stress_index = stress_data['stress_index']
                self.stress_buffer.append(stress_index)
        
        # 4. MQTT로 데이터 전송
        if self.mqtt_enabled:
            self.mqtt_sender.add_biometric_data(
                heart_rate=heart_rate,
                stress_index=stress_index,
                spo2=spo2_value
            )
    
    def draw_overlay(self, frame, face_bbox=None):
        """오버레이 그리기"""
        h, w = frame.shape[:2]
        
        # 중앙 십자선
        cv2.line(frame, (w//2-30, h//2), (w//2+30, h//2), (0, 255, 0), 2)
        cv2.line(frame, (w//2, h//2-30), (w//2, h//2+30), (0, 255, 0), 2)
        
        # 얼굴 박스
        if face_bbox is not None:
            x, y, w_face, h_face = face_bbox
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (255, 0, 0), 2)
            
            center_x = x + w_face // 2
            center_y = y + h_face // 2
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
        
        # 조작키 안내
        cv2.putText(frame, "Pi5: 'q'=quit, 'd'=debug, 'a'=AI, 'm'=MQTT", 
                   (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run(self):
        """메인 실행 루프"""
        print("🚀 Starting AI Camera Face Tracking + Biometrics + MQTT (Pi 5)...")
        
        self.running = True
        auto_search_enabled = False
        no_face_counter = 0
        fps_time = time.time()
        fps = 0
        
        try:
            while True:
                # 카메라가 꺼져있으면 대기
                if not self.camera_active:
                    cv2.putText(blank_frame := np.zeros((480, 640, 3), dtype=np.uint8),
                               "Camera OFF - Waiting for motion...", 
                               (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
                    cv2.imshow('AI Camera Face Tracking + MQTT (Pi 5)', blank_frame)
                    
                    if cv2.waitKey(100) & 0xFF == ord('q'):
                        break
                    continue
                
                ret, frame = self.cap.read()
                if not ret:
                    if self.camera_active:  # 카메라가 켜져있는데 읽기 실패
                        print("✗ Camera read failed")
                        time.sleep(0.1)
                    continue
                
                # FPS 계산
                fps_time_now = time.time()
                if fps_time_now - fps_time > 0:
                    fps = 1.0 / (fps_time_now - fps_time)
                fps_time = fps_time_now
                
                # 얼굴 감지
                face_bbox = self.detect_face(frame)
                
                if face_bbox is not None:
                    no_face_counter = 0
                    
                    # 1. 얼굴 트래킹
                    error_x, error_y = self.calculate_error(face_bbox, frame.shape)
                    self.update_servo_position(error_x, error_y)
                    
                    # 2. 생체신호 처리 및 MQTT 전송
                    self.process_biometrics_with_mqtt(frame, face_bbox)
                else:
                    no_face_counter += 1
                    self.last_face_center = None
                    
                    # 리셋
                    if no_face_counter > 60:
                        if self.rppg_enabled:
                            self.rppg.reset()
                        if self.stress_enabled:
                            self.stress_analyzer.reset()
                        if self.spo2_enabled:
                            self.spo2_estimator.reset()
                    
                    # 자동 탐색
                    if auto_search_enabled and no_face_counter > 30:
                        self.auto_search()
                
                # 화면 표시
                frame = self.draw_overlay(frame, face_bbox)
                
                if not self.debug_mode:
                    self.draw_clean_biometrics(frame)
                else:
                    # 디버그 모드
                    if self.rppg_enabled:
                        self.rppg.draw_roi(frame)
                        self.rppg.draw_heart_rate(frame, x=10, y=180)
                        self.rppg.draw_signal_plot(frame, x=10, y=280)
                    
                    if self.stress_enabled and self.rppg_enabled:
                        self.stress_analyzer.draw_stress_info(frame, x=10, y=380)
                    
                    if self.spo2_enabled:
                        self.spo2_estimator.draw_spo2_info(frame, x=10, y=450)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f} | {GPIO_LIB}", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 5초 평균 출력
                self.calculate_and_print_averages()
                
                # 화면 표시
                cv2.imshow('AI Camera Face Tracking + MQTT (Pi 5)', frame)
                
                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.current_pan = 90
                    self.current_tilt = 90
                    if self.kit:
                        self.kit.servo[self.pan_channel].angle = 90
                        self.kit.servo[self.tilt_channel].angle = 90
                    print("🔄 Position reset")
                elif key == ord('s'):
                    auto_search_enabled = not auto_search_enabled
                    print(f"🔍 Auto search: {'ON' if auto_search_enabled else 'OFF'}")
                elif key == ord('h'):
                    self.rppg_enabled = not self.rppg_enabled
                    if not self.rppg_enabled:
                        self.rppg.reset()
                        self.stress_analyzer.reset()
                    print(f"💓 Heart rate: {'ON' if self.rppg_enabled else 'OFF'}")
                elif key == ord('t'):
                    self.stress_enabled = not self.stress_enabled
                    if not self.stress_enabled:
                        self.stress_analyzer.reset()
                    print(f"😰 Stress: {'ON' if self.stress_enabled else 'OFF'}")
                elif key == ord('o'):
                    self.spo2_enabled = not self.spo2_enabled
                    if not self.spo2_enabled:
                        self.spo2_estimator.reset()
                    print(f"🫁 SpO2: {'ON' if self.spo2_enabled else 'OFF'}")
                elif key == ord('d'):
                    self.debug_mode = not self.debug_mode
                    print(f"🐛 Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                elif key == ord('a'):
                    self.ai_enhanced = not self.ai_enhanced
                    print(f"🤖 AI enhancement: {'ON' if self.ai_enhanced else 'OFF'}")
                elif key == ord('m'):
                    if self.mqtt_enabled:
                        if self.mqtt_sender.connected:
                            self.mqtt_sender.stop_sending()
                            self.mqtt_sender.disconnect()
                            print("📤 MQTT transmission: OFF")
                        else:
                            if self.mqtt_sender.connect():
                                self.mqtt_sender.start_sending()
                                print("📤 MQTT transmission: ON")
                    else:
                        print("⚠️ MQTT not available")
        
        except KeyboardInterrupt:
            print("\n👋 User interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """정리"""
        print("\n🧹 Cleaning up...")
        
        # PIR 모니터링 종료
        self.running = False
        
        # MQTT 정리
        if self.mqtt_enabled:
            self.mqtt_sender.stop_sending()
            self.mqtt_sender.disconnect()
        
        # 서보 중앙 위치로 복귀
        if self.kit:
            try:
                self.kit.servo[self.pan_channel].angle = 90
                self.kit.servo[self.tilt_channel].angle = 90
            except:
                pass
        
        # 카메라 해제
        if self.camera_active:
            self.cap.release()
        cv2.destroyAllWindows()
        
        # PIR 센서 정리
        if self.pir_enabled:
            self.pir_sensor.cleanup()
        
        print("✓ Cleanup complete")


# PID Controller 클래스 (기본 제공)
if 'PIDController' not in globals():
    class PIDController:
        def __init__(self, kp, ki, kd):
            self.kp = kp
            self.ki = ki
            self.kd = kd
            self.prev_error = 0
            self.integral = 0
            self.integral_limit = 1.0
        
        def update(self, error):
            self.integral += error
            self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
            derivative = error - self.prev_error
            output = self.kp * error + self.ki * self.integral + self.kd * derivative
            self.prev_error = error
            return output
        
        def reset(self):
            self.prev_error = 0
            self.integral = 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Camera Face Tracking + Biometrics + MQTT (Pi 5 Compatible)')
    parser.add_argument('--width', type=int, default=640, help='Camera width')
    parser.add_argument('--height', type=int, default=480, help='Camera height')
    parser.add_argument('--fps', type=int, default=30, help='Camera FPS')
    parser.add_argument('--pir-pin', type=int, default=17, 
                       help='PIR sensor GPIO pin (default: 17). If not set, camera always on')
    parser.add_argument('--start-off', action='store_true',
                       help='Start with camera off (only with PIR sensor)')
    parser.add_argument('--mqtt-broker', default='localhost', 
                       help='MQTT broker address (default: localhost)')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                       help='MQTT broker port (default: 1883)')
    parser.add_argument('--mqtt-topic', default='healthcare/biometrics',
                       help='MQTT topic prefix (default: healthcare/biometrics)')
    
    args = parser.parse_args()
    
    try:
        # 시스템 정보 출력
        print("🏥 AI Camera Biometrics System with MQTT")
        print("🔧 Raspberry Pi 5 Compatible Version")
        print("="*70)
        
        # GPIO 라이브러리 정보
        if IS_RASPBERRY_PI:
            print(f"🔌 GPIO Library: {GPIO_LIB}")
        else:
            print("🔌 GPIO Library: Mock Mode")
        
        # PIR 센서 정보 출력
        print(f"📡 PIR sensor: GPIO {args.pir_pin}")
        print("   Camera will turn ON after 10s of motion detection")
        print("   Camera will turn OFF after 30s of no motion")
        if args.start_off:
            print("   Starting with camera OFF")
        
        # MQTT 정보 출력
        print(f"📤 MQTT Broker: {args.mqtt_broker}:{args.mqtt_port}")
        print(f"📋 MQTT Topic: {args.mqtt_topic}")
        print(f"🔬 Biometrics: Heart Rate, Stress Index, SpO2")
        print("="*70)
        
        # 메인 시스템 실행
        tracker = FaceTrackerWithAIMQTT(
            pir_pin=args.pir_pin, 
            start_off=args.start_off,
            mqtt_broker=args.mqtt_broker,
            mqtt_port=args.mqtt_port,
            mqtt_topic=args.mqtt_topic
        )
        tracker.run()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
