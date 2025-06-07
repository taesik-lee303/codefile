#!/usr/bin/env python3
# lcd_test_rpi5.py - 라즈베리파이 5용 ILI9488 LCD 테스트

from gpiozero import OutputDevice
import spidev
import time

class ILI9488_RPi5:
    def __init__(self):
        # GPIO 설정 (gpiozero 사용)
        print("GPIO 초기화 중...")
        self.RST = OutputDevice(25)  # GPIO25 (Pin 22)
        self.DC = OutputDevice(24)   # GPIO24 (Pin 18)
        # CS는 SPI가 자동으로 처리
        
        # SPI 초기화
        print("SPI 초기화 중...")
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # bus 0, device 0 (CE0)
        self.spi.max_speed_hz = 16000000  # 16MHz로 시작
        self.spi.mode = 0
        
        # LCD 크기
        self.width = 320
        self.height = 480
        
        print("LCD 초기화 중...")
        self.init_display()
        
    def reset(self):
        """하드웨어 리셋"""
        print("LCD 리셋...")
        self.RST.on()
        time.sleep(0.1)
        self.RST.off()
        time.sleep(0.1)
        self.RST.on()
        time.sleep(0.1)
        
    def write_cmd(self, cmd):
        """명령 전송"""
        self.DC.off()  # DC=0 for command
        self.spi.writebytes([cmd])
        
    def write_data(self, data):
        """데이터 전송"""
        self.DC.on()  # DC=1 for data
        if isinstance(data, int):
            self.spi.writebytes([data])
        else:
            self.spi.writebytes(list(data))
    
    def init_display(self):
        """ILI9488 초기화 시퀀스"""
        self.reset()
        
        # Sleep Out
        self.write_cmd(0x11)
        time.sleep(0.12)
        
        # Power Control
        self.write_cmd(0xC0)
        self.write_data(0x17)
        self.write_data(0x15)
        
        self.write_cmd(0xC1)
        self.write_data(0x41)
        
        # VCOM Control
        self.write_cmd(0xC5)
        self.write_data(0x00)
        self.write_data(0x12)
        self.write_data(0x80)
        
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
    
    def fill_color(self, color):
        """전체 화면을 단색으로 채우기"""
        print(f"화면을 색상 0x{color:04X}로 채우는 중...")
        
        # Set window to full screen
        self.write_cmd(0x2A)  # Column Address Set
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data((self.width-1) >> 8)
        self.write_data((self.width-1) & 0xFF)
        
        self.write_cmd(0x2B)  # Page Address Set
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data((self.height-1) >> 8)
        self.write_data((self.height-1) & 0xFF)
        
        self.write_cmd(0x2C)  # Memory Write
        
        # 색상 데이터 전송
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        
        # 작은 청크로 나눠서 전송
        chunk_size = 1024
        total_pixels = self.width * self.height
        
        self.DC.on()  # Data mode
        for i in range(0, total_pixels, chunk_size // 2):
            remaining = min(chunk_size // 2, total_pixels - i)
            chunk = [high, low] * remaining
            self.spi.writebytes(chunk)
    
    def simple_test(self):
        """간단한 색상 테스트"""
        colors = [
            (0xF800, "빨강"),
            (0x07E0, "초록"),
            (0x001F, "파랑"),
            (0xFFFF, "흰색"),
            (0x0000, "검정"),
        ]
        
        print("\n=== LCD 색상 테스트 ===")
        for color, name in colors:
            print(f"{name} 표시 중...")
            self.fill_color(color)
            time.sleep(1.5)
        
        print("테스트 완료!")
    
    def cleanup(self):
        """정리"""
        self.spi.close()
        self.RST.close()
        self.DC.close()

# 더 간단한 테스트
def simple_gpio_test():
    """GPIO만 테스트"""
    print("\n=== 간단한 GPIO 테스트 ===")
    from gpiozero import LED
    import time
    
    # LED 클래스로 GPIO 제어
    rst = LED(25)
    dc = LED(24)
    
    print("RST 핀 테스트 (GPIO25)...")
    for i in range(3):
        rst.on()
        print(f"  RST=HIGH ({i+1}/3)")
        time.sleep(0.5)
        rst.off()
        print(f"  RST=LOW ({i+1}/3)")
        time.sleep(0.5)
    
    print("\nDC 핀 테스트 (GPIO24)...")
    for i in range(3):
        dc.on()
        print(f"  DC=HIGH ({i+1}/3)")
        time.sleep(0.5)
        dc.off()
        print(f"  DC=LOW ({i+1}/3)")
        time.sleep(0.5)
    
    rst.close()
    dc.close()
    print("\nGPIO 테스트 완료!")

def main():
    try:
        print("라즈베리파이 5 - ILI9488 LCD 테스트")
        print("=" * 50)
        
        # 먼저 GPIO만 테스트
        response = input("GPIO 테스트를 먼저 실행하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            simple_gpio_test()
            print("")
        
        # LCD 테스트
        response = input("LCD 전체 테스트를 실행하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            lcd = ILI9488_RPi5()
            lcd.simple_test()
            lcd.cleanup()
        
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
