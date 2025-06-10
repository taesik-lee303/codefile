from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import ili9341
from PIL import Image, ImageDraw

# 디바이스 설정
serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, 
             bus_speed_hz=32000000)
device = ili9341(serial, rotate=1)  # 90도 회전

# 테스트 그리기
with canvas(device) as draw:
    draw.rectangle(device.bounding_box, outline="white", fill="red")
    draw.text((10, 10), "Hello!", fill="white")

print("Display test complete!")
