#!/usr/bin/env python3
import lgpio
import spidev
import time

# GPIO 핸들 열기
h = lgpio.gpiochip_open(0)

# GPIO 핀 번호
DC_PIN = 24
RESET_PIN = 25

# GPIO 출력으로 설정
lgpio.gpio_claim_output(h, DC_PIN)
lgpio.gpio_claim_output(h, RESET_PIN)

# SPI 설정
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 32000000

# 리셋
lgpio.gpio_write(h, RESET_PIN, 0)
time.sleep(0.1)
lgpio.gpio_write(h, RESET_PIN, 1)
time.sleep(0.1)

def send_command(cmd):
    lgpio.gpio_write(h, DC_PIN, 0)
    spi.writebytes([cmd])

def send_data(data):
    lgpio.gpio_write(h, DC_PIN, 1)
    if isinstance(data, list):
        spi.writebytes(data)
    else:
        spi.writebytes([data])

# 테스트
send_command(0x01)
time.sleep(0.2)
print("Display initialized with lgpio!")

# 정리
spi.close()
lgpio.gpiochip_close(h)
