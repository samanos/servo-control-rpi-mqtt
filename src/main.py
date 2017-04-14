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
    p.add('--temp-sensor-path', env_var='TEMP_SENSOR_PATH', default='/sys/bus/w1/devices', help='Path to the temperature sensor files')

    p.add('--temp-measure-period-seconds', env_var='TEMP_MEASURE_PERIOD_SECONDS', type=int, default=5, help='A delay between temperature measurements')

    p.add('--initial-middle-temp', env_var='INITIAL_MIDDLE_TEMP', type=float, default=60, help='Initial middle temperature')
    p.add('--initial-bottom-temp', env_var='INITIAL_BOTTOM_TEMP', type=float, default=40, help='Initial bottom temperature')

    p.add('--valve-full-close-at', env_var='VALVE_FULL_CLOSE_AT', type=int, default=2010, help='Duty cycle at which 4way valve is fully closed')
    p.add('--valve-full-open-at', env_var='VALVE_FULL_OPEN_AT', type=int, default=850, help='Duty cycle at which 4way valve is fully open')

    p.add('-v', '--verbose', help='Enable verbose logging', action='store_const', const=logging.DEBUG)

    return p.parse_args()

@asyncio.coroutine
def report_temperature():
    try:
        for idx, temp in enumerate(get_temperature()):
            mqtt.publish("dash/temperature/{}".format(idx), "{:4.1f}°".format(temp))
    except Exception as ex:
        logging.error('Exception in `report_temperature`: %s', ex)
    finally:
        yield from asyncio.sleep(options.temp_measure_period_seconds)
        asyncio.async(report_temperature())

@asyncio.coroutine
def control_valve():
    try:
        control_temp = get_temperature()[0]
        control = (control_temp - bottom_temp) / ((middle_temp - bottom_temp) * 2)
        control = max(0, min(1, control))
        mqtt.publish("dash/open_valve", "{:4.1f}%".format(control * 100))
        duty = options.valve_full_close_at - (control * (options.valve_full_close_at - options.valve_full_open_at))
        servo.set_servo(options.servo_bcm_pin, prepare_duty_cycle(duty))
    except Exception as ex:
        logging.error('Exception in `control_valve`: %s', ex)
    finally:
        yield from asyncio.sleep(options.temp_measure_period_seconds)
        asyncio.async(control_valve())

def prepare_duty_cycle(duty_cycle):
    return int(duty_cycle / 10) * 10 # duty needs to be divisible by 10

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

def get_temp_sensor(options):
    from w1thermsensor import W1ThermSensor
    W1ThermSensor.BASE_DIRECTORY = options.temp_sensor_path
    return W1ThermSensor

def turn_on_green():
    try:
        import RPIO
        RPIO.setup(options.green_led_bcm_pin, RPIO.OUT)
        RPIO.output(options.green_led_bcm_pin, True)
    except SystemError:
        logging.debug("Not on a RPi. Turning on green virtual console led. *blink*")

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

    client.publish("home/4way_valve/middle_temp", middle_temp, retain=True)
    client.publish("home/4way_valve/bottom_temp", bottom_temp, retain=True)

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
    servo.set_servo(options.servo_bcm_pin, prepare_duty_cycle(duty))

def on_4way_middle_temp(msg):
    logging.info('Received new middle temp %s', msg.payload)
    global middle_temp
    middle_temp = float(msg.payload)

def on_4way_bottom_temp(msg):
    logging.info('Received new bottom temp %s', msg.payload)
    global bottom_temp
    bottom_temp = float(msg.payload)

if __name__ == "__main__":
    options = get_options()
    logging.basicConfig(level=options.verbose or logging.INFO)

    middle_temp = options.initial_middle_temp
    bottom_temp = options.initial_bottom_temp

    servo = get_servo()
    temp_sensor = get_temp_sensor(options)
    mqtt = get_mqtt_client(options, on_connect, on_message)

    loop = asyncio.get_event_loop()
    try:
        asyncio.async(report_temperature())
        asyncio.async(control_valve())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
