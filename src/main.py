from w1thermsensor import W1ThermSensor

import time
import random

from flexx import app, ui, event


class Monitor(ui.Widget):

    def init(self):
        with ui.HBox():
            with ui.VBox():
                self.info = ui.Label(text='...')
                ui.Widget(flex=1)

        self.refresh()

    def refresh(self):
        for sensor in W1ThermSensor.get_available_sensors():
            self.info.text = "Sensor %s has temperature %.2f" % (sensor.id, sensor.get_temperature())
            print("Sensor %s has temperature %.2f" % (sensor.id, sensor.get_temperature()))

        app.call_later(1, self.refresh)


if __name__ == '__main__':
    app.serve(Monitor)
    # m = app.launch(Monitor)  # for use during development
    app.start()
