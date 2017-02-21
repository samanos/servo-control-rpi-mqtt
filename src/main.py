from flexx import app, ui, event
from w1thermsensor import W1ThermSensor


class Relay(event.HasEvents):

    def __init__(self):
        super().__init__()
        self.refresh()

    @event.emitter
    def system_info(self):
        temperature = [(sensor.id, sensor.get_temperature()) for sensor in W1ThermSensor.get_available_sensors()]
        return dict(temp=temperature)

    def refresh(self):
        self.system_info()
        app.call_later(1, self.refresh)


class Monitor(ui.Widget):

    def init(self):
        with ui.HBox():
            with ui.VBox():
                self.info = ui.Label(text='...')
                ui.Widget(flex=1)

        # Relay global info into this app
        relay.connect(self.push_info, 'system_info:' + self.id)

    def push_info(self, *events):
        ev = events[-1]
        self.info.text = "Temperatures" % (ev.temp)
        print("Temperatures" % (ev.temp))


# Create global relay
relay = Relay()



if __name__ == '__main__':
    app.serve(Monitor)
    # m = app.launch(Monitor)  # for use during development
    app.start()
