# main_ai_camera.py (서보모터 제거 버전)

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import sys
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

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

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

    def detect_face(self, frame):
        if self.ai_enhanced and hasattr(self.cap, 'get_metadata'):
            metadata = self.cap.get_metadata()
            if 'AI.FaceDetection' in metadata:
                faces = metadata['AI.FaceDetection']
                if len(faces) > 0:
                    x, y, w, h = faces[0]['bbox']
                    return (int(x), int(y), int(w), int(h))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) > 0:
            return max(faces, key=lambda f: f[2] * f[3])
        return None

    def draw_overlay(self, frame, face_bbox=None):
        h, w = frame.shape[:2]
        cv2.line(frame, (w//2-30, h//2), (w//2+30, h//2), (0, 255, 0), 2)
        cv2.line(frame, (w//2, h//2-30), (w//2, h//2+30), (0, 255, 0), 2)
        if face_bbox is not None:
            x, y, wf, hf = face_bbox
            cv2.rectangle(frame, (x, y), (x+wf, y+hf), (255, 0, 0), 2)
            cx = x + wf // 2
            cy = y + hf // 2
            cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)
        return frame

    def draw_biometrics(self, frame):
        panel_y = 10
        if self.rppg_enabled:
            hr, _ = self.rppg.get_heart_rate()
            text = f"HR: {hr:.0f} BPM" if 40 < hr < 180 else "HR: ---"
            cv2.putText(frame, text, (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        if self.stress_enabled:
            stress = self.stress_analyzer.get_stress_data()['stress_index']
            text = f"Stress: {stress:.0f}%" if stress > 0 else "Stress: ---"
            cv2.putText(frame, text, (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
        if self.spo2_enabled:
            spo2 = self.spo2_estimator.get_spo2_data()['spo2']
            text = f"SpO2: {spo2:.0f}%" if 85 <= spo2 <= 100 else "SpO2: ---"
            cv2.putText(frame, text, (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    def run(self):
        print("Starting AI Camera (no servo mode)...")
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Camera read failed")
                break
            face_bbox = self.detect_face(frame)
            if face_bbox:
                if self.rppg_enabled:
                    self.rppg.process_frame(frame, face_bbox)
                    hr, _ = self.rppg.get_heart_rate()
                    if 40 < hr < 180:
                        self.hr_buffer.append(hr)
                        self.stress_analyzer.update_heart_rate(hr)
                if self.spo2_enabled:
                    self.spo2_estimator.process_frame(frame, face_bbox)
                    spo2 = self.spo2_estimator.get_spo2_data()['spo2']
                    if 85 <= spo2 <= 100:
                        self.spo2_buffer.append(spo2)
                if self.stress_enabled:
                    stress = self.stress_analyzer.get_stress_data()['stress_index']
                    if stress > 0:
                        self.stress_buffer.append(stress)
            frame = self.draw_overlay(frame, face_bbox)
            self.draw_biometrics(frame)
            cv2.imshow("AI Camera", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        self.cleanup()

    def cleanup(self):
        self.cap.release()
        cv2.destroyAllWindows()
        if IS_RASPBERRY_PI:
            try:
                GPIO.cleanup()
            except:
                pass

if __name__ == "__main__":
    tracker = FaceTrackerWithAI()
    tracker.run()
