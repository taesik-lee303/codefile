#!/usr/bin/env python3
import cv2
import numpy as np
import lgpio
import spidev
import time
import sys

class ILI9341VideoPlayer_LGPIO:
    def __init__(self, width=240, height=320):
        self.width = width
        self.height = height
        
        # GPIO 설정 (lgpio)
        self.h = lgpio.gpiochip_open(0)
        self.DC_PIN = 24
        self.RESET_PIN = 25
        
        lgpio.gpio_claim_output(self.h, self.DC_PIN)
        lgpio.gpio_claim_output(self.h, self.RESET_PIN)
        
        # SPI 설정
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 64000000
        self.spi.mode = 0
        
        self.init_display()
        
    def send_command(self, cmd):
        lgpio.gpio_write(self.h, self.DC_PIN, 0)
        self.spi.writebytes([cmd])
        
    def send_data(self, data):
        lgpio.gpio_write(self.h, self.DC_PIN, 1)
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            # 대량 데이터는 writebytes2로 전송 (더 빠름)
            self.spi.writebytes2(data)
            
    # 나머지 메서드들은 위의 gpiozero 버전과 동일...#!/usr/bin/env python3
import cv2
import numpy as np
import lgpio
import spidev
import time
import sys

class ILI9341VideoPlayer_LGPIO:
    def __init__(self, width=240, height=320):
        self.width = width
        self.height = height
        
        # GPIO 설정 (lgpio)
        self.h = lgpio.gpiochip_open(0)
        self.DC_PIN = 24
        self.RESET_PIN = 25
        
        lgpio.gpio_claim_output(self.h, self.DC_PIN)
        lgpio.gpio_claim_output(self.h, self.RESET_PIN)
        
        # SPI 설정
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 64000000
        self.spi.mode = 0
        
        self.init_display()
        
    def send_command(self, cmd):
        lgpio.gpio_write(self.h, self.DC_PIN, 0)
        self.spi.writebytes([cmd])
        
    def send_data(self, data):
        lgpio.gpio_write(self.h, self.DC_PIN, 1)
        if isinstance(data, list):
            self.spi.writebytes(data)
        else:
            # 대량 데이터는 writebytes2로 전송 (더 빠름)
            self.spi.writebytes2(data)
            
    # 나머지 메서드들은 위의 gpiozero 버전과 동일...
