"""
Remotely control a DataLogger

Created on Thu Apr  1 15:14:39 2021 by Benedikt Moneke
"""

# Standard packages.
import datetime
import logging
from pathlib import Path
from time import strftime

# 3rd party
import numpy as np
import pint
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import pyqtSlot

from pyleco.utils.parser import parse_command_line_parameters

# Local packages.
from DataLoggerBase import DataLoggerBase
from analysis.data import load_datalogger_file
from data.Settings import Settings

log = logging.Logger(__name__)
log.addHandler(logging.StreamHandler())
u = pint.get_application_registry()
unit = u


def seconds_utc_to_time(seconds: int):
    """Return the time of a seconds value."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    today_dt = datetime.datetime.combine(today, datetime.time(),
                                         datetime.timezone.utc)
    return (today_dt + datetime.timedelta(seconds=seconds)).astimezone().time()


class DataLoggerViewer(DataLoggerBase):
    """View data of a DataLogger

    Open files saved by the DataLogger and visualize the contained data.

    :param name: Name of this program.
    :param host: Host of the Coordinator.
    """

    def __init__(self, name: str = "DataLoggerViewer", **kwargs) -> None:
        # Use initialization of parent class QMainWindow.
        super().__init__(name=name, settings_dialog_class=Settings, **kwargs)

        # Add dictionaries for internal storage.
        self.plots = []
        self.lists = {}
        self.units = {}
        self.last_path = ""  # last path used

    def setup_actions(self) -> None:
        super().setup_actions()
        self.actionStart.triggered.connect(self.start)

    def setup_buttons(self) -> None:
        for widget in (self.cbTimer, self.sbTimeout, self.cbTrigger, self.leTrigger,
                       self.cbValueLast, self.cbValueMean, self.cbRepeat, self.leHeader,
                       self.leVariables):
            widget.setEnabled(False)
        self.actionStart.setToolTip("Load a measurement file.")

    def setup_timers(self):
        self.timer = QtCore.QTimer()  # for plots.
        pass  # do nothing, no timers needed.

    "GUI interaction"
    # Controls
    @pyqtSlot()
    def start(self):
        """Start a measurement."""
        settings = QtCore.QSettings()
        file_name = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open file",
            directory=self.last_path or settings.value('savePath', type=str),
            filter=(";;".join((
                "JSON (*.json)",
                f"This year ({strftime('%Y')}_*)",
                f"This month ({strftime('%Y_%m')}_*)",
                f"Today ({strftime('%Y_%m_%d')}*)",
                "Pickled (*.pkl)",
                "All files (*)",
                )))
        )[0]
        if file_name == "":
            return  # user pressed cancel
        self.last_path = file_name
        path = Path(file_name)
        header, data, meta = load_datalogger_file(path)
        self.lists = data
        self.leHeader.setPlainText(header.rsplit("\n", maxsplit=1)[0])
        self.set_configuration(meta.get("configuration", {}))
        if "time" in data.keys() and "time_h" not in data.keys():
            self.lists["time_h"] = list(np.array(data["time"]) / 3600)
            self.variables = self.variables + ["time_h"]
            d = self.units
            d["time_h"] = "h"
            self.units = d
        self.current_units = self.units
        self.leSavedName.setText(path.name)
        self.signals.update_plots.emit()
        self.signals.started.emit()
        # get length of data points:
        try:
            length = len(self.lists[list(self.lists).pop()])
        except IndexError:
            pass
        else:
            self.lbCount.setText(f"Data points: {length}")


if __name__ == '__main__':
    doc = DataLoggerViewer.__doc__
    kwargs = parse_command_line_parameters(
        logger=log,
        parser_description=doc.split(":param", maxsplit=1)[0] if doc else None,
    )
    app = QtWidgets.QApplication([])
    window = DataLoggerViewer(**kwargs)
    app.exec()
