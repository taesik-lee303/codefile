#!/usr/bin/env python3
"""
2.2인치 SPI TFT LCD (ILI9341) 디스플레이 테스트 스크립트
라즈베리파이5에서 정상 작동 확인용
"""

import time
import board
import digitalio
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ili9341

def test_lcd_display():
    """LCD 디스플레이 테스트 함수"""
    
    print("=" * 50)
    print("2.2인치 SPI TFT LCD (ILI9341) 테스트 시작")
    print("=" * 50)
    
    try:
        # SPI 설정 (하드웨어 SPI 사용)
        print("1. SPI 인터페이스 초기화 중...")
        spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        
        # GPIO 핀 설정 (연결표에 따라)
        print("2. GPIO 핀 설정 중...")
        cs = digitalio.DigitalInOut(board.CE0)    # GPIO8 (Pin 24) - CS
        dc = digitalio.DigitalInOut(board.D24)    # GPIO24 (Pin 18) - DC/RS
        reset = digitalio.DigitalInOut(board.D25) # GPIO25 (Pin 22) - RESET
        
        print("   - CS: GPIO8 (Pin 24)")
        print("   - DC/RS: GPIO24 (Pin 18)")
        print("   - RESET: GPIO25 (Pin 22)")
        print("   - SCK: GPIO11 (Pin 23)")
        print("   - MOSI: GPIO10 (Pin 19)")
        
        # ILI9341 디스플레이 초기화
        print("3. ILI9341 디스플레이 초기화 중...")
        display = adafruit_ili9341.ILI9341(
            spi,
            cs=cs,
            dc=dc,
            rst=reset,
            baudrate=24000000  # 24MHz
        )
        
        print(f"   - 디스플레이 크기: {display.width} x {display.height}")
        print("   ✓ 디스플레이 초기화 성공!")
        
        # 테스트 이미지 생성
        print("4. 테스트 이미지 생성 중...")
        
        # 테스트 1: 전체 화면 색상 테스트
        colors = [
            (255, 0, 0),    # 빨강
            (0, 255, 0),    # 초록
            (0, 0, 255),    # 파랑
            (255, 255, 0),  # 노랑
            (255, 0, 255),  # 마젠타
            (0, 255, 255),  # 시안
            (255, 255, 255) # 흰색
        ]
        
        color_names = ["빨강", "초록", "파랑", "노랑", "마젠타", "시안", "흰색"]
        
        for i, (color, name) in enumerate(zip(colors, color_names)):
            print(f"   테스트 {i+1}/7: {name} 화면 표시")
            image = Image.new("RGB", (display.width, display.height), color)
            display.image(image)
            time.sleep(1)
        
        # 테스트 2: 그래픽 테스트
        print("5. 그래픽 패턴 테스트 중...")
        
        # 체크보드 패턴
        print("   - 체크보드 패턴")
        image = Image.new("RGB", (display.width, display.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        square_size = 20
        for x in range(0, display.width, square_size):
            for y in range(0, display.height, square_size):
                if (x // square_size + y // square_size) % 2 == 0:
                    draw.rectangle([x, y, x + square_size, y + square_size], fill=(255, 255, 255))
        
        display.image(image)
        time.sleep(2)
        
        # 그라데이션 테스트
        print("   - 그라데이션 패턴")
        image = Image.new("RGB", (display.width, display.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        for x in range(display.width):
            color_value = int((x / display.width) * 255)
            draw.line([(x, 0), (x, display.height)], fill=(color_value, color_value, color_value))
        
        display.image(image)
        time.sleep(2)
        
        # 테스트 3: 텍스트 표시 테스트
        print("6. 텍스트 표시 테스트 중...")
        
        image = Image.new("RGB", (display.width, display.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 기본 폰트 사용
        try:
            # 시스템 폰트 로드 시도
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            # 기본 폰트 사용
            font = ImageFont.load_default()
        
        # 텍스트 그리기
        texts = [
            "LCD Test Success!",
            "ILI9341 Display",
            "Raspberry Pi 5",
            "Resolution:",
            f"{display.width} x {display.height}",
            "",
            "All tests passed!"
        ]
        
        y_pos = 10
        for text in texts:
            draw.text((10, y_pos), text, font=font, fill=(255, 255, 255))
            y_pos += 25
        
        # 색상 바 추가
        bar_height = 20
        bar_y = display.height - bar_height - 10
        colors_bar = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        bar_width = display.width // len(colors_bar)
        
        for i, color in enumerate(colors_bar):
            x1 = i * bar_width
            x2 = (i + 1) * bar_width
            draw.rectangle([x1, bar_y, x2, bar_y + bar_height], fill=color)
        
        display.image(image)
        
        print("7. 테스트 완료!")
        print("   ✓ 모든 테스트가 성공적으로 완료되었습니다!")
        print("   ✓ LCD 디스플레이가 정상적으로 작동합니다!")
        
        # 10초간 결과 표시
        print("   (10초 후 테스트 종료)")
        time.sleep(10)
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        print("\n문제 해결 방법:")
        print("1. 연결 상태 확인:")
        print("   - VCC: 3.3V (Pin 1)")
        print("   - GND: GND (Pin 6)")
        print("   - CS: GPIO8 (Pin 24)")
        print("   - RESET: GPIO25 (Pin 22)")
        print("   - DC/RS: GPIO24 (Pin 18)")
        print("   - SDI/MOSI: GPIO10 (Pin 19)")
        print("   - SCK: GPIO11 (Pin 23)")
        print("   - LED: 3.3V (Pin 1)")
        print("\n2. SPI 활성화 확인:")
        print("   sudo raspi-config > Interface Options > SPI > Enable")
        print("\n3. 필요 라이브러리 설치:")
        print("   pip install adafruit-circuitpython-ili9341 pillow")
        
        return False

def check_spi_status():
    """SPI 상태 확인"""
    import os
    
    print("SPI 인터페이스 상태 확인...")
    
    # /dev/spidev 확인
    spi_devices = [f for f in os.listdir('/dev') if f.startswith('spidev')]
    
    if spi_devices:
        print(f"✓ SPI 디바이스 발견: {spi_devices}")
        return True
    else:
        print("❌ SPI 디바이스를 찾을 수 없습니다.")
        print("sudo raspi-config에서 SPI를 활성화해주세요.")
        return False

def main():
    """메인 함수"""
    print("라즈베리파이5 LCD 디스플레이 테스트")
    print("=" * 50)
    
    # SPI 상태 확인
    if not check_spi_status():
        return
    
    # LCD 테스트 실행
    try:
        test_lcd_display()
    except KeyboardInterrupt:
        print("\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")

if __name__ == "__main__":
    main()
