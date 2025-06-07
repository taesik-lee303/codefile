#!/usr/bin/env python3
# lcd_test_ili9488.py - ILI9488 3.5" LCD 테스트

import RPi.GPIO as GPIO
import spidev
import time
import numpy as np

class ILI9488:
    def __init__(self):
        # GPIO 설정 (표에 맞춰서)
        self.RST = 25  # GPIO25 (Pin 22)
        self.DC = 24   # GPIO24 (Pin 18)
        self.CS = 8    # GPIO8 (Pin 24)
        
        # GPIO 초기화
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.RST, GPIO.OUT)
        GPIO.setup(self.DC, GPIO.OUT)
        
        # SPI 초기화
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # bus 0, device 0
        self.spi.max_speed_hz = 32000000  # 32MHz
        
        # LCD 크기
        self.width = 320
        self.height = 480
        
        print("LCD 초기화 중...")
        self.init_display()
        
    def reset(self):
        """하드웨어 리셋"""
        GPIO.output(self.RST, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(self.RST, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.RST, GPIO.HIGH)
        time.sleep(0.1)
        
    def write_cmd(self, cmd):
        """명령 전송"""
        GPIO.output(self.DC, GPIO.LOW)
        self.spi.writebytes([cmd])
        
    def write_data(self, data):
        """데이터 전송"""
        GPIO.output(self.DC, GPIO.HIGH)
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(data)
    
    def init_display(self):
        """ILI9488 초기화 시퀀스"""
        self.reset()
        
        # Sleep Out
        self.write_cmd(0x11)
        time.sleep(0.12)
        
        # Interface Pixel Format - 16bit/pixel
        self.write_cmd(0x3A)
        self.write_data(0x55)
        
        # Memory Access Control
        self.write_cmd(0x36)
        self.write_data(0x48)
        
        # Display ON
        self.write_cmd(0x29)
        time.sleep(0.1)
        
        print("LCD 초기화 완료!")
    
    def set_window(self, x0, y0, x1, y1):
        """디스플레이 영역 설정"""
        # Column Address Set
        self.write_cmd(0x2A)
        self.write_data(x0 >> 8)
        self.write_data(x0 & 0xFF)
        self.write_data(x1 >> 8)
        self.write_data(x1 & 0xFF)
        
        # Page Address Set
        self.write_cmd(0x2B)
        self.write_data(y0 >> 8)
        self.write_data(y0 & 0xFF)
        self.write_data(y1 >> 8)
        self.write_data(y1 & 0xFF)
        
        # Memory Write
        self.write_cmd(0x2C)
    
    def fill_color(self, color):
        """전체 화면을 단색으로 채우기"""
        print(f"화면을 색상 {color:04X}로 채우는 중...")
        self.set_window(0, 0, self.width-1, self.height-1)
        
        # 16비트 색상을 바이트로 변환
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        
        # 한 번에 보낼 데이터 크기
        chunk_size = 4096
        chunk = [high, low] * (chunk_size // 2)
        
        total_pixels = self.width * self.height
        pixels_sent = 0
        
        GPIO.output(self.DC, GPIO.HIGH)
        while pixels_sent < total_pixels:
            remaining = total_pixels - pixels_sent
            if remaining < chunk_size // 2:
                chunk = [high, low] * remaining
            self.spi.writebytes(chunk)
            pixels_sent += chunk_size // 2
    
    def draw_rect(self, x, y, w, h, color):
        """사각형 그리기"""
        self.set_window(x, y, x+w-1, y+h-1)
        
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        data = [high, low] * (w * h)
        
        GPIO.output(self.DC, GPIO.HIGH)
        # 큰 데이터는 나눠서 전송
        chunk_size = 4096
        for i in range(0, len(data), chunk_size):
            self.spi.writebytes(data[i:i+chunk_size])
    
    def test_pattern(self):
        """테스트 패턴 표시"""
        colors = [
            (0xF800, "빨강"),  # Red
            (0x07E0, "초록"),  # Green
            (0x001F, "파랑"),  # Blue
            (0xFFFF, "흰색"),  # White
            (0x0000, "검정"),  # Black
            (0xFFE0, "노랑"),  # Yellow
            (0xF81F, "자홍"),  # Magenta
            (0x07FF, "청록"),  # Cyan
        ]
        
        print("\n=== LCD 색상 테스트 시작 ===")
        for color, name in colors:
            print(f"{name} 표시 중...")
            self.fill_color(color)
            time.sleep(1)
        
        # 사각형 패턴
        print("\n사각형 패턴 표시 중...")
        self.fill_color(0x0000)  # 검정 배경
        
        # 여러 색상의 사각형 그리기
        self.draw_rect(10, 10, 100, 100, 0xF800)   # 빨강
        self.draw_rect(120, 10, 100, 100, 0x07E0)  # 초록
        self.draw_rect(10, 120, 100, 100, 0x001F)  # 파랑
        self.draw_rect(120, 120, 100, 100, 0xFFE0) # 노랑
        
        time.sleep(3)
        
        # 그라데이션 효과
        print("\n그라데이션 표시 중...")
        for i in range(0, 320, 10):
            color = (i // 10) << 11  # 빨강 그라데이션
            self.draw_rect(i, 200, 10, 100, color)
        
        time.sleep(3)
    
    def cleanup(self):
        """정리"""
        self.spi.close()
        GPIO.cleanup()

def main():
    try:
        print("ILI9488 LCD 테스트 시작")
        print("연결 확인:")
        print("- VCC: 3.3V (Pin 1)")
        print("- GND: GND (Pin 6)")
        print("- CS: GPIO8 (Pin 24)")
        print("- RESET: GPIO25 (Pin 22)")
        print("- DC/RS: GPIO24 (Pin 18)")
        print("- SDI/MOSI: GPIO10 (Pin 19)")
        print("- SCK: GPIO11 (Pin 23)")
        print("- LED: 3.3V (Pin 1)")
        print("")
        
        lcd = ILI9488()
        
        # 기본 색상 테스트
        lcd.test_pattern()
        
        # 애니메이션 효과
        print("\n움직이는 사각형...")
        lcd.fill_color(0x0000)  # 검정 배경
        
        for x in range(0, 220, 5):
            lcd.fill_color(0x0000)  # 이전 것 지우기
            lcd.draw_rect(x, 100, 50, 50, 0xF800)  # 빨간 사각형
            time.sleep(0.05)
        
        print("\nLCD 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if 'lcd' in locals():
            lcd.cleanup()
        print("정리 완료")

if __name__ == "__main__":
    main()
