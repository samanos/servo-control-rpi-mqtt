import asyncio
import os
import ssl
from tempfile import NamedTemporaryFile

import paho.mqtt.client as paho


TEMPERATURE_REPORT_PERIOD_SECONDS=1

@asyncio.coroutine
def report_temperature():
    yield from asyncio.sleep(TEMPERATURE_REPORT_PERIOD_SECONDS)
    for idx, temp in enumerate(get_temperature()):
        mqtt.publish("dash/temperature/{}".format(idx), "{:4.1f}°".format(temp))
    asyncio.async(report_temperature())

def get_temperature():
    try:
        from w1thermsensor import W1ThermSensor
        return [sensor.get_temperature() for sensor in W1ThermSensor.get_available_sensors()]
    except FileNotFoundError:
        return [1.11, 2.22, 3.33, 4.44]

class ConsoleServo:
    def set_servo(self, pin, duty):
        print("Setting pin {} to {}".format(pin, duty))

def get_servo():
    try:
        from RPIO import PWM
        return PWM.Servo()
    except SystemError:
        print("Not runnig on RPi.")
        return ConsoleServo()

def on_connect(client, userdata, flags, rc):
    print("connected")
    client.subscribe("home/servo")

def on_message(client, userdata, msg):
    duty = msg.payload
    print(msg.topic + " " + str(msg.payload))

# def prepare_key_and_certs():
#     ca_crt = NamedTemporaryFile(delete=False)
#     ca_crt.write(os.environ.get('MQTT_CA_CRT').replace('\\n', '\n').encode("utf8"))
#     ca_crt.close()
#
#     cl_crt = NamedTemporaryFile(delete=False)
#     cl_crt.write(os.environ.get('MQTT_CL_CRT').replace('\\n', '\n').encode("utf8"))
#     cl_crt.close()
#
#     private_key = NamedTemporaryFile(delete=False)
#     private_key.write(os.environ.get('MQTT_PRIVATE_KEY').replace('\\n', '\n').encode("utf8"))
#     private_key.close()
#
#     return (ca_crt.name, cl_crt.name, private_key.name)

servo = get_servo()

#(ca_crt, cl_crt, private_key) = prepare_key_and_certs()

mqtt = paho.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
# mqtt.tls_set(ca_certs=ca_crt, certfile=cl_crt, keyfile=private_key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
mqtt.username_pw_set(os.environ.get('MQTT_USERNAME'), os.environ.get('MQTT_PASSWORD'))
mqtt.connect(os.environ.get('MQTT_HOSTNAME'), int(os.environ.get('MQTT_PORT')), keepalive=60)
mqtt.loop_start()

loop = asyncio.get_event_loop()
try:
    asyncio.async(report_temperature())
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()

