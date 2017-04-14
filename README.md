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
