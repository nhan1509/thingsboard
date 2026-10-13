"""ThingsBoard MQTT TLS transport, RPC commands delivered to a worker queue."""
import json
import queue
import ssl
import paho.mqtt.client as mqtt
from config import TB_HOST, TB_PORT, TB_TOKEN

class ThingsBoardClient:
    def __init__(self, command_queue):
        if not TB_TOKEN:
            raise ValueError('Set TB_TOKEN in .env or environment')
        self.commands = command_queue
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(TB_TOKEN)
        if TB_PORT == 8883:
            self.client.tls_set_context(ssl.create_default_context())
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print('[MQTT] Connected to', TB_HOST)
            client.subscribe('v1/devices/me/rpc/request/+', qos=1)
        else:
            print('[MQTT] Connect failed:', reason_code)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        print('[MQTT] Disconnected:', reason_code)

    def on_message(self, client, userdata, message):
        try:
            request_id = message.topic.rsplit('/', 1)[-1]
            payload = json.loads(message.payload.decode('utf-8'))
            if not isinstance(payload, dict):
                raise ValueError('RPC must be a JSON object')
            self.commands.put_nowait((request_id, payload))
        except (ValueError, UnicodeError, queue.Full) as exc:
            print('[RPC] Invalid or dropped:', exc)

    def start(self):
        self.client.connect_async(TB_HOST, TB_PORT, keepalive=60)
        self.client.loop_start()

    def telemetry(self, values):
        if values:
            self.client.publish('v1/devices/me/telemetry', json.dumps(values), qos=1)

    def attributes(self, values):
        self.client.publish('v1/devices/me/attributes', json.dumps(values), qos=1)

    def reply(self, request_id, values):
        self.client.publish('v1/devices/me/rpc/response/' + request_id,
                            json.dumps(values), qos=1)

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
