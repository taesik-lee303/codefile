import numpy as np
from collections import deque
import time
from scipy import signal
import threading

class SpO2Estimator:
    """카메라 기반 산소 포화도(SpO2) 추정"""
    
    def __init__(self, fps=30, buffer_size=150):
        self.fps = fps
        self.buffer_size = buffer_size
        
        # RGB 채널별 신호 버퍼
        self.red_values = deque(maxlen=buffer_size)
        self.blue_values = deque(maxlen=buffer_size)
        self.green_values = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)
        
        # SpO2 결과
        self.spo2_value = 0
        self.spo2_confidence = 0
        self.r_value = 0  # R value (AC_red/DC_red) / (AC_infrared/DC_infrared)
        
        # 캘리브레이션 상수 (조정된 값)
        self.calibration_a = 100.0  # 기본값
        self.calibration_b = 15.0   # 기본값
        
        # ROI 시각화용
        self.roi_bbox = None
        
        # 스레드 안전
        self.lock = threading.Lock()
        
        # 디버그용
        self.debug_info = {
            'dc_red': 0,
            'dc_blue': 0,
            'ac_red': 0,
            'ac_blue': 0
        }
        
    def process_frame(self, frame, face_bbox):
        """프레임에서 SpO2 추정을 위한 신호 추출"""
        if face_bbox is None:
            return
            
        # ROI 추출 (이마 영역)
        roi = self._extract_spo2_roi(frame, face_bbox)
        if roi is None or roi.size == 0:
            return
        
        # roi가 올바른 형태인지 확인
        if len(roi.shape) != 3 or roi.shape[2] != 3:
            return
            
        # 평균 RGB 값 계산
        mean_rgb = np.mean(roi, axis=(0, 1))
        
        # mean_rgb가 올바른 형태인지 확인
        if mean_rgb.shape != (3,):
            return
        
        with self.lock:
            # BGR to RGB 순서 변경
            self.blue_values.append(float(mean_rgb[0]))
            self.green_values.append(float(mean_rgb[1]))
            self.red_values.append(float(mean_rgb[2]))
            self.timestamps.append(time.time())
            
            # 충분한 데이터가 모이면 SpO2 계산
            if len(self.red_values) >= self.buffer_size:
                self._calculate_spo2()
    
    def _extract_spo2_roi(self, frame, face_bbox):
        """SpO2 측정을 위한 ROI 추출 (볼 영역 포함)"""
        x, y, w, h = face_bbox
        
        # 이마 영역을 주로 사용 (더 안정적)
        forehead_y = y + int(h * 0.05)
        forehead_h = int(h * 0.25)
        forehead_x = x + int(w * 0.2)
        forehead_w = int(w * 0.6)
        
        # 경계 체크
        frame_h, frame_w = frame.shape[:2]
        
        # 경계 조정
        forehead_x = max(0, forehead_x)
        forehead_y = max(0, forehead_y)
        forehead_w = min(forehead_w, frame_w - forehead_x)
        forehead_h = min(forehead_h, frame_h - forehead_y)
        
        if forehead_w > 0 and forehead_h > 0:
            roi = frame[forehead_y:forehead_y+forehead_h, 
                       forehead_x:forehead_x+forehead_w]
            
            # ROI 위치 저장 (시각화용)
            self.roi_bbox = (forehead_x, forehead_y, forehead_w, forehead_h)
            
            return roi
        
        return None
    
    def _calculate_spo2(self):
        """SpO2 계산"""
        try:
            # 신호 배열 생성
            red_array = np.array(self.red_values)
            blue_array = np.array(self.blue_values)
            time_array = np.array(self.timestamps)
            
            # 실제 샘플링 레이트
            time_diff = time_array[-1] - time_array[0]
            if time_diff == 0:
                return
            actual_fps = len(time_array) / time_diff
            
            # DC 성분 (평균값)
            dc_red = np.mean(red_array)
            dc_blue = np.mean(blue_array)
            
            self.debug_info['dc_red'] = dc_red
            self.debug_info['dc_blue'] = dc_blue
            
            # 신호가 너무 약하면 리턴
            if dc_red < 10 or dc_blue < 10:
                return
            
            # AC 성분 추출을 위한 간단한 고주파 통과 필터
            # 평균을 빼서 DC 제거
            ac_red = red_array - dc_red
            ac_blue = blue_array - dc_blue
            
            # 간단한 이동평균 필터로 스무딩
            window = 5
            if len(ac_red) > window:
                ac_red = np.convolve(ac_red, np.ones(window)/window, mode='same')
                ac_blue = np.convolve(ac_blue, np.ones(window)/window, mode='same')
            
            # RMS 값 계산 (AC 성분의 크기)
            ac_red_rms = np.sqrt(np.mean(ac_red ** 2))
            ac_blue_rms = np.sqrt(np.mean(ac_blue ** 2))
            
            self.debug_info['ac_red'] = ac_red_rms
            self.debug_info['ac_blue'] = ac_blue_rms
            
            # R 값 계산
            if dc_red > 0 and dc_blue > 0 and ac_red_rms > 0 and ac_blue_rms > 0:
                self.r_value = (ac_red_rms / dc_red) / (ac_blue_rms / dc_blue)
                
                # SpO2 추정 (간단한 선형 모델)
                # 일반적으로 R value는 0.5 ~ 2.0 범위
                if 0.4 < self.r_value < 2.5:
                    estimated_spo2 = self.calibration_a - self.calibration_b * self.r_value
                    
                    # 범위 제한
                    estimated_spo2 = np.clip(estimated_spo2, 85, 100)
                    
                    # 신뢰도 계산 (단순화)
                    if ac_red_rms > 0.01 and ac_blue_rms > 0.01:
                        self.spo2_confidence = 50
                    else:
                        self.spo2_confidence = 20
                    
                    # 값 업데이트
                    if self.spo2_value == 0:
                        self.spo2_value = estimated_spo2
                    else:
                        # 이동평균
                        alpha = 0.2
                        self.spo2_value = alpha * estimated_spo2 + (1 - alpha) * self.spo2_value
            
        except Exception as e:
            # 오류가 발생해도 조용히 처리
            pass
    
    def get_spo2_data(self):
        """현재 SpO2 데이터 반환"""
        with self.lock:
            return {
                'spo2': self.spo2_value,
                'confidence': self.spo2_confidence,
                'r_value': self.r_value
            }
    
    def draw_spo2_info(self, frame, x=10, y=450):
        """SpO2 정보 표시"""
        data = self.get_spo2_data()
        
        # ROI 영역 표시
        if self.roi_bbox is not None:
            rx, ry, rw, rh = self.roi_bbox
            cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (255, 255, 0), 2)
            cv2.putText(frame, "SpO2 ROI", (rx, ry-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        if data['spo2'] > 0:
            # SpO2 값에 따른 색상
            if data['spo2'] >= 95:
                color = (0, 255, 0)  # 정상 (초록)
            elif data['spo2'] >= 90:
                color = (0, 255, 255)  # 주의 (노랑)
            else:
                color = (0, 0, 255)  # 위험 (빨강)
            
            # SpO2 표시
            cv2.putText(frame, f"SpO2: {data['spo2']:.0f}%", 
                       (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 신뢰도 표시
            conf_color = (0, 255, 0) if data['confidence'] > 50 else (0, 165, 255)
            cv2.putText(frame, f"Confidence: {data['confidence']}%", 
                       (x, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, conf_color, 1)
            
            # 산소 아이콘
            if data['spo2'] >= 95:
                cv2.putText(frame, "O2", (x+150, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        else:
            # 측정 중
            buffer_percent = (len(self.red_values) / self.buffer_size) * 100
            cv2.putText(frame, f"SpO2: Measuring... ({buffer_percent:.0f}%)", 
                       (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, "Please keep still", 
                       (x, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    
    def calibrate(self, known_spo2):
        """알려진 SpO2 값으로 캘리브레이션"""
        if self.r_value > 0 and known_spo2 > 0:
            # 새로운 캘리브레이션 상수 계산
            # SpO2 = a - b * R
            # known_spo2 = a - b * current_R
            # 단순화를 위해 b는 고정하고 a만 조정
            self.calibration_a = known_spo2 + self.calibration_b * self.r_value
            print(f"캘리브레이션 완료: a={self.calibration_a:.1f}")
    
    def reset(self):
        """버퍼 초기화"""
        with self.lock:
            self.red_values.clear()
            self.blue_values.clear()
            self.green_values.clear()
            self.timestamps.clear()
            self.spo2_value = 0
            self.spo2_confidence = 0
            self.r_value = 0


# OpenCV import
try:
    import cv2
except ImportError:
    print("경고: OpenCV를 찾을 수 없습니다. 시각화 기능이 제한됩니다.")


# 주의사항 텍스트
DISCLAIMER = """
주의: 이 SpO2 측정은 의료용이 아닌 실험/교육 목적입니다.
정확한 측정을 위해서는 의료용 펄스 옥시미터를 사용하세요.
카메라 기반 SpO2는 다음 요인에 영향을 받습니다:
- 조명 조건
- 피부색
- 움직임
- 카메라 품질
"""