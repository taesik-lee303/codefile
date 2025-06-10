#!/usr/bin/env python3
import cv2
import numpy as np
from gpiozero import OutputDevice
import spidev
import time
import sys

class ILI9341VideoPlayer:
    def __init__(self):
        self.width = 240
        self.height = 320
        
        # GPIO 설정
        self.dc_pin = OutputDevice(24)
        self.reset_pin = OutputDevice(25)
        
        # SPI 설정 (속도를 낮춰서 시작)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 32000000  # 32MHz로 시작
        self.spi.mode = 0
        
        self.init_display()
        
    def init_display(self):
        """최소한의 초기화"""
        # 리셋
        self.reset_pin.off()
        time.sleep(0.1)
        self.reset_pin.on()
        time.sleep(0.1)
        
        # 기본 초기화 명령
        self.send_command(0x01)  # Software Reset
        time.sleep(0.15)
        
        self.send_command(0x11)  # Sleep Out
        time.sleep(0.12)
        
        # 픽셀 포맷 설정
        self.send_command(0x3A)
        self.send_data(0x55)  # 16-bit color
        
        # 메모리 접근 제어
        self.send_command(0x36)
        self.send_data(0x48)  # 올바른 방향 설정
        
        # 디스플레이 ON
        self.send_command(0x29)
        time.sleep(0.05)
        
        # 테스트: 화면을 빨간색으로
        self.test_fill_red()
        time.sleep(1)
        
    def send_command(self, cmd):
        self.dc_pin.off()
        self.spi.writebytes([cmd])
        
    def send_data(self, data):
        self.dc_pin.on()
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(list(data))
            
    def test_fill_red(self):
        """화면을 빨간색으로 채우기 (테스트)"""
        # 전체 화면 영역 설정
        self.send_command(0x2A)  # Column Address Set
        self.send_data([0x00, 0x00, 0x00, 0xEF])
        
        self.send_command(0x2B)  # Page Address Set
        self.send_data([0x00, 0x00, 0x01, 0x3F])
        
        self.send_command(0x2C)  # Memory Write
        
        # 빨간색 데이터 전송
        red_pixel = [0xF8, 0x00]  # RGB565 빨간색
        chunk = red_pixel * 1000
        
        for _ in range(77):  # 240*320/1000 ≈ 77
            self.spi.writebytes(chunk)
            
    def display_frame(self, frame):
        """프레임 표시 (수정된 버전)"""
        # 크기 조정
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
            
        # BGR을 RGB로 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # RGB888을 RGB565로 변환
        r = (frame_rgb[:, :, 0] >> 3).astype(np.uint16)
        g = (frame_rgb[:, :, 1] >> 2).astype(np.uint16)
        b = (frame_rgb[:, :, 2] >> 3).astype(np.uint16)
        
        rgb565 = (r << 11) | (g << 5) | b
        
        # 바이트 순서 변경 (big-endian)
        rgb565_bytes = rgb565.astype('>u2').tobytes()
        
        # 전송 영역 설정
        self.send_command(0x2A)
        self.send_data([0x00, 0x00, 0x00, 0xEF])
        
        self.send_command(0x2B)
        self.send_data([0x00, 0x00, 0x01, 0x3F])
        
        self.send_command(0x2C)
        
        # 데이터 전송 (청크로 나누어서)
        chunk_size = 4096
        data_list = list(rgb565_bytes)
        
        for i in range(0, len(data_list), chunk_size):
            self.spi.writebytes(data_list[i:i+chunk_size])
            
    def play_video(self, video_path):
        """비디오 재생"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"Cannot open video: {video_path}")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_delay = 1.0 / fps
        
        print(f"Playing: {video_path} at {fps:.1f} FPS")
        print("Press Ctrl+C to stop")
        
        frame_count = 0
        
        try:
            while True:
                start_time = time.time()
                
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                    
                self.display_frame(frame)
                
                # FPS 제어
                elapsed = time.time() - start_time
                if elapsed < frame_delay:
                    time.sleep(frame_delay - elapsed)
                    
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"Frame: {frame_count}")
                    
        except KeyboardInterrupt:
            print("\nStopped")
        finally:
            cap.release()
            self.cleanup()
            
    def cleanup(self):
        self.spi.close()
        self.dc_pin.close()
        self.reset_pin.close()

if __name__ == "__main__":
    player = ILI9341VideoPlayer()
    
    if len(sys.argv) > 1:
        player.play_video(sys.argv[1])
    else:
        print("Testing display with colors...")
        time.sleep(2)
