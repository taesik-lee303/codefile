#!/usr/bin/env python3
import cv2
import numpy as np
from gpiozero import OutputDevice
import spidev
import time
import struct
from PIL import Image
import sys

class ILI9341VideoPlayer:
    def __init__(self, width=240, height=320):
        # 디스플레이 크기
        self.width = width
        self.height = height
        
        # GPIO 설정 (gpiozero)
        self.dc_pin = OutputDevice(24)
        self.reset_pin = OutputDevice(25)
        
        # SPI 설정
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 64000000  # 64MHz
        self.spi.mode = 0
        
        # 디스플레이 초기화
        self.init_display()
        
    def reset(self):
        """하드웨어 리셋"""
        self.reset_pin.off()
        time.sleep(0.1)
        self.reset_pin.on()
        time.sleep(0.1)
        
    def send_command(self, cmd, data=None):
        """명령 전송"""
        self.dc_pin.off()  # Command mode
        self.spi.writebytes([cmd])
        if data:
            self.send_data(data)
            
    def send_data(self, data):
        """데이터 전송"""
        self.dc_pin.on()  # Data mode
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            self.spi.writebytes([data])
            
    def init_display(self):
        """ILI9341 초기화 시퀀스"""
        self.reset()
        
        # Software Reset
        self.send_command(0x01)
        time.sleep(0.15)
        
        # Power Control A
        self.send_command(0xCB, [0x39, 0x2C, 0x00, 0x34, 0x02])
        
        # Power Control B
        self.send_command(0xCF, [0x00, 0xC1, 0x30])
        
        # Driver Timing Control A
        self.send_command(0xE8, [0x85, 0x00, 0x78])
        
        # Driver Timing Control B
        self.send_command(0xEA, [0x00, 0x00])
        
        # Power On Sequence Control
        self.send_command(0xED, [0x64, 0x03, 0x12, 0x81])
        
        # Pump Ratio Control
        self.send_command(0xF7, [0x20])
        
        # Power Control 1
        self.send_command(0xC0, [0x23])
        
        # Power Control 2
        self.send_command(0xC1, [0x10])
        
        # VCOM Control 1
        self.send_command(0xC5, [0x3e, 0x28])
        
        # VCOM Control 2
        self.send_command(0xC7, [0x86])
        
        # Memory Access Control
        self.send_command(0x36, [0x48])  # 0x48 for 240x320
        
        # Pixel Format Set
        self.send_command(0x3A, [0x55])  # 16-bit color
        
        # Frame Rate Control
        self.send_command(0xB1, [0x00, 0x18])
        
        # Display Function Control
        self.send_command(0xB6, [0x08, 0x82, 0x27])
        
        # Gamma Set
        self.send_command(0x26, [0x01])
        
        # Sleep Out
        self.send_command(0x11)
        time.sleep(0.12)
        
        # Display ON
        self.send_command(0x29)
        
        # Clear screen
        self.fill_screen(0x0000)
        
    def set_window(self, x0, y0, x1, y1):
        """표시 영역 설정"""
        # Column Address Set
        self.send_command(0x2A)
        self.send_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
        
        # Page Address Set
        self.send_command(0x2B)
        self.send_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
        
        # Memory Write
        self.send_command(0x2C)
        
    def fill_screen(self, color):
        """화면 전체를 특정 색으로 채우기"""
        self.set_window(0, 0, self.width - 1, self.height - 1)
        
        # 16비트 색상을 바이트로 변환
        color_bytes = struct.pack('>H', color) * (self.width * self.height)
        
        # SPI 버퍼 크기 제한으로 나누어 전송
        chunk_size = 4096
        for i in range(0, len(color_bytes), chunk_size):
            self.spi.writebytes(list(color_bytes[i:i + chunk_size]))
            
    def display_frame(self, frame):
        """프레임을 디스플레이에 표시"""
        # 이미지 크기 조정
        if frame.shape[:2] != (self.height, self.width):
            frame = cv2.resize(frame, (self.width, self.height))
            
        # BGR을 RGB로 변환
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
        # RGB888을 RGB565로 변환
        r = (frame[:, :, 0] >> 3) & 0x1F
        g = (frame[:, :, 1] >> 2) & 0x3F
        b = (frame[:, :, 2] >> 3) & 0x1F
        rgb565 = (r << 11) | (g << 5) | b
        
        # 바이트 배열로 변환
        data = rgb565.astype(np.uint16).tobytes()
        
        # 디스플레이에 전송
        self.set_window(0, 0, self.width - 1, self.height - 1)
        
        # 청크로 나누어 전송
        chunk_size = 4096
        for i in range(0, len(data), chunk_size):
            self.spi.writebytes(list(data[i:i + chunk_size]))
            
    def play_video(self, video_path):
        """비디오 재생"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Cannot open video {video_path}")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = 25
            
        frame_time = 1.0 / fps
        
        print(f"Playing video: {video_path}")
        print(f"FPS: {fps}")
        print("Press Ctrl+C to stop")
        
        try:
            frame_count = 0
            start_time = time.time()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    # 비디오 끝나면 처음부터
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                    
                # 프레임 표시
                frame_start = time.time()
                self.display_frame(frame)
                frame_end = time.time()
                
                # FPS 유지
                elapsed = frame_end - frame_start
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
                    
                frame_count += 1
                
                # 성능 모니터링 (10프레임마다)
                if frame_count % 10 == 0:
                    total_elapsed = time.time() - start_time
                    actual_fps = frame_count / total_elapsed
                    print(f"Frame: {frame_count}, FPS: {actual_fps:.2f}")
                    
        except KeyboardInterrupt:
            print("\nStopping video playback...")
        finally:
            cap.release()
            self.cleanup()
            
    def cleanup(self):
        """정리"""
        self.fill_screen(0x0000)  # 화면 지우기
        self.spi.close()
        self.dc_pin.close()
        self.reset_pin.close()

# 사용 예
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 video_player.py <video_file.mov>")
        sys.exit(1)
        
    video_file = sys.argv[1]
    player = ILI9341VideoPlayer()
    player.play_video(video_file)
