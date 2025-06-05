import cv2
import numpy as np
import time
from collections import deque
from scipy import signal
import threading

class rPPGProcessor:
    """rPPG를 이용한 비접촉 심박수 측정"""
    
    def __init__(self, fps=30, buffer_size=150):
        self.fps = fps
        self.buffer_size = buffer_size
        
        # 신호 버퍼
        self.raw_values = deque(maxlen=buffer_size)
        self.timestamps = deque(maxlen=buffer_size)
        
        # 심박수 결과
        self.heart_rate = 0
        self.heart_rates = deque(maxlen=10)  # 이동평균용
        self.signal_quality = 0
        
        # ROI 시각화용
        self.roi_bbox = None
        
        # 스레드 안전을 위한 락
        self.lock = threading.Lock()
        
        # 디버그용
        self.debug_info = {
            'fps': 0,
            'signal_range': 0,
            'peak_freq': 0
        }
        
    def extract_roi(self, frame, face_bbox):
        """얼굴에서 이마 영역 추출"""
        if face_bbox is None:
            return None
            
        x, y, w, h = face_bbox
        
        # 이마 영역 설정 (얼굴 상단 15-35%)
        roi_y = y + int(h * 0.15)
        roi_h = int(h * 0.20)
        roi_x = x + int(w * 0.25)
        roi_w = int(w * 0.50)
        
        # 경계 체크
        frame_h, frame_w = frame.shape[:2]
        roi_y = max(0, roi_y)
        roi_x = max(0, roi_x)
        roi_h = min(roi_h, frame_h - roi_y)
        roi_w = min(roi_w, frame_w - roi_x)
        
        if roi_h <= 0 or roi_w <= 0:
            return None
            
        # ROI 추출
        roi = frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # 시각화용 좌표 저장
        self.roi_bbox = (roi_x, roi_y, roi_w, roi_h)
        
        return roi
    
    def process_frame(self, frame, face_bbox):
        """프레임 처리 및 심박수 업데이트"""
        # ROI 추출
        roi = self.extract_roi(frame, face_bbox)
        if roi is None or roi.size == 0:
            return
        
        # 평균 색상값 계산
        mean_rgb = np.mean(roi, axis=(0, 1))
        
        # 녹색 채널 사용 (가장 강한 PPG 신호)
        green_value = mean_rgb[1]
        
        # 스레드 안전하게 버퍼에 추가
        with self.lock:
            self.raw_values.append(green_value)
            self.timestamps.append(time.time())
            
            # 충분한 데이터가 모이면 심박수 계산
            if len(self.raw_values) >= self.buffer_size:
                self._calculate_heart_rate()
    
    def _calculate_heart_rate(self):
        """심박수 계산 (내부 메서드)"""
        try:
            # 신호 배열 생성
            signal_array = np.array(self.raw_values)
            time_array = np.array(self.timestamps)
            
            # 실제 샘플링 레이트 계산
            time_diff = time_array[-1] - time_array[0]
            if time_diff == 0:
                return
                
            actual_fps = len(time_array) / time_diff
            self.debug_info['fps'] = actual_fps
            
            # 신호 범위 체크 (너무 작으면 노이즈)
            signal_range = np.max(signal_array) - np.min(signal_array)
            self.debug_info['signal_range'] = signal_range
            
            if signal_range < 0.5:  # 신호가 너무 약함
                return
            
            # 신호 전처리
            # 1. 평균 제거 (DC 성분 제거)
            signal_array = signal_array - np.mean(signal_array)
            
            # 2. 트렌드 제거 (느린 변화 제거)
            signal_detrended = signal.detrend(signal_array)
            
            # 3. 대역통과 필터 (0.75Hz ~ 3Hz, 45-180 BPM)
            nyquist = actual_fps / 2
            low = 0.75 / nyquist
            high = min(3.0 / nyquist, 0.99)
            
            if low < high:
                b, a = signal.butter(4, [low, high], btype='band')
                filtered = signal.filtfilt(b, a, signal_detrended)
            else:
                filtered = signal_detrended
            
            # 스무딩 (노이즈 감소)
            window_size = 5
            if len(filtered) > window_size:
                filtered = np.convolve(filtered, np.ones(window_size)/window_size, mode='same')
            
            # FFT로 주파수 분석
            fft_result = np.fft.rfft(filtered)
            frequencies = np.fft.rfftfreq(len(filtered), d=1/actual_fps)
            
            # 파워 스펙트럼
            power_spectrum = np.abs(fft_result) ** 2
            
            # 심박수 범위 내에서 최대 피크 찾기
            valid_range = (frequencies >= 0.75) & (frequencies <= 3.0)
            if not np.any(valid_range):
                return
                
            valid_power = power_spectrum[valid_range]
            valid_freq = frequencies[valid_range]
            
            # 최대 피크 찾기
            peak_idx = np.argmax(valid_power)
            peak_freq = valid_freq[peak_idx]
            heart_rate_bpm = peak_freq * 60
            
            self.debug_info['peak_freq'] = peak_freq
            
            # 신호 품질 평가 (0-100)
            # 피크의 prominence를 기준으로
            peak_power = valid_power[peak_idx]
            mean_power = np.mean(valid_power)
            if mean_power > 0:
                snr = peak_power / mean_power
                self.signal_quality = min(100, int(snr * 15))
            
            # 이상치 필터링
            if 40 < heart_rate_bpm < 180:  # 정상 범위
                self.heart_rates.append(heart_rate_bpm)
                if len(self.heart_rates) >= 3:  # 최소 3개 이상일 때만 평균
                    self.heart_rate = np.median(self.heart_rates)  # 중앙값 사용
            
        except Exception as e:
            print(f"심박수 계산 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def get_heart_rate(self):
        """현재 심박수 반환"""
        with self.lock:
            return self.heart_rate, self.signal_quality
    
    def draw_roi(self, frame):
        """ROI 영역 시각화"""
        if self.roi_bbox is not None:
            x, y, w, h = self.roi_bbox
            # 이마 영역 표시
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.putText(frame, "ROI", (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    def draw_heart_rate(self, frame, x=10, y=150):
        """심박수 정보 표시"""
        hr, quality = self.get_heart_rate()
        
        # 버퍼 상태 표시
        buffer_percent = (len(self.raw_values) / self.buffer_size) * 100
        cv2.putText(frame, f"Buffer: {buffer_percent:.0f}%", 
                   (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        if hr > 0 and 40 < hr < 180:  # 정상 범위 체크
            # 심박수 표시
            color = (0, 255, 0) if quality > 50 else (0, 165, 255)
            cv2.putText(frame, f"HR: {hr:.0f} BPM", 
                       (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 신호 품질 표시
            cv2.putText(frame, f"Signal: {quality}%", 
                       (x, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 하트 아이콘 애니메이션
            if int(time.time() * 2) % 2 == 0:
                cv2.putText(frame, "PROCEEDING", (x+150, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        else:
            # 측정 중 또는 대기 상태
            if len(self.raw_values) < self.buffer_size:
                cv2.putText(frame, "HR: Measuring...", 
                           (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            else:
                cv2.putText(frame, "HR: ???", 
                           (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            cv2.putText(frame, "Keep still", 
                       (x, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    
    def draw_signal_plot(self, frame, x=10, y=250, width=200, height=60):
        """실시간 신호 그래프 표시"""
        if len(self.raw_values) < 2:
            return
            
        # 그래프 배경
        cv2.rectangle(frame, (x, y), (x+width, y+height), (50, 50, 50), -1)
        cv2.rectangle(frame, (x, y), (x+width, y+height), (100, 100, 100), 1)
        
        # 신호 그리기
        with self.lock:
            values = list(self.raw_values)[-width:]
            if len(values) > 1:
                # 정규화
                values = np.array(values)
                values = values - np.mean(values)
                max_val = np.max(np.abs(values))
                if max_val > 0:
                    values = values / max_val * (height//2)
                
                # 선 그리기
                points = []
                for i, val in enumerate(values):
                    px = x + i
                    py = int(y + height//2 - val)
                    points.append((px, py))
                
                points = np.array(points, dtype=np.int32)
                cv2.polylines(frame, [points], False, (0, 255, 0), 1)
            
            # 디버그 정보
            cv2.putText(frame, f"FPS: {self.debug_info['fps']:.1f}", 
                       (x, y+height+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            cv2.putText(frame, f"Range: {self.debug_info['signal_range']:.2f}", 
                       (x+80, y+height+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # 라벨
        cv2.putText(frame, "PPG Signal", (x, y-5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    def reset(self):
        """버퍼 초기화"""
        with self.lock:
            self.raw_values.clear()
            self.timestamps.clear()
            self.heart_rates.clear()
            self.heart_rate = 0
            self.signal_quality = 0