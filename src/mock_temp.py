import asyncio
import json
import logging
import main
import os
from pathlib import Path

def get_options():
    import configargparse
    p = configargparse.ArgParser()
    p.add('--mqtt-username', required=True, env_var='MQTT_USERNAME', help='MQTT broker username')
    p.add('--mqtt-password', required=True, env_var='MQTT_PASSWORD', help='MQTT broker password')
    p.add('--mqtt-hostname', required=True, env_var='MQTT_HOSTNAME', help='MQTT broker hostname')
    p.add('--mqtt-port', required=True, env_var='MQTT_PORT', type=int, help='MQTT broker port')

    p.add('--sensor-directory', env_var='SENSOR_DIRECTORY', default='/tmp/w1/devices', help='Directory where sensor files will be created')

    p.add('-v', '--verbose', help='Enable verbose logging', action='store_const', const=logging.DEBUG)

    return p.parse_args()

def on_connect(client, userdata, flags, rc):
    logging.info("Connected to the MQTT broker.")
    client.subscribe("mock/temp")

def on_message(client, userdata, msg):
    temp = json.loads(msg.payload)

    sensor_path = Path('{}/28-00000{}/w1_slave'.format(options.sensor_directory, temp.get('id')))
    sensor_path.parent.mkdir(parents=True, exist_ok=True)

    with sensor_path.open('w+') as f:
        f.write('70 01 4b 46 7f ff 10 10 e1 : crc=e1 YES\n')
        f.write('70 01 4b 46 7f ff 10 10 e1 t={}0'.format(int(float(temp.get('value')) * 100)))

if __name__ == "__main__":
    options = get_options()
    logging.basicConfig(level=options.verbose or logging.INFO)

    path = Path(options.sensor_directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    mqtt = main.get_mqtt_client(options, on_connect, on_message)

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()