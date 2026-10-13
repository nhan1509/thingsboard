"""Read DHT11 and HC-SR04 on Raspberry Pi (BCM numbering)."""
import time
import board
import adafruit_dht
from gpiozero import DistanceSensor
from config import TRIGGER_PIN, ECHO_PIN

class Sensors:
    def __init__(self):
        self.dht = adafruit_dht.DHT11(board.D4, use_pulseio=False)
        self.ultrasonic = DistanceSensor(echo=ECHO_PIN, trigger=TRIGGER_PIN,
                                         max_distance=4, queue_len=5)

    def read(self):
        result = {}
        try:
            temp = self.dht.temperature
            humid = self.dht.humidity
            if temp is not None:
                result['temperature'] = float(temp)
            if humid is not None:
                result['humidity'] = float(humid)
        except (RuntimeError, OverflowError) as exc:
            print('[DHT11] Read retry:', exc)
        try:
            result['distance'] = round(self.ultrasonic.distance * 100, 1)
        except Exception as exc:
            print('[HC-SR04] Read failed:', exc)
        return result

    def close(self):
        self.dht.exit()
        self.ultrasonic.close()
