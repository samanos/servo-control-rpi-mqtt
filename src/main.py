import asyncio
import logging


def get_options():
    import configargparse
    p = configargparse.ArgParser()
    p.add('--mqtt-username', required=True, env_var='MQTT_USERNAME', help='MQTT broker username')
    p.add('--mqtt-password', required=True, env_var='MQTT_PASSWORD', help='MQTT broker password')
    p.add('--mqtt-hostname', required=True, env_var='MQTT_HOSTNAME', help='MQTT broker hostname')
    p.add('--mqtt-port', required=True, env_var='MQTT_PORT', type=int, help='MQTT broker port')

    p.add('--servo-bcm-pin', env_var='SERVO_BCM_PIN', type=int, default=18, help='BCM port number where the servo is connected to')
    p.add('--green-led-bcm-pin', env_var='GREEN_LED_BCM_PIN', type=int, default=17, help='BCM port number where the green led is connected to')
    p.add('--red-led-bcm-pin', env_var='RED_LED_BCM_PIN', type=int, default=27, help='BCM port number where the red led is connected to')

    p.add('--temp-measure-period-seconds', env_var='TEMP_MEASURE_PERIOD_SECONDS', type=int, default=1, help='A delay between temperature measurements')

    p.add('-v', '--verbose', help='Enable verbose logging', action='store_const', const=logging.DEBUG)

    return p.parse_args()

@asyncio.coroutine
def report_temperature():
    yield from asyncio.sleep(options.temp_measure_period_seconds)
    for idx, temp in enumerate(get_temperature()):
        print(idx, temp)
        mqtt.publish("dash/temperature/{}".format(idx), "{:4.1f}°".format(temp))
    asyncio.async(report_temperature())

def get_temperature():
    try:
        return [get_temperature_from_sensor(sensor) for sensor in temp_sensor.get_available_sensors()]
    except FileNotFoundError:
        return [1.11, 2.22, 3.33, 4.44]

def get_temperature_from_sensor(sensor):
    from w1thermsensor.core import SensorNotReadyError
    try:
        return sensor.get_temperature()
    except SensorNotReadyError:
        return 0

class ConsoleServo:
    def set_servo(self, pin, duty):
        logging.debug("Setting pin %s to %s", pin, duty)

def get_servo():
    try:
        from RPIO import PWM
        return PWM.Servo()
    except SystemError:
        logging.debug("Not on a RPi. Will use a console servo.")
        return ConsoleServo()

def get_temp_sensor():
    from w1thermsensor import W1ThermSensor
    try:
        W1ThermSensor.get_available_sensors()
        return W1ThermSensor
    except FileNotFoundError:
        W1ThermSensor.BASE_DIRECTORY = "/tmp/w1/devices"
        return W1ThermSensor

def turn_on_green():
    try:
        import RPIO
        RPIO.setup(options.green_led_bcm_pin, RPIO.OUT)
        RPIO.output(options.green_led_bcm_pin, True)
    except SystemError:
        logging.debug("Not on a RPi. Turning on green led.")

def get_mqtt_client(options, on_connect, on_message):
    import paho.mqtt.client as paho
    mqtt = paho.Client()
    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.username_pw_set(options.mqtt_username, options.mqtt_password)
    mqtt.connect(options.mqtt_hostname, options.mqtt_port, keepalive=60)
    mqtt.loop_start()
    return mqtt

def on_connect(client, userdata, flags, rc):
    logging.info("Connected to the MQTT broker.")
    client.subscribe("home/servo")
    client.subscribe("home/4way_valve/middle_temp")
    client.subscribe("home/4way_valve/bottom_temp")
    turn_on_green()

def on_message(client, userdata, msg):
    if msg.topic == 'home/servo':
        on_servo_control(msg)
    elif msg.topic == 'home/4way_valve/middle_temp':
        on_4way_middle_temp(msg)
    elif msg.topic == 'home/4way_valve/bottom_temp':
        on_4way_bottom_temp(msg)
    else:
        logging.info('Received an unhandled message from a topic [%s].', msg.topic)

def on_servo_control(msg):
    duty = int(msg.payload)
    servo.set_servo(options.servo_bcm_pin, duty)

def on_4way_middle_temp(msg):
    logging.info('Received new middle temp %s', msg.payload)

def on_4way_bottom_temp(msg):
    logging.info('Received new bottom temp %s', msg.payload)

if __name__ == "__main__":
    options = get_options()
    logging.basicConfig(level=options.verbose or logging.INFO)

    servo = get_servo()
    temp_sensor = get_temp_sensor()
    mqtt = get_mqtt_client(options, on_connect, on_message)

    loop = asyncio.get_event_loop()
    try:
        asyncio.async(report_temperature())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
