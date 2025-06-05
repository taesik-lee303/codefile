import numpy as np
from collections import deque
import time
from scipy import signal
import threading

class StressAnalyzer:
    """심박 변이도(HRV) 기반 스트레스 지수 측정"""
    
    def __init__(self, buffer_size=300):
        self.buffer_size = buffer_size
        
        # RR 간격 버퍼 (심박 간 시간 간격)
        self.rr_intervals = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)
        
        # HRV 메트릭스
        self.rmssd = 0  # Root Mean Square of Successive Differences
        self.sdnn = 0   # Standard Deviation of NN intervals
        self.pnn50 = 0  # Percentage of successive RR intervals that differ by more than 50 ms
        
        # 스트레스 지수
        self.stress_index = 0
        self.stress_level = "측정 중..."
        
        # 이전 심박수와 시간
        self.last_hr = 0
        self.last_hr_time = 0
        
        # 스레드 안전
        self.lock = threading.Lock()
        
    def update_heart_rate(self, heart_rate):
        """심박수 업데이트 및 RR 간격 계산"""
        if heart_rate <= 0 or heart_rate > 200:
            return
            
        current_time = time.time()
        
        with self.lock:
            if self.last_hr > 0 and self.last_hr_time > 0:
                # RR 간격 계산 (ms 단위)
                rr_interval = (60.0 / heart_rate) * 1000  # BPM to ms
                
                self.rr_intervals.append(rr_interval)
                self.timestamps.append(current_time)
                
                # 충분한 데이터가 모이면 HRV 계산
                if len(self.rr_intervals) >= 30:  # 최소 30개 이상
                    self._calculate_hrv_metrics()
                    self._calculate_stress_index()
            
            self.last_hr = heart_rate
            self.last_hr_time = current_time
    
    def _calculate_hrv_metrics(self):
        """HRV 메트릭스 계산"""
        try:
            rr_array = np.array(self.rr_intervals)
            
            # RMSSD: 연속된 RR 간격 차이의 제곱 평균 제곱근
            if len(rr_array) > 1:
                successive_diffs = np.diff(rr_array)
                self.rmssd = np.sqrt(np.mean(successive_diffs ** 2))
            
            # SDNN: RR 간격의 표준 편차
            self.sdnn = np.std(rr_array)
            
            # pNN50: 50ms 이상 차이나는 연속 RR 간격의 비율
            if len(rr_array) > 1:
                successive_diffs = np.abs(np.diff(rr_array))
                nn50 = np.sum(successive_diffs > 50)
                self.pnn50 = (nn50 / len(successive_diffs)) * 100
            
        except Exception as e:
            print(f"HRV 계산 오류: {e}")
    
    def _calculate_stress_index(self):
        """스트레스 지수 계산 (0-100)"""
        try:
            # 스트레스 지수 계산 공식
            # 낮은 HRV = 높은 스트레스
            # 높은 HRV = 낮은 스트레스
            
            # RMSSD 기반 (정상 범위: 20-50ms)
            rmssd_score = 0
            if self.rmssd > 0:
                if self.rmssd >= 40:
                    rmssd_score = 0  # 매우 낮은 스트레스
                elif self.rmssd >= 30:
                    rmssd_score = 25
                elif self.rmssd >= 20:
                    rmssd_score = 50
                elif self.rmssd >= 15:
                    rmssd_score = 75
                else:
                    rmssd_score = 100  # 매우 높은 스트레스
            
            # SDNN 기반 (정상 범위: 50-100ms)
            sdnn_score = 0
            if self.sdnn > 0:
                if self.sdnn >= 60:
                    sdnn_score = 0
                elif self.sdnn >= 40:
                    sdnn_score = 25
                elif self.sdnn >= 30:
                    sdnn_score = 50
                elif self.sdnn >= 20:
                    sdnn_score = 75
                else:
                    sdnn_score = 100
            
            # pNN50 기반 (정상 범위: >15%)
            pnn50_score = 0
            if self.pnn50 >= 20:
                pnn50_score = 0
            elif self.pnn50 >= 15:
                pnn50_score = 25
            elif self.pnn50 >= 10:
                pnn50_score = 50
            elif self.pnn50 >= 5:
                pnn50_score = 75
            else:
                pnn50_score = 100
            
            # 종합 스트레스 지수 (가중 평균)
            self.stress_index = int(
                rmssd_score * 0.4 + 
                sdnn_score * 0.4 + 
                pnn50_score * 0.2
            )
            
            # 스트레스 레벨 분류
            if self.stress_index >= 80:
                self.stress_level = "매우 높음"
            elif self.stress_index >= 60:
                self.stress_level = "높음"
            elif self.stress_index >= 40:
                self.stress_level = "보통"
            elif self.stress_index >= 20:
                self.stress_level = "낮음"
            else:
                self.stress_level = "매우 낮음"
            
        except Exception as e:
            print(f"스트레스 지수 계산 오류: {e}")
    
    def get_stress_data(self):
        """현재 스트레스 데이터 반환"""
        with self.lock:
            return {
                'stress_index': self.stress_index,
                'stress_level': self.stress_level,
                'rmssd': self.rmssd,
                'sdnn': self.sdnn,
                'pnn50': self.pnn50
            }
    
    def draw_stress_info(self, frame, x=10, y=350):
        """스트레스 정보 표시"""
        data = self.get_stress_data()
        
        # 스트레스 지수 색상 결정
        if data['stress_index'] >= 80:
            color = (0, 0, 255)  # 빨강
        elif data['stress_index'] >= 60:
            color = (0, 128, 255)  # 주황
        elif data['stress_index'] >= 40:
            color = (0, 255, 255)  # 노랑
        else:
            color = (0, 255, 0)  # 초록
        
        # 스트레스 지수 표시
        cv2.putText(frame, f"Stress: {data['stress_index']}% ({data['stress_level']})", 
                   (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # HRV 메트릭스 표시 (디버그용)
        if data['rmssd'] > 0:
            cv2.putText(frame, f"RMSSD: {data['rmssd']:.1f}ms", 
                       (x, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(frame, f"SDNN: {data['sdnn']:.1f}ms", 
                       (x+120, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # 스트레스 바 그래프
        bar_width = 150
        bar_height = 15
        bar_x = x
        bar_y = y + 35
        
        # 배경 바
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + bar_width, bar_y + bar_height), 
                     (100, 100, 100), -1)
        
        # 스트레스 레벨 바
        stress_width = int((data['stress_index'] / 100.0) * bar_width)
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + stress_width, bar_y + bar_height), 
                     color, -1)
        
        # 바 테두리
        cv2.rectangle(frame, (bar_x, bar_y), 
                     (bar_x + bar_width, bar_y + bar_height), 
                     (200, 200, 200), 1)
    
    def reset(self):
        """버퍼 초기화"""
        with self.lock:
            self.rr_intervals.clear()
            self.timestamps.clear()
            self.stress_index = 0
            self.stress_level = "측정 중..."
            self.rmssd = 0
            self.sdnn = 0
            self.pnn50 = 0


# OpenCV import (draw 함수용)
try:
    import cv2
except ImportError:
    print("경고: OpenCV를 찾을 수 없습니다. 시각화 기능이 제한됩니다.")