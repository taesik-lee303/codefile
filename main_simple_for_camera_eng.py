import cv2
import numpy as np
import time
import sys
from collections import deque

# 기존 모듈 import
try:
    from servo_face_tracker import FaceTracker, PIDController
except ImportError:
    print("경고: servo_face_tracker.py를 찾을 수 없습니다.")
    print("Windows 테스트 모드로 실행합니다.")
    # Windows 테스트용 기본 클래스 정의
    from servo_face_tracker_test import FaceTracker, PIDController

# rPPG 모듈 import
from rppg_addon import rPPGProcessor
from stress_analyzer import StressAnalyzer
from spo2_estimator import SpO2Estimator


class FaceTrackerWithRPPG(FaceTracker):
    """face tracking + rPPG HP measuring + stress + SpO2 Unit Class"""
    
    def __init__(self):
        # 부모 클래스 초기화 (얼굴 트래킹)
        super().__init__()
        
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
        self.spo2_debug = True  # SpO2 디버깅용
        
        # 5초 평균 계산용 버퍼
        self.hr_buffer = deque(maxlen=150)  # 30fps * 5초
        self.stress_buffer = deque(maxlen=150)
        self.spo2_buffer = deque(maxlen=150)
        self.last_avg_time = time.time()
        
        print("\n=== face tracking + bio signal measure system ===")
        print("measure list:")
        print("- HP (rPPG)")
        print("- Stress rate (HRV)")
        print("- SpO2")
        print("\nControlKey:")
        print("'q' - END")
        print("'r' - Servo MID Reset")
        print("'s' - Auto Tracking ON/OFF")
        print("'h' - Measuring HP ON/OFF")
        print("'t' - Measuring Stress ON/OFF")
        print("'o' - Measuring SpO2 ON/OFF")
        print("'d' - Debug Mode ON/OFF")
        print("=========================================\n")
    
    def draw_clean_biometrics(self, frame):
        """깔끔한 생체 신호 표시 (주요 값만)"""
        # 배경 패널
        panel_height = 120
        panel_y = 10
        cv2.rectangle(frame, (10, panel_y), (350, panel_y + panel_height), 
                     (0, 0, 0), -1)
        cv2.rectangle(frame, (10, panel_y), (350, panel_y + panel_height), 
                     (100, 100, 100), 2)
        
        # 심박수
        if self.rppg_enabled:
            hr, _ = self.rppg.get_heart_rate()
            if hr > 0 and 40 < hr < 180:  # 정상 범위 체크
                cv2.putText(frame, f"HR: {hr:.0f} BPM", 
                           (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "HR: ---", 
                           (30, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # 스트레스
        if self.stress_enabled:
            stress_data = self.stress_analyzer.get_stress_data()
            if stress_data['stress_index'] > 0:
                # 색상 결정
                if stress_data['stress_index'] >= 60:
                    color = (0, 128, 255)  # 주황
                elif stress_data['stress_index'] >= 40:
                    color = (0, 255, 255)  # 노랑
                else:
                    color = (0, 255, 0)    # 초록
                cv2.putText(frame, f"Stress: {stress_data['stress_index']:.0f}%", 
                           (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                cv2.putText(frame, "Stress: ---", 
                           (30, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # SpO2
        if self.spo2_enabled:
            spo2_data = self.spo2_estimator.get_spo2_data()
            
            # SpO2 디버깅 정보
            if self.spo2_debug:
                buffer_size = len(self.spo2_estimator.red_values)
                cv2.putText(frame, f"SpO2 Buffer: {buffer_size}/150", 
                           (200, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                if spo2_data['r_value'] > 0:
                    cv2.putText(frame, f"R: {spo2_data['r_value']:.2f}", 
                               (200, panel_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            if spo2_data['spo2'] > 0 and 85 <= spo2_data['spo2'] <= 100:
                # 색상 결정
                if spo2_data['spo2'] >= 95:
                    color = (0, 255, 0)    # 초록
                elif spo2_data['spo2'] >= 90:
                    color = (0, 255, 255)  # 노랑
                else:
                    color = (0, 0, 255)    # 빨강
                cv2.putText(frame, f"SpO2: {spo2_data['spo2']:.0f}%", 
                           (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            else:
                cv2.putText(frame, "SpO2: ---", 
                           (30, panel_y + 95), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    def calculate_and_print_averages(self):
        """5초간의 평균값 계산 및 출력"""
        current_time = time.time()
        
        # 5초마다 평균 출력
        if current_time - self.last_avg_time >= 5.0:
            # 유효한 값들만 필터링
            valid_hr = [h for h in self.hr_buffer if 40 < h < 180]
            valid_stress = [s for s in self.stress_buffer if s > 0]
            valid_spo2 = [o for o in self.spo2_buffer if 85 <= o <= 100]
            
            # 평균 계산
            avg_hr = np.mean(valid_hr) if valid_hr else 0
            avg_stress = np.mean(valid_stress) if valid_stress else 0
            avg_spo2 = np.mean(valid_spo2) if valid_spo2 else 0
            
            # 터미널에 출력
            print("\n" + "="*50)
            print(f"[{time.strftime('%H:%M:%S')}] 5seconds mean bio signal")
            print("="*50)
            if avg_hr > 0:
                print(f"HP:     {avg_hr:.1f} BPM")
            else:
                print("HP:     Measuring...")
            
            if avg_stress > 0:
                print(f"Stress:   {avg_stress:.0f}%")
            else:
                print("Stress:   Measuring...")
            
            if avg_spo2 > 0:
                print(f"SpO2: {avg_spo2:.1f}%")
            else:
                print("SpO2: Measuring...")
            
            # 디버깅 정보
            if self.spo2_debug:
                print(f"[Debug] HR EffValue: {len(valid_hr)}, Stress EffValue: {len(valid_stress)}, SpO2 EffValue: {len(valid_spo2)}")
            
            print("="*50)
            
            # 버퍼 초기화
            self.hr_buffer.clear()
            self.stress_buffer.clear()
            self.spo2_buffer.clear()
            self.last_avg_time = current_time
    
    def run(self):
        """확장된 메인 루프"""
        print("Face Tracking + HP Measuring Start...")
        
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
                    
                    # 심박수가 계산되면 스트레스 분석기에 전달
                    hr, _ = self.rppg.get_heart_rate()
                    if hr > 0 and 40 < hr < 180:
                        self.hr_buffer.append(hr)
                        if self.stress_enabled:
                            self.stress_analyzer.update_heart_rate(hr)
                
                # 3. SpO2 처리
                if self.spo2_enabled:
                    self.spo2_estimator.process_frame(frame, face_bbox)
                    spo2_data = self.spo2_estimator.get_spo2_data()
                    if spo2_data['spo2'] > 0 and 85 <= spo2_data['spo2'] <= 100:
                        self.spo2_buffer.append(spo2_data['spo2'])
                
                # 4. 스트레스 값 버퍼에 추가
                if self.stress_enabled:
                    stress_data = self.stress_analyzer.get_stress_data()
                    if stress_data['stress_index'] > 0:
                        self.stress_buffer.append(stress_data['stress_index'])
                
            else:
                # 얼굴을 찾지 못했을 때
                no_face_counter += 1
                self.last_face_center = None
                
                # rPPG/스트레스/SpO2 리셋
                if no_face_counter > 60:  # 2초 이상 얼굴 없으면
                    if self.rppg_enabled:
                        self.rppg.reset()
                    if self.stress_enabled:
                        self.stress_analyzer.reset()
                    if self.spo2_enabled:
                        self.spo2_estimator.reset()
                
                # 자동 탐색
                if auto_search_enabled and no_face_counter > 30:
                    self.auto_search()
            
            # 화면에 정보 표시
            frame = self.draw_overlay(frame, face_bbox)
            
            # 깔끔한 생체 신호 표시 (디버그 모드가 아닐 때)
            if not self.debug_mode:
                self.draw_clean_biometrics(frame)
            else:
                # 디버그 모드일 때는 상세 정보 표시
                if self.rppg_enabled:
                    self.rppg.draw_roi(frame)
                    self.rppg.draw_heart_rate(frame, x=10, y=150)
                    self.rppg.draw_signal_plot(frame, x=10, y=250)
                
                if self.stress_enabled and self.rppg_enabled:
                    self.stress_analyzer.draw_stress_info(frame, x=10, y=350)
                
                if self.spo2_enabled:
                    self.spo2_estimator.draw_spo2_info(frame, x=10, y=450)
            
            # 5초 평균 계산 및 출력
            self.calculate_and_print_averages()
            
            # FPS 표시 (디버그 모드일 때만)
            if self.debug_mode:
                cv2.putText(frame, f"FPS: {fps:.1f}", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 자동 탐색 상태 표시 (디버그 모드일 때만)
            if self.debug_mode:
                if auto_search_enabled:
                    cv2.putText(frame, "Auto Search: ON", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 기능 상태 표시
                status_y = 120
                if self.rppg_enabled:
                    cv2.putText(frame, "HR: ON", 
                               (150, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                if self.stress_enabled:
                    cv2.putText(frame, "Stress: ON", 
                               (230, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                if self.spo2_enabled:
                    cv2.putText(frame, "SpO2: ON", 
                               (340, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
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
                    self.stress_analyzer.reset()  # 스트레스도 리셋
                print(f"심박수 측정: {'ON' if self.rppg_enabled else 'OFF'}")
            elif key == ord('t'):
                # 스트레스 토글
                self.stress_enabled = not self.stress_enabled
                if not self.stress_enabled:
                    self.stress_analyzer.reset()
                print(f"스트레스 측정: {'ON' if self.stress_enabled else 'OFF'}")
            elif key == ord('o'):
                # SpO2 토글
                self.spo2_enabled = not self.spo2_enabled
                if not self.spo2_enabled:
                    self.spo2_estimator.reset()
                print(f"SpO2 측정: {'ON' if self.spo2_enabled else 'OFF'}")
            elif key == ord('d'):
                # 디버그 모드 토글
                self.debug_mode = not self.debug_mode
                print(f"디버그 모드: {'ON' if self.debug_mode else 'OFF'}")
        
        # 정리
        self.cleanup()
    
    def draw_overlay(self, frame, face_bbox=None):
        """오버레이 그리기"""
        h, w = frame.shape[:2]
        
        # 중앙 십자선
        cv2.line(frame, (w//2-30, h//2), (w//2+30, h//2), (0, 255, 0), 2)
        cv2.line(frame, (w//2, h//2-30), (w//2, h//2+30), (0, 255, 0), 2)
        
        # 얼굴 박스 및 중심점
        if face_bbox is not None:
            x, y, w_face, h_face = face_bbox
            # 얼굴 박스
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (255, 0, 0), 2)
            
            # 얼굴 중심점
            center_x = x + w_face // 2
            center_y = y + h_face // 2
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
        
        # 조작키 안내 (화면 하단)
        cv2.putText(frame, "Press 'q' to quit, 'd' for debug mode", 
                   (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame


# 독립 실행 가능한 간단한 데모 클래스는 그대로 유지...
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