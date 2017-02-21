from flexx import app, ui, event
from w1thermsensor import W1ThermSensor
import wiringpi


class Relay(event.HasEvents):

    def __init__(self):
        super().__init__()
        self.refresh()

    @event.emitter
    def system_info(self):
        temperature = [(sensor.id, sensor.get_temperature()) for sensor in W1ThermSensor.get_available_sensors()]
        print("Temperature %s" % temperature)
        return dict(temp=temperature)

    def refresh(self):
        self.system_info()
        app.call_later(1, self.refresh)


class Monitor(ui.Widget):

    def init(self):
        with ui.HBox():
            with ui.VBox():
                self.info = ui.Label(text='...')
                self.left = ui.Button(flex=1, text='Kaire')
                self.right = ui.Button(flex=1, text='Dešine')

        # Relay global info into this app
        relay.connect(self.push_info, 'system_info:' + self.id)

        self.pulse = 50

    def push_info(self, *events):
        ev = events[-1]
        self.info.text = "Pulse %s, Temperature %s" % (self.pulse, ev.temp)

    @event.connect('left.mouse_click')
    def left_button_clicked(self, *events):
        self.pulse = self.pulse + 10
        wiringpi.pwmWrite(18, self.pulse)

    @event.connect('right.mouse_click')
    def left_button_clicked(self, *events):
        self.pulse = self.pulse - 10
        wiringpi.pwmWrite(18, self.pulse)

# Create global relay
relay = Relay()

# Prepare PWM
# use 'GPIO naming'
wiringpi.wiringPiSetupGpio()

# set #18 to be a PWM output
wiringpi.pinMode(18, wiringpi.GPIO.PWM_OUTPUT)

# set the PWM mode to milliseconds stype
wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)

# divide down clock
wiringpi.pwmSetClock(192)
wiringpi.pwmSetRange(2000)

delay_period = 0.01

if __name__ == '__main__':
    app.serve(Monitor)
    # m = app.launch(Monitor)  # for use during development
    app.start()
