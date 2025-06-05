import cv2
import numpy as np
import time
import sys

# 기존 모듈 import
try:
    from servo_face_tracker import FaceTracker, PIDController
except ImportError:
    print("경고: servo_face_tracker.py를 찾을 수 없습니다.")
    print("Windows 테스트 모드로 실행합니다.")
    # Windows 테스트용 기본 클래스 정의
    from servo_face_tracker_test import FaceTracker, PIDController

# rPPG 모듈 import
from rppg_addon_test import rPPGProcessor

#stress 모듈 import
from stress_monitor import StressMonitor

class FaceTrackerWithRPPG(FaceTracker):
    """얼굴 트래킹 + rPPG 심박수 측정 통합 클래스"""
    
    def __init__(self):
        # 부모 클래스 초기화 (얼굴 트래킹)
        super().__init__()
        
        # rPPG 프로세서 추가
        self.rppg = rPPGProcessor(fps=30)
        
        # rPPG 활성화 여부
        self.rppg_enabled = True
        
        # 디버그 모드
        self.debug_mode = False
        
        print("\n=== 얼굴 트래킹 + rPPG 심박수 측정 ===")
        print("추가 단축키:")
        print("'h' - rPPG ON/OFF")
        print("'d' - 디버그 모드 ON/OFF")
        print("=====================================\n")
    
    def run(self):
        """확장된 메인 루프"""
        print("얼굴 트래킹 + 심박수 측정 시작...")
        
        auto_search_enabled = False
        no_face_counter = 0
        fps_time = time.time()
        fps = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("카메라 읽기 실패")
                break
            
            # FPS 계산
            fps_time_now = time.time()
            if fps_time_now - fps_time > 0:
                fps = 1.0 / (fps_time_now - fps_time)
            fps_time = fps_time_now
            
            # 얼굴 감지 (부모 클래스 메서드)
            face_bbox = self.detect_face(frame)
            
            if face_bbox is not None:
                # 얼굴을 찾았을 때
                no_face_counter = 0
                
                # 1. 얼굴 트래킹 (기존 기능)
                error_x, error_y = self.calculate_error(face_bbox, frame.shape)
                self.update_servo_position(error_x, error_y)
                
                # 2. rPPG 처리 (추가 기능)
                if self.rppg_enabled:
                    self.rppg.process_frame(frame, face_bbox)
                
            else:
                # 얼굴을 찾지 못했을 때
                no_face_counter += 1
                self.last_face_center = None
                
                # rPPG 리셋
                if no_face_counter > 60:  # 2초 이상 얼굴 없으면
                    self.rppg.reset()
                
                # 자동 탐색
                if auto_search_enabled and no_face_counter > 30:
                    self.auto_search()
            
            # 화면에 정보 표시
            frame = self.draw_overlay(frame, face_bbox)
            
            # rPPG 정보 표시
            if self.rppg_enabled:
                self.rppg.draw_roi(frame)
                self.rppg.draw_heart_rate(frame, x=10, y=150)
                
                if self.debug_mode:
                    self.rppg.draw_signal_plot(frame, x=10, y=250)
            
            # FPS 표시
            cv2.putText(frame, f"FPS: {fps:.1f}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 자동 탐색 상태 표시
            if auto_search_enabled:
                cv2.putText(frame, "Auto Search: ON", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # rPPG 상태 표시
            if self.rppg_enabled:
                cv2.putText(frame, "rPPG: ON", 
                           (150, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # 서보 시뮬레이션 (Windows 테스트 모드일 때만)
            if hasattr(self, 'draw_servo_simulation'):
                sim_frame = self.draw_servo_simulation()
                cv2.imshow('Servo Position', sim_frame)
            
            # 프레임 표시
            cv2.imshow('Face Tracking + rPPG', frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # 중앙으로 리셋
                self.current_pan = 90
                self.current_tilt = 90
                self.kit.servo[self.pan_channel].angle = 90
                self.kit.servo[self.tilt_channel].angle = 90
                print("위치 리셋")
            elif key == ord('s'):
                # 자동 탐색 토글
                auto_search_enabled = not auto_search_enabled
                print(f"자동 탐색: {'ON' if auto_search_enabled else 'OFF'}")
            elif key == ord('h'):
                # rPPG 토글
                self.rppg_enabled = not self.rppg_enabled
                if not self.rppg_enabled:
                    self.rppg.reset()
                print(f"rPPG: {'ON' if self.rppg_enabled else 'OFF'}")
            elif key == ord('d'):
                # 디버그 모드 토글
                self.debug_mode = not self.debug_mode
                print(f"디버그 모드: {'ON' if self.debug_mode else 'OFF'}")
        
        # 정리
        self.cleanup()
    
    def draw_overlay(self, frame, face_bbox=None):
        """오버레이 그리기 (부모 메서드 확장)"""
        # 부모 클래스의 오버레이 먼저 그리기
        frame = super().draw_overlay(frame, face_bbox)
        
        # 추가 정보 표시
        h = frame.shape[0]
        cv2.putText(frame, "'h' - rPPG ON/OFF, 'd' - Debug mode", 
                   (10, h-80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame


# 독립 실행 가능한 간단한 데모
class SimpleRPPGDemo:
    """서보모터 없이 rPPG만 테스트하는 데모"""
    
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        self.rppg = rPPGProcessor()
        
    def run(self):
        print("rPPG 심박수 측정 데모 (서보모터 없음)")
        print("'q' - 종료")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # 얼굴 감지
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
            
            if len(faces) > 0:
                face_bbox = faces[0]
                x, y, w, h = face_bbox
                
                # 얼굴 박스 그리기
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # rPPG 처리
                self.rppg.process_frame(frame, face_bbox)
                self.rppg.draw_roi(frame)
                self.rppg.draw_heart_rate(frame)
                self.rppg.draw_signal_plot(frame)
            
            cv2.imshow('rPPG Demo', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='얼굴 트래킹 + rPPG')
    parser.add_argument('--rppg-only', action='store_true', 
                       help='rPPG만 테스트 (서보모터 없음)')
    args = parser.parse_args()
    
    try:
        if args.rppg_only:
            # rPPG만 테스트
            demo = SimpleRPPGDemo()
            demo.run()
        else:
            # 전체 시스템 실행
            tracker = FaceTrackerWithRPPG()
            tracker.run()
            
    except KeyboardInterrupt:
        print("\n사용자 중단")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()