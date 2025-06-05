import multiprocessing
import RPi.GPIO as GPIO
import adafruit_dht
import board
import time
import random
import json
from kafka import KafkaProducer

PIR_PIN = 17  # OUT 핀을 연결한 GPIO 핀 번호
SENSOR_PIN = 23  # LM393 센서의 디지털 출력 핀 번호
# Kafka configuration
KAFKA_SERVERS = ['203.250.148.52:47995', '203.250.148.52:47996', '203.250.148.52:47997']
TOPIC = 'sensor'
def json_serializer(data):
    return json.dumps(data).encode('utf-8')
if __name__ == "__main__":
        # Initialize Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=json_serializer,
        buffer_memory=33554432,  # 32 MB
        linger_ms=100,           # 100 ms delay
        batch_size=16384,        # 16 KB
        retries=5,
        retry_backoff_ms=200     # 200 ms backoff
    )
    GPIO.setmode(GPIO.BCM)  # BCM 핀 번호 체계 사용
    dht_device = adafruit_dht.DHT11(board.D4)
    movement_list = []
    sound_list = []
    try:
        while True:
            try:
                
                time.sleep(1)
                # 온습도
                temperature = dht_device.temperature
                humidity = dht_device.humidity
                if temperature is not None and humidity is not None:
                    print(f'Temperature: {temperature:.1f}C  Humidity: {humidity:.1f}%')
                else:
                    print('Failed to retrieve data from the sensor')
                    continue
                    
                # 움직임
                GPIO.setmode(GPIO.BCM)  # BCM 핀 번호 체계 사용
                GPIO.setup(PIR_PIN, GPIO.IN)  # PIR 센서를 입력으로 설정
                movement = GPIO.input(PIR_PIN)
                time.sleep(1)
                if len(movement_list) > 20:
                    movement_list.pop()
                movement_list.append(movement)
                
                display_movement = "보통"
                if sum(movement_list) > 3:
                    display_movement = "활발함"
                print('move sum : '+str(movement_list))
                    
                #소음
                # GPIO 모드 설정
                GPIO.setmode(GPIO.BCM)  # BCM 핀 번호 체계 사용
                GPIO.setup(SENSOR_PIN, GPIO.IN)
                noise_detected = GPIO.input(SENSOR_PIN)
                time.sleep(1)
                
                if len(sound_list) > 20:
                    sound_list.pop()
                sound_list.append(noise_detected)
                display_sound = "조용함"
                if sum(movement_list) > 3:
                    display_sound = "약간 시끄러움"
                elif sum(movement_list) > 5:
                    display_sound = "시끄러움"
                print('sound sum : '+str(movement_list))
                    
                sound = random.randint(40,60)
                if noise_detected == 1 :
                    sound = random.randint(100,140)
                
                entity = {
                    "observed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "data" : {
                        "movement" : display_movement,
                        "humidty": {
                            "out": 45,
                            "in": humidity 
                        },
                        "temperature" : {
                            "out" : 13, 
                            "in" : temperature 
                        },
                        "sound" : display_sound,
                        "sound_in" : sound,
                        "gas" : "유출 없음"
                    }
                }
                # Produce the entity to Kafka
                producer.send(TOPIC, entity)
                producer.flush()  # Ensure data is sent
                
                # Display log message
                print(f"Produced message to Kafka: {entity}")
                GPIO.cleanup()

                # Main loop delay
                time.sleep(1)
                # Clean up GPIO pins and close Kafka producer on exit
            except RuntimeError as error:
                print(f'Error reading from sensor: {error}')
    except KeyboardInterrupt:
        print("Interrupted by user")
        # Clean up GPIO and close producer on exit
        GPIO.cleanup()
        producer.close()

    # finally:
        # # Clean up GPIO and close producer on exit
        # GPIO.cleanup()
        # producer.close()
        