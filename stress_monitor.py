import numpy as np
import cv2
from collections import deque
import time

class StressMonitor:
    def __init__(self, window_size=30):
        """
        스트레스 지수 모니터링 클래스
        HRV(Heart Rate Variability)를 기반으로 스트레스 지수 계산
        
        Args:
            window_size: HRV 계산을 위한 윈도우 크기 (초)
        """
        self.window_size = window_size
        self.rr_intervals = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        self.last_peak_time = None
        self.stress_level = 0.0
        
    def add_heartbeat(self, timestamp):
        """
        심박 타임스탬프 추가
        
        Args:
            timestamp: 심박이 감지된 시간
        """
        if self.last_peak_time is not None:
            rr_interval = timestamp - self.last_peak_time
            if 0.4 < rr_interval < 2.0:  # 정상 범위의 RR 간격만 사용 (30-150 BPM)
                self.rr_intervals.append(rr_interval)
                self.timestamps.append(timestamp)
        
        self.last_peak_time = timestamp
    
    def calculate_hrv_metrics(self):
        """
        HRV 메트릭 계산
        
        Returns:
            dict: HRV 메트릭들 (RMSSD, SDNN, pNN50)
        """
        if len(self.rr_intervals) < 5:
            return None
        
        rr_array = np.array(self.rr_intervals)
        
        # RMSSD (Root Mean Square of Successive Differences)
        diff_rr = np.diff(rr_array)
        rmssd = np.sqrt(np.mean(diff_rr ** 2)) * 1000  # ms 단위
        
        # SDNN (Standard Deviation of NN intervals)
        sdnn = np.std(rr_array) * 1000  # ms 단위
        
        # pNN50 (percentage of NN50)
        nn50 = np.sum(np.abs(diff_rr) > 0.05)
        pnn50 = (nn50 / len(diff_rr)) * 100 if len(diff_rr) > 0 else 0
        
        return {
            'rmssd': rmssd,
            'sdnn': sdnn,
            'pnn50': pnn50,
            'mean_hr': 60.0 / np.mean(rr_array) if np.mean(rr_array) > 0 else 0
        }
    
    def calculate_stress_index(self):
        """
        스트레스 지수 계산 (0-100 스케일)
        
        Returns:
            float: 스트레스 지수 (0: 매우 낮음, 100: 매우 높음)
        """
        hrv_metrics = self.calculate_hrv_metrics()
        
        if hrv_metrics is None:
            return self.stress_level
        
        # HRV 기반 스트레스 지수 계산
        # 낮은 RMSSD와 높은 심박수는 높은 스트레스를 의미
        rmssd = hrv_metrics['rmssd']
        mean_hr = hrv_metrics['mean_hr']
        
        # RMSSD 기반 스트레스 (정상: 20-50ms)
        if rmssd > 40:
            rmssd_stress = 0
        elif rmssd > 20:
            rmssd_stress = (40 - rmssd) / 20 * 50
        else:
            rmssd_stress = 50 + (20 - rmssd) / 20 * 30
        
        # 심박수 기반 스트레스 (정상: 60-100 BPM)
        if mean_hr < 60:
            hr_stress = 0
        elif mean_hr < 100:
            hr_stress = (mean_hr - 60) / 40 * 30
        else:
            hr_stress = 30 + min((mean_hr - 100) / 20 * 20, 20)
        
        # 종합 스트레스 지수
        self.stress_level = min(rmssd_stress * 0.7 + hr_stress * 0.3, 100)
        
        return self.stress_level
    
    def get_stress_category(self):
        """
        스트레스 카테고리 반환
        
        Returns:
            str: 스트레스 레벨 카테고리
        """
        if self.stress_level < 20:
            return "매우 낮음"
        elif self.stress_level < 40:
            return "낮음"
        elif self.stress_level < 60:
            return "보통"
        elif self.stress_level < 80:
            return "높음"
        else:
            return "매우 높음"
    
    def get_stress_color(self):
        """
        스트레스 레벨에 따른 색상 반환 (BGR)
        
        Returns:
            tuple: BGR 색상 값
        """
        if self.stress_level < 20:
            return (0, 255, 0)      # 초록색
        elif self.stress_level < 40:
            return (0, 255, 255)    # 노란색
        elif self.stress_level < 60:
            return (0, 165, 255)    # 주황색
        elif self.stress_level < 80:
            return (0, 100, 255)    # 빨간색-주황색
        else:
            return (0, 0, 255)      # 빨간색

# 테스트 코드
if __name__ == "__main__":
    stress_monitor = StressMonitor()
    
    # 시뮬레이션된 심박 데이터로 테스트
    print("스트레스 모니터 테스트 시작...")
    
    # 정상 심박 시뮬레이션 (70 BPM)
    base_time = time.time()
    for i in range(20):
        # 약간의 변동성을 가진 심박 간격
        interval = 0.857 + np.random.normal(0, 0.05)  # 70 BPM ± 변동
        base_time += interval
        stress_monitor.add_heartbeat(base_time)
    
    stress_index = stress_monitor.calculate_stress_index()
    hrv_metrics = stress_monitor.calculate_hrv_metrics()
    
    print(f"스트레스 지수: {stress_index:.1f}")
    print(f"스트레스 레벨: {stress_monitor.get_stress_category()}")
    
    if hrv_metrics:
        print(f"HRV 메트릭:")
        print(f"  - RMSSD: {hrv_metrics['rmssd']:.1f} ms")
        print(f"  - SDNN: {hrv_metrics['sdnn']:.1f} ms")
        print(f"  - pNN50: {hrv_metrics['pnn50']:.1f} %")
        print(f"  - 평균 심박수: {hrv_metrics['mean_hr']:.1f} BPM")