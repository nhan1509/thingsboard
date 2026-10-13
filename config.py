import os

TB_HOST = os.getenv('TB_HOST', 'demo.thingsboard.io')
TB_PORT = int(os.getenv('TB_PORT', '8883'))
TB_TOKEN = os.getenv('TB_TOKEN', '')
SEND_INTERVAL = float(os.getenv('SEND_INTERVAL', '2'))
DHT_PIN = 4
TRIGGER_PIN = 23
ECHO_PIN = 24
SERVO_PIN = 18
