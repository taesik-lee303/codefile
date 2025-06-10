#!/usr/bin/env python3
"""
Raspberry Pi AI Camera를 사용한 얼굴 감지 + 생체신호 측정 시스템
서보모터 제어 기능 제거 버전
"""

from picamera2 import Picamera2
import cv2
import numpy as np
import time
import sys
from collections import deque

# rPPG 모듈 import
from rppg_addon import rPPGProcessor
from stress_analyzer import StressAnalyzer
from spo2_estimator import SpO2Estimator


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
            print(f"AI Camera started: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except Exception as e:
            print(f"Camera initialization failed: {e}")
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
            self.picam2.stop()
            self.started = False
    
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


class FaceDetectorWithBiometrics:
    """AI 카메라를 사용한 얼굴 감지 + 생체신호 측정"""
    
    def __init__(self):
        # AI 카메라로 초기화
        self.cap = AICamera(width=640, height=480, fps=30)
        if not self.cap.start():
            print("Failed to start AI Camera")
            sys.exit(1)
        
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
        
        print("\n=== Raspberry Pi AI Camera System ===")
        print("Features:")
        print("- Face Detection with AI Camera")
        print("- Heart Rate (rPPG)")
        print("- Stress Index (HRV)")
        print("- SpO2 Estimation")
        print("\nControls:")
        print("'q' - Quit")
        print("'h' - Toggle heart rate")
        print("'t' - Toggle stress")
        print("'o' - Toggle SpO2")
        print("'d' - Toggle debug mode")
        print("'a' - Toggle AI enhancement")
        print("=====================================\n")
    
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
    
    def draw_clean_biometrics(self, frame):
        """생체 신호 표시"""
        panel_height = 120
        panel_y = 10
        cv2.rectangle(frame, (10, panel_y), (350, panel_y + panel_height), 
                     (0, 0, 0), -1)
        cv2.rectangle(frame, (10, panel_y), (350, panel_y + panel_height), 
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
        
        # AI 상태
        if self.ai_enhanced:
            cv2.putText(frame, "AI", (300, panel_y + 20), 
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
                print(f"Heart Rate:  {avg_hr:.1f} BPM")
            else:
                print("Heart Rate:  Measuring...")
            
            if avg_stress > 0:
                print(f"Stress:      {avg_stress:.0f}%")
            else:
                print("Stress:      Measuring...")
            
            if avg_spo2 > 0:
                print(f"SpO2:        {avg_spo2:.1f}%")
            else:
                print("SpO2:        Measuring...")
            
            print("="*50)
            
            self.hr_buffer.clear()
            self.stress_buffer.clear()
            self.spo2_buffer.clear()
            self.last_avg_time = current_time
    
    def draw_overlay(self, frame, face_bbox=None):
        """오버레이 그리기"""
        h, w = frame.shape[:2]
        
        # 얼굴 박스
        if face_bbox is not None:
            x, y, w_face, h_face = face_bbox
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (255, 0, 0), 2)
            
            center_x = x + w_face // 2
            center_y = y + h_face // 2
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
            
            # 얼굴 감지 상태
            cv2.putText(frame, "Face Detected", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 조작키 안내
        cv2.putText(frame, "Press 'q' to quit, 'd' for debug, 'a' for AI toggle", 
                   (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def run(self):
        """메인 실행 루프"""
        print("Starting AI Camera Face Detection + Biometrics...")
        
        no_face_counter = 0
        fps_time = time.time()
        fps = 0
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Camera read failed")
                    break
                
                # FPS 계산
                fps_time_now = time.time()
                if fps_time_now - fps_time > 0:
                    fps = 1.0 / (fps_time_now - fps_time)
                fps_time = fps_time_now
                
                # 얼굴 감지
                face_bbox = self.detect_face(frame)
                
                if face_bbox is not None:
                    no_face_counter = 0
                    
                    # 1. rPPG 처리
                    if self.rppg_enabled:
                        self.rppg.process_frame(frame, face_bbox)
                        hr, _ = self.rppg.get_heart_rate()
                        if hr > 0 and 40 < hr < 180:
                            self.hr_buffer.append(hr)
                            if self.stress_enabled:
                                self.stress_analyzer.update_heart_rate(hr)
                    
                    # 2. SpO2 처리
                    if self.spo2_enabled:
                        self.spo2_estimator.process_frame(frame, face_bbox)
                        spo2_data = self.spo2_estimator.get_spo2_data()
                        if spo2_data['spo2'] > 0 and 85 <= spo2_data['spo2'] <= 100:
                            self.spo2_buffer.append(spo2_data['spo2'])
                    
                    # 3. 스트레스 처리
                    if self.stress_enabled:
                        stress_data = self.stress_analyzer.get_stress_data()
                        if stress_data['stress_index'] > 0:
                            self.stress_buffer.append(stress_data['stress_index'])
                else:
                    no_face_counter += 1
                    
                    # 리셋
                    if no_face_counter > 60:
                        if self.rppg_enabled:
                            self.rppg.reset()
                        if self.stress_enabled:
                            self.stress_analyzer.reset()
                        if self.spo2_enabled:
                            self.spo2_estimator.reset()
                
                # 화면 표시
                frame = self.draw_overlay(frame, face_bbox)
                
                if not self.debug_mode:
                    self.draw_clean_biometrics(frame)
                else:
                    # 디버그 모드
                    if self.rppg_enabled:
                        self.rppg.draw_roi(frame)
                        self.rppg.draw_heart_rate(frame, x=10, y=150)
                        self.rppg.draw_signal_plot(frame, x=10, y=250)
                    
                    if self.stress_enabled and self.rppg_enabled:
                        self.stress_analyzer.draw_stress_info(frame, x=10, y=350)
                    
                    if self.spo2_enabled:
                        self.spo2_estimator.draw_spo2_info(frame, x=10, y=450)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f}", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 5초 평균 출력
                self.calculate_and_print_averages()
                
                # 화면 표시
                cv2.imshow('AI Camera Face Detection', frame)
                
                # 키 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('h'):
                    self.rppg_enabled = not self.rppg_enabled
                    if not self.rppg_enabled:
                        self.rppg.reset()
                        self.stress_analyzer.reset()
                    print(f"Heart rate: {'ON' if self.rppg_enabled else 'OFF'}")
                elif key == ord('t'):
                    self.stress_enabled = not self.stress_enabled
                    if not self.stress_enabled:
                        self.stress_analyzer.reset()
                    print(f"Stress: {'ON' if self.stress_enabled else 'OFF'}")
                elif key == ord('o'):
                    self.spo2_enabled = not self.spo2_enabled
                    if not self.spo2_enabled:
                        self.spo2_estimator.reset()
                    print(f"SpO2: {'ON' if self.spo2_enabled else 'OFF'}")
                elif key == ord('d'):
                    self.debug_mode = not self.debug_mode
                    print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                elif key == ord('a'):
                    self.ai_enhanced = not self.ai_enhanced
                    print(f"AI enhancement: {'ON' if self.ai_enhanced else 'OFF'}")
        
        except KeyboardInterrupt:
            print("\nUser interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """정리"""
        print("\nCleaning up...")
        
        self.cap.release()
        cv2.destroyAllWindows()
        
        print("Cleanup complete")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Camera Face Detection + Biometrics')
    parser.add_argument('--width', type=int, default=640, help='Camera width')
    parser.add_argument('--height', type=int, default=480, help='Camera height')
    parser.add_argument('--fps', type=int, default=30, help='Camera FPS')
    
    args = parser.parse_args()
    
    try:
        # 메인 시스템 실행
        detector = FaceDetectorWithBiometrics()
        detector.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()