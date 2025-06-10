#!/usr/bin/env python3
# 핀 연결 테스트
from gpiozero import LED
import time

# DC와 RESET 핀 테스트
dc_led = LED(24)
reset_led = LED(25)

print("Testing DC pin (GPIO 24)...")
for _ in range(5):
    dc_led.on()
    time.sleep(0.5)
    dc_led.off()
    time.sleep(0.5)

print("Testing RESET pin (GPIO 25)...")
for _ in range(5):
    reset_led.on()
    time.sleep(0.5)
    reset_led.off()
    time.sleep(0.5)

print("If LEDs connected to these pins blink, connections are OK")
