import cv2
import numpy as np
import time
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

class FaceTrackerRPi5:
    def __init__(self):
        # PiGPIO를 사용한 정밀한 서보 제어
        factory = PiGPIOFactory()
        
        # 서보모터 초기화 (GPIO 핀 번호 설정)
        self.pan_servo = Servo(18, pin_factory=factory)    # 좌우 회전
        self.tilt_servo = Servo(19, pin_factory=factory)   # 상하 회전
        
        # 서보 중앙 위치로 초기화 (서보 값 범위: -1 ~ 1)
        self.pan_servo.value = 0   # 중앙
        self.tilt_servo.value = 0  # 중앙
        
        # 현재 서보 값 저장 (-1 ~ 1 범위)
        self.current_pan = 0
        self.current_tilt = 0
        
        # PID 제어 변수
        self.pan_pid = PIDController(kp=0.5, ki=0.01, kd=0.1)
        self.tilt_pid = PIDController(kp=0.5, ki=0.01, kd=0.1)
        
        # 카메라 초기화
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 얼굴 감지기 초기화
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # 부드러운 움직임을 위한 변수
        self.smoothing_factor = 0.7
        self.last_face_center = None
        
        print("라즈베리파이 5 직접 서보 제어 초기화 완료")
        
    def servo_value_to_angle(self, value):
        """서보 값(-1~1)을 각도(0~180)로 변환 (표시용)"""
        return int((value + 1) * 90)
        
    def detect_face(self, frame):
        """얼굴 감지 및 가장 큰 얼굴 반환"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )
        
        if len(faces) > 0:
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            return largest_face
        
        return None
    
    def calculate_error(self, face_bbox, frame_shape):
        """화면 중앙과 얼굴 중심 간의 오차 계산"""
        x, y, w, h = face_bbox
        frame_h, frame_w = frame_shape[:2]
        
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        # 부드러운 움직임을 위한 필터링
        if self.last_face_center is not None:
            face_center_x = (self.smoothing_factor * self.last_face_center[0] + 
                           (1 - self.smoothing_factor) * face_center_x)
            face_center_y = (self.smoothing_factor * self.last_face_center[1] + 
                           (1 - self.smoothing_factor) * face_center_y)
        
        self.last_face_center = (face_center_x, face_center_y)
        
        frame_center_x = frame_w // 2
        frame_center_y = frame_h // 2
        
        # 오차 계산 (정규화: -1 ~ 1)
        error_x = (face_center_x - frame_center_x) / (frame_w // 2)
        error_y = (face_center_y - frame_center_y) / (frame_h // 2)
        
        return error_x, error_y
    
    def update_servo_position(self, error_x, error_y):
        """PID 제어를 사용한 서보 위치 업데이트"""
        # 데드존 설정
        if abs(error_x) < 0.05:
            error_x = 0
        if abs(error_y) < 0.05:
            error_y = 0
        
        # PID 제어 적용
        pan_adjustment = self.pan_pid.update(error_x)
        tilt_adjustment = self.tilt_pid.update(error_y)
        
        # 조정값 제한 (최대 이동 속도 제한)
        pan_adjustment = np.clip(pan_adjustment, -0.1, 0.1)
        tilt_adjustment = np.clip(tilt_adjustment, -0.1, 0.1)
        
        # 새로운 서보 값 계산
        self.current_pan -= pan_adjustment
        self.current_tilt += tilt_adjustment
        
        # 서보 값 제한 (-1 ~ 1)
        self.current_pan = np.clip(self.current_pan, -1, 1)
        self.current_tilt = np.clip(self.current_tilt, -1, 1)
        
        # 서보 모터 이동
        try:
            self.pan_servo.value = self.current_pan
            self.tilt_servo.value = self.current_tilt
        except Exception as e:
            print(f"서보 제어 오류: {e}")
    
    def draw_overlay(self, frame, face_bbox=None):
        """화면에 정보 오버레이"""
        h, w = frame.shape[:2]
        
        # 중앙 십자선
        cv2.line(frame, (w//2-30, h//2), (w//2+30, h//2), (0, 255, 0), 2)
        cv2.line(frame, (w//2, h//2-30), (w//2, h//2+30), (0, 255, 0), 2)
        
        # 얼굴 박스 및 중심점
        if face_bbox is not None:
            x, y, w_face, h_face = face_bbox
            cv2.rectangle(frame, (x, y), (x+w_face, y+h_face), (255, 0, 0), 2)
            
            center_x = x + w_face // 2
            center_y = y + h_face // 2
            cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
            
            cv2.line(frame, (w//2, h//2), (int(center_x), int(center_y)), (255, 255, 0), 1)
        
        # 서보 각도 정보 (표시용으로 각도 변환)
        pan_angle = self.servo_value_to_angle(self.current_pan)
        tilt_angle = self.servo_value_to_angle(self.current_tilt)
        
        cv2.putText(frame, f"Pan: {pan_angle}° ({self.current_pan:.2f})", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Tilt: {tilt_angle}° ({self.current_tilt:.2f})", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Press 'q' to quit", 
                   (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame
    
    def auto_search(self):
        """얼굴을 찾지 못했을 때 자동 탐색"""
        if not hasattr(self, 'search_direction'):
            self.search_direction = 1
            self.search_speed = 0.02
        
        self.current_pan += self.search_direction * self.search_speed
        
        # 경계에 도달하면 방향 전환
        if self.current_pan >= 0.8 or self.current_pan <= -0.8:
            self.search_direction *= -1
            # 틸트도 약간 조정
            self.current_tilt = np.random.uniform(-0.3, 0.3)
            self.current_tilt = np.clip(self.current_tilt, -1, 1)
        
        # 서보 이동
        self.pan_servo.value = self.current_pan
        self.tilt_servo.value = self.current_tilt
    
    def run(self):
        """메인 트래킹 루프"""
        print("라즈베리파이 5 얼굴 트래킹 시작...")
        print("'q' - 종료")
        print("'r' - 중앙 위치로 리셋")
        print("'s' - 자동 탐색 모드 토글")
        
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
                no_face_counter = 0
                error_x, error_y = self.calculate_error(face_bbox, frame.shape)
                self.update_servo_position(error_x, error_y)
            else:
                no_face_counter += 1
                self.last_face_center = None
                
                if auto_search_enabled and no_face_counter > 30:
                    self.auto_search()
            
            # 화면에 정보 표시
            frame = self.draw_overlay(frame, face_bbox)
            
            # FPS 표시
            cv2.putText(frame, f"FPS: {fps:.1f}", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if auto_search_enabled:
                cv2.putText(frame, "Auto Search: ON", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow('RPi5 Face Tracking', frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # 중앙으로 리셋
                self.current_pan = 0
                self.current_tilt = 0
                self.pan_servo.value = 0
                self.tilt_servo.value = 0
                print("위치 리셋")
            elif key == ord('s'):
                auto_search_enabled = not auto_search_enabled
                print(f"자동 탐색: {'ON' if auto_search_enabled else 'OFF'}")
        
        self.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        print("\n종료 중...")
        
        # 서보를 중앙 위치로
        self.pan_servo.value = 0
        self.tilt_servo.value = 0
        
        # 서보 정리
        self.pan_servo.close()
        self.tilt_servo.close()
        
        # 카메라와 창 닫기
        self.cap.release()
        cv2.destroyAllWindows()
        print("종료 완료")


class PIDController:
    """PID 제어기 클래스"""
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.prev_error = 0
        self.integral = 0
        self.integral_limit = 1.0
        
    def update(self, error):
        """PID 계산"""
        self.integral += error
        self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
        
        derivative = error - self.prev_error
        
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        self.prev_error = error
        return output
    
    def reset(self):
        """PID 상태 리셋"""
        self.prev_error = 0
        self.integral = 0


# 사용 예시
if __name__ == "__main__":
    try:
        tracker = FaceTrackerRPi5()
        tracker.run()
    except KeyboardInterrupt:
        print("\n사용자 중단")
    except Exception as e:
        print(f"오류 발생: {e}")
