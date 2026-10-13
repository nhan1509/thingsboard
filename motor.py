"""Servo driver; reports commanded angle, not measured physical angle."""
from gpiozero import AngularServo
from config import SERVO_PIN

class Motor:
    def __init__(self):
        self.servo = AngularServo(SERVO_PIN, min_angle=0, max_angle=180,
                                  min_pulse_width=0.0005,
                                  max_pulse_width=0.0025,
                                  initial_angle=None)
        self.angle = None

    def set_angle(self, angle):
        if isinstance(angle, bool) or not isinstance(angle, (int, float)):
            raise ValueError('Angle must be a number')
        if not 0 <= angle <= 180:
            raise ValueError('Angle must be between 0 and 180')
        self.servo.angle = float(angle)
        self.angle = float(angle)
        return self.angle

    def close(self):
        self.servo.close()
