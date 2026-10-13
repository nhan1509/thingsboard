"""Main loop: GPIO access on one thread, MQTT callback only queues commands."""
import queue
import time
from config import SEND_INTERVAL
from sensors import Sensors
from motor import Motor
from mqtt_client import ThingsBoardClient


def execute_rpc(request_id, request, motor, tb):
    method = request.get('method')
    try:
        if method != 'setServoAngle':
            raise ValueError('Unknown RPC method: ' + str(method))
        params = request.get('params')
        # Accept both {"params":90} and {"params":{"angle":90}}
        angle = params.get('angle') if isinstance(params, dict) else params
        actual_command = motor.set_angle(angle)
        tb.reply(request_id, {'success': True, 'angle': actual_command})
        tb.attributes({'servoAngle': actual_command})
        print('[RPC] Servo commanded to:', actual_command)
    except (ValueError, TypeError) as exc:
        tb.reply(request_id, {'success': False, 'error': str(exc)})
        print('[RPC] Rejected:', exc)


def main():
    commands = queue.Queue(maxsize=100)
    sensors = Sensors()
    motor = Motor()
    tb = ThingsBoardClient(commands)
    try:
        tb.start()
        next_read = time.monotonic()
        print('Lab01 started. Ctrl+C to exit.')
        while True:
            try:
                request_id, request = commands.get(timeout=0.1)
                execute_rpc(request_id, request, motor, tb)
            except queue.Empty:
                pass
            now = time.monotonic()
            if now >= next_read:
                data = sensors.read()
                if data:
                    tb.telemetry(data)
                    print('[SENSOR]', data)
                next_read = now + SEND_INTERVAL
    except KeyboardInterrupt:
        print('\nStopping...')
    finally:
        tb.close()
        motor.close()
        sensors.close()


if __name__ == '__main__':
    main()
