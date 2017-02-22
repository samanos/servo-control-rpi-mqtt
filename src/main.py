from flexx import app, ui, event
from w1thermsensor import W1ThermSensor
import time

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
        p = GPIO.PWM(12, 100)
        p.start(0)
        for dc in range(0, 31, 1):
            p.ChangeDutyCycle(dc)
            time.sleep(0.01)
        p.stop()
        #p.ChangeDutyCycle(self.pulse)

    @event.connect('right.mouse_click')
    def right_button_clicked(self, *events):
        self.pulse = self.pulse - 10
        p = GPIO.PWM(12, 100)
        p.start(20)
        for dc in range(30, -1, -1):
            p.ChangeDutyCycle(dc)
            time.sleep(0.01)
        p.stop()
        #p.ChangeDutyCycle(self.pulse)

# Create global relay
relay = Relay()

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(12, GPIO.OUT)

if __name__ == '__main__':
    app.serve(Monitor)
    # m = app.launch(Monitor)  # for use during development
    app.start()
