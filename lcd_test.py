from luma.core.interface.serial import spi
from luma.lcd.device import ili9341
from PIL import Image, ImageDraw

serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
device = ili9341(serial, width=240, height=320, rotate=0)

img = Image.new("RGB", (240, 320), "black")
draw = ImageDraw.Draw(img)
draw.rectangle((20, 20, 220, 300), outline="white", width=3)
device.display(img)
