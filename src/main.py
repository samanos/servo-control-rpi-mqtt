import asyncio
import os

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

servo = get_servo()

mqtt = paho.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
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

