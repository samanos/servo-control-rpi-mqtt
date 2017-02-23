from flexx import app, ui, event
from w1thermsensor import W1ThermSensor

class Relay(event.HasEvents):

    def __init__(self):
        super().__init__()
        self.refresh()

    def refresh(self):
        self.system_info()
        app.call_later(1, self.refresh)

    @event.emitter
    def system_info(self):
        temperature = self.get_temperature()
        print("Temperature %s" % temperature)
        return dict(temp=temperature)

    def get_temperature(self):
        try:
            return [(sensor.id, sensor.get_temperature()) for sensor in W1ThermSensor.get_available_sensors()]
        except FileNotFoundError:
            return [1.11, 2.22, 3.33, 4.44]

class Monitor(ui.Widget):

    min_duty = 500
    init_duty = 700
    max_duty = 3000

    def init(self):
        with ui.HBox():
            with ui.VBox():
                with ui.HBox():
                    self.temps = [
                        ui.Label(text='??°', style='font-weight: bold; font-size: xx-large'),
                        ui.Label(text='??°', style='font-weight: bold; font-size: xx-large')
                    ]
                with ui.HBox():
                    ui.Label(text="{} <= ".format(self.min_duty))
                    self.duty_edit = ui.LineEdit(text=self.init_duty)
                    ui.Label(text=" <= {}".format(self.max_duty))
                with ui.HBox():
                    self.duty_slider = ui.Slider(flex=1, min=self.min_duty, max=self.max_duty, step=10)

        # Relay global info into this app
        relay.connect(self.push_info, 'system_info:' + self.id)

    def push_info(self, *events):
        ev = events[-1]
        for temp, label in zip(ev.temp, self.temps):
            label.text = "{:4.1f}°".format(temp)

    @event.connect('duty_edit.text')
    def duty_edited(self, *events):
        duty = int(events[-1].new_value)
        if self.min_duty <= duty <= self.max_duty:
            self.duty_slider.value = duty
            servo.set_servo(18, duty)

    @event.connect('duty_slider.value')
    def duty_slided(self, *events):
        duty = events[-1].new_value
        self.duty_edit.text = duty
        servo.set_servo(18, duty)

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

# Create global relay
relay = Relay()

servo = get_servo()

if __name__ == '__main__':
    app.serve(Monitor)
    # m = app.launch(Monitor)  # for use during development
    app.start()
