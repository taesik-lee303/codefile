# test_integrated_face_rppg.py
# 라즈베리파이 5에서 얼굴 검출 및 rPPG 통합 테스트

import cv2
from picamera2 import Picamera2
import time
import os
import sys
import numpy as np

# rPPG 모듈 존재 여부 확인
RPPG_AVAILABLE = True
try:
    from rppg_addon import rPPGProcessor
    from stress_analyzer import StressAnalyzer
    from spo2_estimator import SpO2Estimator
    print("✓ rPPG modules found")
except ImportError as e:
    print(f"✗ rPPG modules not found: {e}")
    RPPG_AVAILABLE = False

class TestFaceDetectionAndRPPG:
    def __init__(self):
        self.picam2 = None
        self.face_cascade = None
        self.rppg = None
        self.stress_analyzer = None
        self.spo2_estimator = None
        
    def find_cascade_file(self):
        """Haar Cascade 파일 찾기"""
        print("\n=== Finding Haar Cascade file ===")
        cascade_paths = [
            '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
            '/usr/lib/python3/dist-packages/cv2/data/haarcascade_frontalface_default.xml',
            './haarcascade_frontalface_default.xml',
        ]
        
        for path in cascade_paths:
            if os.path.exists(path):
                print(f"✓ Found cascade file at: {path}")
                return path
            else:
                print(f"✗ Not found: {path}")
        
        # cv2.data 방법 시도
        try:
            if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                if os.path.exists(cascade_path):
                    print(f"✓ Found cascade file via cv2.data: {cascade_path}")
                    return cascade_path
        except:
            pass
        
        print("✗ No cascade file found!")
        return None
    
    def initialize_camera(self):
        """카메라 초기화"""
        print("\n=== Initializing Camera ===")
        try:
            self.picam2 = Picamera2()
            
            # 사용 가능한 카메라 모드 확인
            camera_config = self.picam2.sensor_modes
            print(f"Available camera modes: {len(camera_config)}")
            
            config = self.picam2.create_preview_configuration(
                main={"size": (640, 480), "format": "BGR888"},
                controls={
                    "FrameRate": 30,
                    "AeEnable": True,
                    "AwbEnable": True,
                    "AwbMode": 0,
                    "NoiseReductionMode": 1,
                    "Brightness": 0.1,
                    "Contrast": 1.2,
                    "Saturation": 1.0,
                    "ExposureTime": 0,
                    "AnalogueGain": 2.0
                }
            )
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(2)
            print("✓ Camera initialized successfully")
            return True
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            return False
    
    def initialize_face_detection(self):
        """얼굴 검출 초기화"""
        print("\n=== Initializing Face Detection ===")
        cascade_path = self.find_cascade_file()
        
        if cascade_path:
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("✗ Failed to load face cascade!")
                return False
            else:
                print("✓ Face cascade loaded successfully")
                return True
        return False
    
    def initialize_rppg(self):
        """rPPG 모듈 초기화"""
        if not RPPG_AVAILABLE:
            print("\n=== Skipping rPPG initialization (modules not found) ===")
            return False
            
        print("\n=== Initializing rPPG modules ===")
        try:
            self.rppg = rPPGProcessor(fps=30)
            self.stress_analyzer = StressAnalyzer()
            self.spo2_estimator = SpO2Estimator(fps=30)
            print("✓ rPPG modules initialized")
            return True
        except Exception as e:
            print(f"✗ rPPG initialization failed: {e}")
            return False
    
    def test_face_detection(self, num_frames=100):
        """얼굴 검출 테스트"""
        print(f"\n=== Testing Face Detection ({num_frames} frames) ===")
        
        face_count = 0
        total_faces = 0
        
        for i in range(num_frames):
            frame = self.picam2.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 얼굴 검출
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5,
                minSize=(80, 80)
            )
            
            if len(faces) > 0:
                face_count += 1
                total_faces += len(faces)
                
            # 10프레임마다 상태 출력
            if i % 10 == 0:
                print(f"Frame {i}: Detected {len(faces)} faces")
            
            # 얼굴 영역 표시
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, "Face", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            
            # 프레임 정보 표시
            cv2.putText(frame, f"Frame: {i}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Faces: {len(faces)}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('Face Detection Test', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        print(f"\n=== Face Detection Results ===")
        print(f"Frames with faces: {face_count}/{num_frames} ({face_count/num_frames*100:.1f}%)")
        print(f"Average faces per frame: {total_faces/num_frames:.2f}")
        
        return face_count > 0
    
    def test_rppg(self, duration=30):
        """rPPG 테스트"""
        if not self.rppg:
            print("\n=== Skipping rPPG test (not initialized) ===")
            return
            
        print(f"\n=== Testing rPPG ({duration} seconds) ===")
        print("Please stay still in front of the camera...")
        
        start_time = time.time()
        frame_count = 0
        hr_readings = []
        spo2_readings = []
        stress_readings = []
        
        while time.time() - start_time < duration:
            frame = self.picam2.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 얼굴 검출
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
            
            if len(faces) > 0:
                # 가장 큰 얼굴 선택
                face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = face
                
                # 얼굴 영역 표시
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # rPPG 처리
                try:
                    self.rppg.process_frame(frame, face)
                    hr, confidence = self.rppg.get_heart_rate()
                    
                    # SpO2 처리
                    self.spo2_estimator.process_frame(frame, face)
                    spo2_data = self.spo2_estimator.get_spo2_data()
                    spo2 = spo2_data['spo2']
                    
                    # 스트레스 처리
                    if 40 < hr < 180:
                        self.stress_analyzer.update_heart_rate(hr)
                    stress_data = self.stress_analyzer.get_stress_data()
                    stress = stress_data['stress_index']
                    
                    # 데이터 저장
                    if frame_count % 30 == 0:  # 1초마다
                        if 40 < hr < 180:
                            hr_readings.append(hr)
                        if 85 <= spo2 <= 100:
                            spo2_readings.append(spo2)
                        if stress > 0:
                            stress_readings.append(stress)
                        
                        print(f"Time: {time.time()-start_time:.1f}s | "
                              f"HR: {hr:.1f} (conf: {confidence:.2f}) | "
                              f"SpO2: {spo2:.1f}% | "
                              f"Stress: {stress:.1f}%")
                    
                    # 화면에 표시
                    cv2.putText(frame, f"HR: {hr:.0f} BPM", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"SpO2: {spo2:.0f}%", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(frame, f"Stress: {stress:.0f}%", (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                except Exception as e:
                    print(f"rPPG processing error: {e}")
            else:
                cv2.putText(frame, "No face detected", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # 남은 시간 표시
            elapsed = time.time() - start_time
            cv2.putText(frame, f"Time: {elapsed:.1f}/{duration}s", (10, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('rPPG Test', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            frame_count += 1
        
        print(f"\n=== rPPG Test Results ===")
        print(f"Total frames: {frame_count}")
        if hr_readings:
            print(f"HR readings: {len(hr_readings)}, Avg: {np.mean(hr_readings):.1f} BPM")
        else:
            print("No valid HR readings")
        if spo2_readings:
            print(f"SpO2 readings: {len(spo2_readings)}, Avg: {np.mean(spo2_readings):.1f}%")
        else:
            print("No valid SpO2 readings")
        if stress_readings:
            print(f"Stress readings: {len(stress_readings)}, Avg: {np.mean(stress_readings):.1f}%")
        else:
            print("No valid stress readings")
    
    def cleanup(self):
        """정리"""
        if self.picam2:
            self.picam2.stop()
        cv2.destroyAllWindows()
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=== Starting Integrated Face Detection and rPPG Tests ===")
        print("OpenCV version:", cv2.__version__)
        
        # 카메라 초기화
        if not self.initialize_camera():
            print("Cannot proceed without camera")
            return
        
        # 얼굴 검출 초기화
        if not self.initialize_face_detection():
            print("Cannot proceed without face detection")
            self.cleanup()
            return
        
        # 얼굴 검출 테스트
        face_detection_ok = self.test_face_detection(100)
        
        if face_detection_ok:
            # rPPG 초기화 및 테스트
            if self.initialize_rppg():
                self.test_rppg(30)
            else:
                print("\nrPPG test skipped due to initialization failure")
        else:
            print("\nrPPG test skipped - face detection not working")
        
        self.cleanup()
        print("\n=== All tests completed ===")

if __name__ == "__main__":
    tester = TestFaceDetectionAndRPPG()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.cleanup()
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        tester.cleanup()
