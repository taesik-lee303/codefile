# main_ai_camera.py (서보모터 제거 버전 - cv2.data 오류 수정)

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import sys
import os
from collections import deque

# 라즈베리파이 여부 확인
try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    print("Not running on Raspberry Pi - Mock mode enabled")

# rPPG 관련 모듈
from rppg_addon import rPPGProcessor
from stress_analyzer import StressAnalyzer
from spo2_estimator import SpO2Estimator

class AICamera:
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.picam2 = None
        self.started = False

    def start(self):
        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={"FrameRate": self.fps, "AeEnable": True, "AwbEnable": True, "NoiseReductionMode": 1}
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.started = True
            time.sleep(2)
            print(f"AI Camera started: {self.width}x{self.height} @ {self.fps}fps")
            return True
        except Exception as e:
            print(f"Camera initialization failed: {e}")
            return False

    def read(self):
        if not self.started:
            return False, None
        try:
            frame = self.picam2.capture_array()
            return True, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except:
            return False, None

    def release(self):
        if self.picam2 and self.started:
            self.picam2.stop()
            self.started = False

    def isOpened(self):
        return self.started

    def set(self, prop, value):
        pass

    def get_metadata(self):
        if self.picam2 and self.started:
            return self.picam2.capture_metadata()
        return {}

class FaceTrackerWithAI:
    def __init__(self):
        self.cap = AICamera()
        if not self.cap.start():
            print("Failed to start AI Camera")
            sys.exit(1)

        # cv2.data 오류 해결을 위한 수정된 코드
        self.face_cascade = self._load_face_cascade()

        self.rppg = rPPGProcessor(fps=30)
        self.stress_analyzer = StressAnalyzer()
        self.spo2_estimator = SpO2Estimator(fps=30)

        self.rppg_enabled = True
        self.stress_enabled = True
        self.spo2_enabled = True
        self.debug_mode = False

        self.hr_buffer = deque(maxlen=150)
        self.stress_buffer = deque(maxlen=150)
        self.spo2_buffer = deque(maxlen=150)
        self.last_avg_time = time.time()
        self.ai_enhanced = True

    def _load_face_cascade(self):
        """Haar Cascade 파일을 안전하게 로드하는 함수"""
        cascade_paths = [
            # OpenCV 4.x 경로들
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            # 패키지 설치 경로들
            '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
            '/opt/homebrew/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            # 현재 디렉토리
            './haarcascade_frontalface_default.xml',
        ]
        
        # cv2.data가 존재하는 경우 우선 시도
        try:
            if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                cascade = cv2.CascadeClassifier(cascade_path)
                if not cascade.empty():
                    print(f"Face cascade loaded from: {cascade_path}")
                    return cascade
        except:
            pass
        
        # 각 경로를 순차적으로 시도
        for path in cascade_paths:
            if os.path.exists(path):
                cascade = cv2.CascadeClassifier(path)
                if not cascade.empty():
                    print(f"Face cascade loaded from: {path}")
                    return cascade
        
        # 모든 경로 실패 시 기본 방법으로 시도
        print("Warning: Using default cascade classifier (may be empty)")
        return cv2.CascadeClassifier()

    def detect_face(self, frame):
        # AI 얼굴 검출이 가능한 경우 먼저 시도
        if self.ai_enhanced and hasattr(self.cap, 'get_metadata'):
            try:
                metadata = self.cap.get_metadata()
                if 'AI.FaceDetection' in metadata:
                    faces = metadata['AI.FaceDetection']
                    if len(faces) > 0:
                        x, y, w, h = faces[0]['bbox']
                        return (int(x), int(y), int(w), int(h))
            except:
                pass
        
        # Haar Cascade를 사용한 얼굴 검출
        if not self.face_cascade.empty():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(80, 80)
            )
            if len(faces) > 0:
                # 가장 큰 얼굴을 선택하고 tuple로 변환
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                return tuple(largest_face)  # numpy array를 tuple로 변환
        
        return None

    def draw_overlay(self, frame, face_bbox=None):
        h, w = frame.shape[:2]
        # 중앙 십자선 그리기
        cv2.line(frame, (w//2-30, h//2), (w//2+30, h//2), (0, 255, 0), 2)
        cv2.line(frame, (w//2, h//2-30), (w//2, h//2+30), (0, 255, 0), 2)
        
        # 얼굴 영역 표시
        if face_bbox is not None:
            x, y, wf, hf = face_bbox
            cv2.rectangle(frame, (x, y), (x+wf, y+hf), (255, 0, 0), 2)
            cx = x + wf // 2
            cy = y + hf // 2
            cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)
        
        return frame

    def draw_biometrics(self, frame):
        panel_y = 10
        
        # 심박수 표시
        if self.rppg_enabled:
            hr, _ = self.rppg.get_heart_rate()
            text = f"HR: {hr:.0f} BPM" if 40 < hr < 180 else "HR: ---"
            cv2.putText(frame, text, (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        
        # 스트레스 지수 표시
        if self.stress_enabled:
            stress = self.stress_analyzer.get_stress_data()['stress_index']
            text = f"Stress: {stress:.0f}%" if stress > 0 else "Stress: ---"
            cv2.putText(frame, text, (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
        
        # 산소포화도 표시
        if self.spo2_enabled:
            spo2 = self.spo2_estimator.get_spo2_data()['spo2']
            text = f"SpO2: {spo2:.0f}%" if 85 <= spo2 <= 100 else "SpO2: ---"
            cv2.putText(frame, text, (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    def run(self):
        print("Starting AI Camera (no servo mode)...")
        print("Press 'q' to quit")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Camera read failed")
                break
            
            # 얼굴 검출
            face_bbox = self.detect_face(frame)
            
            # face_bbox가 None이 아니고 유효한 값인지 확인
            if face_bbox is not None and len(face_bbox) == 4:
                # rPPG 처리
                if self.rppg_enabled:
                    self.rppg.process_frame(frame, face_bbox)
                    hr, _ = self.rppg.get_heart_rate()
                    if 40 < hr < 180:
                        self.hr_buffer.append(hr)
                        self.stress_analyzer.update_heart_rate(hr)
                
                # SpO2 처리
                if self.spo2_enabled:
                    self.spo2_estimator.process_frame(frame, face_bbox)
                    spo2 = self.spo2_estimator.get_spo2_data()['spo2']
                    if 85 <= spo2 <= 100:
                        self.spo2_buffer.append(spo2)
                
                # 스트레스 분석
                if self.stress_enabled:
                    stress = self.stress_analyzer.get_stress_data()['stress_index']
                    if stress > 0:
                        self.stress_buffer.append(stress)
            
            # 화면에 표시
            frame = self.draw_overlay(frame, face_bbox if face_bbox is not None else None)
            self.draw_biometrics(frame)
            
            cv2.imshow("AI Camera", frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        self.cleanup()

    def cleanup(self):
        print("Cleaning up...")
        self.cap.release()
        cv2.destroyAllWindows()
        if IS_RASPBERRY_PI:
            try:
                GPIO.cleanup()
            except:
                pass

if __name__ == "__main__":
    try:
        tracker = FaceTrackerWithAI()
        tracker.run()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
