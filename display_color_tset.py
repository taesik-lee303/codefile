#!/usr/bin/env python3
from gpiozero import OutputDevice
import spidev
import time

class DisplayTest:
    def __init__(self):
        # GPIO 설정
        self.dc_pin = OutputDevice(24)
        self.reset_pin = OutputDevice(25)
        
        # SPI 설정
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 16000000  # 속도를 낮춰서 테스트
        self.spi.mode = 0
        
        print("Initializing display...")
        self.init_display()
        
    def reset(self):
        self.reset_pin.off()
        time.sleep(0.1)
        self.reset_pin.on()
        time.sleep(0.1)
        
    def send_command(self, cmd):
        self.dc_pin.off()
        self.spi.writebytes([cmd])
        
    def send_data(self, data):
        self.dc_pin.on()
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(list(data))
            
    def init_display(self):
        self.reset()
        
        # Software Reset
        self.send_command(0x01)
        time.sleep(0.15)
        
        # Display OFF
        self.send_command(0x28)
        
        # Power Control B
        self.send_command(0xCF)
        self.send_data([0x00, 0xC1, 0x30])
        
        # Power on sequence control
        self.send_command(0xED)
        self.send_data([0x64, 0x03, 0x12, 0x81])
        
        # Driver timing control A
        self.send_command(0xE8)
        self.send_data([0x85, 0x00, 0x78])
        
        # Power control A
        self.send_command(0xCB)
        self.send_data([0x39, 0x2C, 0x00, 0x34, 0x02])
        
        # Pump ratio control
        self.send_command(0xF7)
        self.send_data([0x20])
        
        # Driver timing control B
        self.send_command(0xEA)
        self.send_data([0x00, 0x00])
        
        # Power Control 1
        self.send_command(0xC0)
        self.send_data([0x23])
        
        # Power Control 2
        self.send_command(0xC1)
        self.send_data([0x10])
        
        # VCOM Control 1
        self.send_command(0xC5)
        self.send_data([0x3E, 0x28])
        
        # VCOM Control 2
        self.send_command(0xC7)
        self.send_data([0x86])
        
        # Memory Access Control
        self.send_command(0x36)
        self.send_data([0x48])
        
        # Pixel Format Set
        self.send_command(0x3A)
        self.send_data([0x55])  # 16-bit
        
        # Frame Rate Control
        self.send_command(0xB1)
        self.send_data([0x00, 0x18])
        
        # Display Function Control
        self.send_command(0xB6)
        self.send_data([0x08, 0x82, 0x27])
        
        # Sleep Out
        self.send_command(0x11)
        time.sleep(0.12)
        
        # Display ON
        self.send_command(0x29)
        time.sleep(0.05)
        
    def fill_color(self, color):
        """화면을 단색으로 채우기"""
        # Set Column Address
        self.send_command(0x2A)
        self.send_data([0x00, 0x00, 0x00, 0xEF])  # 0-239
        
        # Set Page Address  
        self.send_command(0x2B)
        self.send_data([0x00, 0x00, 0x01, 0x3F])  # 0-319
        
        # Memory Write
        self.send_command(0x2C)
        
        # 색상 데이터 전송 (RGB565)
        # 빨간색 = 0xF800, 초록색 = 0x07E0, 파란색 = 0x001F
        color_high = (color >> 8) & 0xFF
        color_low = color & 0xFF
        
        # 한 번에 전송할 픽셀 수
        pixels_per_chunk = 1000
        color_data = [color_high, color_low] * pixels_per_chunk
        
        total_pixels = 240 * 320
        for i in range(0, total_pixels, pixels_per_chunk):
            remaining = min(pixels_per_chunk, total_pixels - i)
            if remaining < pixels_per_chunk:
                color_data = [color_high, color_low] * remaining
            self.spi.writebytes(color_data)
            
    def test_colors(self):
        """여러 색상 테스트"""
        colors = [
            ("Red", 0xF800),
            ("Green", 0x07E0),
            ("Blue", 0x001F),
            ("White", 0xFFFF),
            ("Black", 0x0000),
            ("Yellow", 0xFFE0),
            ("Cyan", 0x07FF),
            ("Magenta", 0xF81F)
        ]
        
        for name, color in colors:
            print(f"Displaying {name}")
            self.fill_color(color)
            time.sleep(1)
            
    def cleanup(self):
        self.spi.close()
        self.dc_pin.close()
        self.reset_pin.close()

# 테스트 실행
if __name__ == "__main__":
    test = DisplayTest()
    print("Starting color test...")
    test.test_colors()
    test.cleanup()
    print("Test complete!")
