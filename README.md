# Servo Control over MQTT

Originally based from [https://github.com/resin-io-projects/simple-server-python](https://github.com/resin-io-projects/simple-server-python)

# Running

When running the app make sure that the following environment and configuration variables are set with the appropriate values:

| Env var         | Value                                   |
|-----------------|-----------------------------------------|
| MQTT_HOSTNAME   | MQTT endpoint hostname                  |
| MQTT_PORT       | MQTT endpoint port                      |
| MQTT_USERNAME   | MQTT broker username                    |
| MQTT_PASSWORD   | MQTT broker password                    |

| Resin Config var            | Value                                   |
|-----------------------------|-----------------------------------------|
| RESIN_HOST_CONFIG_dtoverlay | w1-gpio,gpiopin=22                      |

# Pinout

| Connection | Colour | Physical Pin | RPi Pin Name | Function  |
|------------|--------|--------------|--------------|-----------|
| 1.         | Brown  | 13           | GPIO 27      | Red Led   |
| 2.         | Brown  | 11           | GPIO 17      | Green Led |
| 3.         | Purple | 9            | Ground       |           |
| 4.         | Gray   | 15           | GPIO 22      | W1 Temp   |
| 5.         | Gray   | 17           | 3v3 Power    |           |
| 6.         | Brown  | 12           | GPIO 18      | Servo     |
