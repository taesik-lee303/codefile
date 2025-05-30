import cv2
import numpy as np
import time

# Windows 테스트용 - 실제 서보 대신 시뮬레이션
class MockServoKit:
    """서보모터 시뮬레이션 클래스"""
    def __init__(self, channels=16):
        self.servo = {}
        for i in range(channels):
            self.servo[i] = MockServo()

class MockServo:
    """개별 서보 시뮬레이션"""
    def __init__(self):
        self._angle = 90
    
    @property
    def angle(self):
        return self._angle
    
    @angle.setter
    def angle(self, value):
        self._angle = np.clip(value, 0, 180)

class FaceTracker:
    def __init__(self):
        # Windows에서는 Mock 서보 사용
        print("Windows 테스트 모드 - 서보모터 시뮬레이션")
        self.kit = MockServoKit(channels=16)
        
        # 서보모터 채널 설정
        self.pan_channel = 0  # 수평 회전 (좌우)
        self.tilt_channel = 1  # 수직 회전 (상하)
        
        # 서보 각도 범위 설정 및 중앙 위치로 초기화
        self.kit.servo[self.pan_channel].angle = 90
        self.kit.servo[self.tilt_channel].angle = 90
        
        # 현재 각도 저장
        self.current_pan = 90
        self.current_tilt = 90
        
        # PID 제어 변수
        self.pan_pid = PIDController(kp=0.08, ki=0.001, kd=0.002)
        self.tilt_pid = PIDController(kp=0.08, ki=0.001, kd=0.002)
        
        # 카메라 초기화
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("경고: 기본 카메라를 찾을 수 없습니다. 다른 카메라 인덱스 시도...")
            for i in range(1, 4):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    print(f"카메라 {i} 사용")
                    break
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 얼굴 감지기 초기화
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # 부드러운 움직임을 위한 변수
        self.smoothing_factor = 0.7
        self.last_face_center = None
        
        # 시뮬레이션용 시각화 창
        self.create_simulation_window()
        
    def create_simulation_window(self):
        """서보 시뮬레이션 창 생성"""
        self.sim_width = 400
        self.sim_height = 300
        
    def draw_servo_simulation(self):
        """서보 위치 시뮬레이션 그리기"""
        sim_frame = np.ones((self.sim_height, self.sim_width, 3), dtype=np.uint8) * 255
        
        # 중앙점
        center_x = self.sim_width // 2
        center_y = self.sim_height // 2
        
        # 서보 각도를 화면 좌표로 변환
        # Pan: 0-180도 → 화면 좌우
        # Tilt: 0-180도 → 화면 상하
        servo_x = int((self.current_pan / 180) * self.sim_width)
        servo_y = int((self.current_tilt / 180) * self.sim_height)
        
        # 배경 격자 그리기
        for i in range(0, self.sim_width, 50):
            cv2.line(sim_frame, (i, 0), (i, self.sim_height), (200, 200, 200), 1)
        for i in range(0, self.sim_height, 50):
            cv2.line(sim_frame, (0, i), (self.sim_width, i), (200, 200, 200), 1)
        
        # 중앙 십자선
        cv2.line(sim_frame, (center_x, 0), (center_x, self.sim_height), (100, 100, 100), 2)
        cv2.line(sim_frame, (0, center_y), (self.sim_width, center_y), (100, 100, 100), 2)
        
        # 서보 위치 표시
        cv2.circle(sim_frame, (servo_x, servo_y), 20, (0, 0, 255), -1)
        cv2.circle(sim_frame, (servo_x, servo_y), 25, (0, 0, 150), 2)
        
        # 중앙에서 서보 위치까지 선
        cv2.line(sim_frame, (center_x, center_y), (servo_x, servo_y), (0, 255, 0), 2)
        
        # 각도 정보 표시
        cv2.putText(sim_frame, f"Pan: {self.current_pan:.1f}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(sim_frame, f"Tilt: {self.current_tilt:.1f}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        cv2.putText(sim_frame, "Servo Simulation", 
                   (10, self.sim_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
        
        return sim_frame
        
    def detect_face(self, frame):
        """얼굴 감지 및 가장 큰 얼굴 반환"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 얼굴 감지 (파라미터 조정으로 성능 최적화)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)  # 최소 얼굴 크기
        )
        
        if len(faces) > 0:
            # 가장 큰 얼굴 선택 (가장 가까운 얼굴)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            return largest_face
        
        return None
    
    def calculate_error(self, face_bbox, frame_shape):
        """화면 중앙과 얼굴 중심 간의 오차 계산"""
        x, y, w, h = face_bbox
        frame_h, frame_w = frame_shape[:2]
        
        # 얼굴 중심점
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # 부드러운 움직임을 위한 필터링
        if self.last_face_center is not None:
            # 이전 위치와 현재 위치를 보간
            face_center_x = (self.smoothing_factor * self.last_face_center[0] + 
                           (1 - self.smoothing_factor) * face_center_x)
            face_center_y = (self.smoothing_factor * self.last_face_center[1] + 
                           (1 - self.smoothing_factor) * face_center_y)
        
        self.last_face_center = (face_center_x, face_center_y)
        
        # 화면 중심점
        frame_center_x = frame_w // 2
        frame_center_y = frame_h // 2
        
        # 오차 계산 (정규화: -1 ~ 1)
        error_x = (face_center_x - frame_center_x) / (frame_w // 2)
        error_y = (face_center_y - frame_center_y) / (frame_h // 2)
        
        return error_x, error_y
    
    def update_servo_position(self, error_x, error_y):
        """PID 제어를 사용한 서보 위치 업데이트"""
        # 데드존 설정 (작은 오차는 무시)
        if abs(error_x) < 0.05:
            error_x = 0
        if abs(error_y) < 0.05:
            error_y = 0
        
        # PID 제어 적용
        pan_adjustment = self.pan_pid.update(error_x)
        tilt_adjustment = self.tilt_pid.update(error_y)
        
        # 조정값을 각도로 변환 (최대 이동 속도 제한)
        pan_adjustment = np.clip(pan_adjustment * 30, -5, 5)
        tilt_adjustment = np.clip(tilt_adjustment * 30, -5, 5)
        
        # 새로운 각도 계산
        self.current_pan -= pan_adjustment
        self.current_tilt += tilt_adjustment
        
        # 각도 제한
        self.current_pan = np.clip(self.current_pan, 10, 170)
        self.current_tilt = np.clip(self.current_tilt, 30, 120)
        
        # 서보 모터 이동 (시뮬레이션)
        self.kit.servo[self.pan_channel].angle = self.current_pan
        self.kit.servo[self.tilt_channel].angle = self.current_tilt
    
    def draw_overlay(self, frame, face_bbox=None):
        """화면에 정보 오버레이"""
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
            
            # 중앙으로부터의 선
            cv2.line(frame, (w//2, h//2), (int(center_x), int(center_y)), (255, 255, 0), 1)
        
        # 서보 각도 정보
        cv2.putText(frame, f"Pan: {self.current_pan:.1f}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Tilt: {self.current_tilt:.1f}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 안내 메시지
        cv2.putText(frame, "Windows Test Mode", 
                   (10, h-50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, "Press 'q' to quit, 'r' to reset", 
                   (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def auto_search(self):
        """얼굴을 찾지 못했을 때 자동 탐색"""
        # 스캔 패턴 (부드러운 좌우 움직임)
        if not hasattr(self, 'search_direction'):
            self.search_direction = 1
            self.search_speed = 2
        
        self.current_pan += self.search_direction * self.search_speed
        
        # 경계에 도달하면 방향 전환
        if self.current_pan >= 160 or self.current_pan <= 20:
            self.search_direction *= -1
            # 틸트도 약간 조정
            self.current_tilt = 90 + np.random.randint(-20, 20)
            self.current_tilt = np.clip(self.current_tilt, 30, 120)
        
        # 서보 이동 (시뮬레이션)
        self.kit.servo[self.pan_channel].angle = self.current_pan
        self.kit.servo[self.tilt_channel].angle = self.current_tilt
    
    def run(self):
        """메인 트래킹 루프"""
        print("\n=== Windows 테스트 모드 ===")
        print("얼굴 트래킹 시작...")
        print("'q' - 종료")
        print("'r' - 중앙 위치로 리셋")
        print("'s' - 자동 탐색 모드 토글")
        print("========================\n")
        
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
            
            # 얼굴 감지
            face_bbox = self.detect_face(frame)
            
            if face_bbox is not None:
                # 얼굴을 찾았을 때
                no_face_counter = 0
                
                # 오차 계산
                error_x, error_y = self.calculate_error(face_bbox, frame.shape)
                
                # 서보 위치 업데이트
                self.update_servo_position(error_x, error_y)
                
            else:
                # 얼굴을 찾지 못했을 때
                no_face_counter += 1
                self.last_face_center = None  # 스무딩 리셋
                
                # 1초 이상 얼굴을 찾지 못하면 자동 탐색
                if auto_search_enabled and no_face_counter > 30:
                    self.auto_search()
            
            # 화면에 정보 표시
            frame = self.draw_overlay(frame, face_bbox)
            
            # FPS 표시
            cv2.putText(frame, f"FPS: {fps:.1f}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 자동 탐색 상태 표시
            if auto_search_enabled:
                cv2.putText(frame, "Auto Search: ON", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 서보 시뮬레이션 표시
            sim_frame = self.draw_servo_simulation()
            
            # 프레임 표시
            cv2.imshow('Face Tracking', frame)
            cv2.imshow('Servo Position', sim_frame)
            
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
        
        # 정리
        self.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        print("\n종료 중...")
        
        # 서보를 중앙 위치로 (시뮬레이션)
        self.kit.servo[self.pan_channel].angle = 90
        self.kit.servo[self.tilt_channel].angle = 90
        
        # 카메라와 창 닫기
        self.cap.release()
        cv2.destroyAllWindows()
        print("종료 완료")


class PIDController:
    """PID 제어기 클래스"""
    def __init__(self, kp, ki, kd):
        self.kp = kp  # 비례 게인
        self.ki = ki  # 적분 게인
        self.kd = kd  # 미분 게인
        
        self.prev_error = 0
        self.integral = 0
        
        # 적분 윈드업 방지
        self.integral_limit = 1.0
        
    def update(self, error):
        """PID 계산"""
        # 적분 항
        self.integral += error
        self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
        
        # 미분 항
        derivative = error - self.prev_error
        
        # PID 출력
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        # 이전 오차 저장
        self.prev_error = error
        
        return output
    
    def reset(self):
        """PID 상태 리셋"""
        self.prev_error = 0
        self.integral = 0


# 사용 예시
if __name__ == "__main__":
    try:
        print("Windows 테스트 버전 시작...")
        tracker = FaceTracker()
        tracker.run()
    except KeyboardInterrupt:
        print("\n사용자 중단")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()