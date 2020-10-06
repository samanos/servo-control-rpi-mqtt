from typing import Iterator, Callable, Protocol, Tuple, List
import asyncio
import logging
from dotenv import load_dotenv
import pigpio
from pydantic import BaseModel
from paho.mqtt.client import Client as PahoClient


class FileHandle(Protocol):
    ...


class PiGpio(Protocol):
    def file_list(self, path: str) -> Tuple[int, bytes]:
        ...

    def file_open(self, path: str, mode: int) -> FileHandle:
        ...

    def file_read(self, handle: FileHandle, count: int) -> Tuple[int, bytes]:
        ...

    def file_close(self, handle: FileHandle) -> None:
        ...

    def write(self, pin: int, value: int) -> None:
        ...

    def set_servo_pulsewidth(self, pin: int, pulse: int) -> None:
        ...

    connected: bool


class Topic:
    servo = "home/servo"
    middle_temp = "home/4way_valve/middle_temp"
    bottom_temp = "home/4way_valve/bottom_temp"
    valve = "dash/open_valve"

    @staticmethod
    def temp(idx: int) -> str:
        return f"dash/temperature/{idx}"


class Options(BaseModel):
    pigpio_hostname: str
    mqtt_username: str
    mqtt_password: str
    mqtt_hostname: str
    mqtt_port: int
    servo_bcm_pin: int
    green_led_bcm_pin: int
    red_led_bcm_pin: int
    temp_sensor_path: str
    temp_measure_period_seconds: int
    initial_middle_temp: int
    initial_bottom_temp: int
    valve_full_close_at: int
    valve_full_open_at: int
    verbose: bool


class State(BaseModel):
    middle_temp: float
    bottom_temp: float


def get_options() -> Options:
    import configargparse

    p = configargparse.ArgParser()
    p.add(
        "--pigpio-hostname",
        env_var="PIGPIO_HOSTNAME",
        help="pigpio hostname",
        default="pigpiod",
    )
    p.add(
        "--mqtt-username",
        required=True,
        env_var="MQTT_USERNAME",
        help="MQTT broker username",
    )
    p.add(
        "--mqtt-password",
        required=True,
        env_var="MQTT_PASSWORD",
        help="MQTT broker password",
    )
    p.add(
        "--mqtt-hostname",
        required=True,
        env_var="MQTT_HOSTNAME",
        help="MQTT broker hostname",
    )
    p.add(
        "--mqtt-port",
        required=True,
        env_var="MQTT_PORT",
        type=int,
        help="MQTT broker port",
    )
    p.add(
        "--servo-bcm-pin",
        env_var="SERVO_BCM_PIN",
        type=int,
        default=18,
        help="BCM port number where the servo is connected to",
    )
    p.add(
        "--green-led-bcm-pin",
        env_var="GREEN_LED_BCM_PIN",
        type=int,
        default=17,
        help="BCM port number where the green led is connected to",
    )
    p.add(
        "--red-led-bcm-pin",
        env_var="RED_LED_BCM_PIN",
        type=int,
        default=27,
        help="BCM port number where the red led is connected to",
    )
    p.add(
        "--temp-sensor-path",
        env_var="TEMP_SENSOR_PATH",
        default="/sys/bus/w1/devices",
        help="Path to the temperature sensor files",
    )
    p.add(
        "--temp-measure-period-seconds",
        env_var="TEMP_MEASURE_PERIOD_SECONDS",
        type=int,
        default=5,
        help="A delay between temperature measurements",
    )
    p.add(
        "--initial-middle-temp",
        env_var="INITIAL_MIDDLE_TEMP",
        type=float,
        default=60,
        help="Initial middle temperature",
    )
    p.add(
        "--initial-bottom-temp",
        env_var="INITIAL_BOTTOM_TEMP",
        type=float,
        default=40,
        help="Initial bottom temperature",
    )
    p.add(
        "--valve-full-close-at",
        env_var="VALVE_FULL_CLOSE_AT",
        type=int,
        default=2010,
        help="Duty cycle at which 4way valve is fully closed",
    )
    p.add(
        "--valve-full-open-at",
        env_var="VALVE_FULL_OPEN_AT",
        type=int,
        default=850,
        help="Duty cycle at which 4way valve is fully open",
    )
    p.add(
        "-v",
        "--verbose",
        env_var="VERBOSE",
        help="Enable verbose logging",
        action="store_const",
        const=True,
        default=False,
    )

    args = p.parse_args()
    return Options(
        pigpio_hostname=args.pigpio_hostname,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        mqtt_hostname=args.mqtt_hostname,
        mqtt_port=args.mqtt_port,
        servo_bcm_pin=args.servo_bcm_pin,
        green_led_bcm_pin=args.green_led_bcm_pin,
        red_led_bcm_pin=args.red_led_bcm_pin,
        temp_sensor_path=args.temp_sensor_path,
        temp_measure_period_seconds=args.temp_measure_period_seconds,
        initial_middle_temp=args.initial_middle_temp,
        initial_bottom_temp=args.initial_bottom_temp,
        valve_full_close_at=args.valve_full_close_at,
        valve_full_open_at=args.valve_full_open_at,
        verbose=args.verbose,
    )


def report_temperature(mqtt: PahoClient, temps: List[float]) -> None:
    for idx, temp in enumerate(temps):
        mqtt.publish(Topic.temp(idx), f"{temp:4.1f}°")


def control_valve(
    options: Options, mqtt: PahoClient, state: State, temps: List[float]
) -> None:
    control_temp = temps[0]
    control = (control_temp - state.bottom_temp) / (
        (state.middle_temp - state.bottom_temp) * 2
    )
    control = max(0, min(1, control))
    mqtt.publish(Topic.valve, "{:4.1f}%".format(control * 100))
    duty = options.valve_full_close_at - (
        control * (options.valve_full_close_at - options.valve_full_open_at)
    )
    mqtt.publish(Topic.servo, prepare_duty_cycle(duty))


def prepare_duty_cycle(duty_cycle: float) -> int:
    return int(duty_cycle / 10) * 10  # duty needs to be divisible by 10


def get_temperature(options: Options, pi: PiGpio) -> Iterator[float]:
    """
    Reads tempreture from sensors on a possible remote RPi.

    Heavily inspired by examples in http://abyz.me.uk/rpi/pigpio/examples.html
    """
    c, files_bytes = pi.file_list(f"{options.temp_sensor_path}/28-00*/w1_slave")
    files = files_bytes.decode("utf8")

    if c >= 0:
        for sensor in files[:-1].split("\n"):
            h = pi.file_open(sensor, pigpio.FILE_READ)
            c, data_bytes = pi.file_read(h, 1000)  # 1000 is plenty to read full file.
            pi.file_close(h)

            data = data_bytes.decode("utf8")

            """
            Typical file contents

            73 01 4b 46 7f ff 0d 10 41 : crc=41 YES
            73 01 4b 46 7f ff 0d 10 41 t=23187
            """

            if "YES" in data:
                (discard, sep, reading) = data.partition(" t=")
                t = float(reading) / 1000.0
                yield t


def turn_on_green(pi: PiGpio, options: Options) -> None:
    pi.write(options.green_led_bcm_pin, 1)


def red_led(pi: PiGpio, options: Options, on: bool) -> None:
    pi.write(options.red_led_bcm_pin, 1 if on else 0)


def get_mqtt_client(options: Options, on_connect, on_message) -> PahoClient:
    mqtt = PahoClient()
    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.username_pw_set(options.mqtt_username, options.mqtt_password)
    mqtt.connect(options.mqtt_hostname, options.mqtt_port, keepalive=60)
    mqtt.loop_start()
    return mqtt


def on_connect_callback(options: Options, pi: PiGpio) -> Callable:
    def on_connect(client, userdata, flags, rc):
        try:
            logging.info("Connected to the MQTT broker.")

            client.subscribe(Topic.servo)
            client.subscribe(Topic.middle_temp)
            client.subscribe(Topic.bottom_temp)

            turn_on_green(pi, options)
        except Exception as ex:
            logging.exception("Error in the on_connect", ex)

    return on_connect


def on_message_callback(options: Options, pi: PiGpio, state: State) -> Callable:
    def on_message(client, userdata, msg):
        try:
            if msg.topic == Topic.servo:
                on_servo_control(pi, options, msg)
            elif msg.topic == Topic.middle_temp:
                on_4way_middle_temp(state, msg)
            elif msg.topic == Topic.bottom_temp:
                on_4way_bottom_temp(state, msg)
            else:
                logging.info(
                    "Received an unhandled message from a topic [%s].", msg.topic
                )
        except Exception as ex:
            logging.exception("Error in the on_message", ex)

    return on_message


def on_servo_control(pi: PiGpio, options: Options, msg) -> None:
    duty = int(msg.payload)
    pi.set_servo_pulsewidth(options.servo_bcm_pin, prepare_duty_cycle(duty))


def on_4way_middle_temp(state: State, msg) -> None:
    logging.info(f"Received new middle temp {msg.payload}")
    state.middle_temp = float(msg.payload)


def on_4way_bottom_temp(state: State, msg) -> None:
    logging.info(f"Received new bottom temp {msg.payload}")
    state.bottom_temp = float(msg.payload)


async def main() -> None:
    load_dotenv()

    options = get_options()
    logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)

    state = State(middle_temp=0, bottom_temp=0)

    pi: PiGpio = pigpio.pi(options.pigpio_hostname)
    if not pi.connected:
        raise AssertionError("Unable to connect to pigpio deamon")

    mqtt = get_mqtt_client(
        options,
        on_connect_callback(options, pi),
        on_message_callback(options, pi, state),
    )

    while True:
        try:
            red_led(pi, options, True)
            temps = list(get_temperature(options, pi))

            report_temperature(mqtt, temps)
            control_valve(options, mqtt, state, temps)
            red_led(pi, options, False)
        except Exception as ex:
            logging.exception("Error in the main loop", ex)

        await asyncio.sleep(options.temp_measure_period_seconds)


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
