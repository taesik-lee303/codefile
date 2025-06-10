#!/usr/bin/env python3
from gpiozero import OutputDevice
import spidev
import time

# GPIO 설정 (gpiozero 사용)
dc_pin = OutputDevice(24)
reset_pin = OutputDevice(25)

# SPI 설정
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 32000000
spi.mode = 0

# 리셋
reset_pin.off()
time.sleep(0.1)
reset_pin.on()
time.sleep(0.1)

# 명령/데이터 전송 함수
def send_command(cmd):
    dc_pin.off()  # Command mode
    spi.writebytes([cmd])

def send_data(data):
    dc_pin.on()  # Data mode
    if isinstance(data, list):
        spi.writebytes(data)
    else:
        spi.writebytes([data])

# ILI9341 초기화
send_command(0x01)  # Software Reset
time.sleep(0.2)

print("Display initialized with gpiozero!")

# 정리
spi.close()
dc_pin.close()
reset_pin.close()
