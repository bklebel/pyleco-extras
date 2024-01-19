"""
Plot window of the Datalogger.

Created on Fri Jul  9 14:32:56 2021 by Benedikt Burger.
"""

import logging
from typing import Any, Protocol

import pint
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Slot as pyqtSlot  # type: ignore


class DataLoggerGuiProtocol(Protocol):
    lists: dict[str, list[Any]]
    current_units: dict[str, str]
    timer: QtCore.QTimer


class PlotGroupWidget(QtWidgets.QWidget):
    """Abstract class for the plot widgets."""

    def __init__(self, parent: DataLoggerGuiProtocol, autoCut=0, grid=False, log=None, **kwargs):
        super().__init__()
        self._setup_actions()
        self._setup_ui()
        self._layout()
        self.show()
        self.main_window = parent
        self.parent = parent  # type: ignore
        self.autoCut = autoCut
        self.sbAutoCut.setValue(autoCut)

        if log is None:
            self.log = logging.getLogger(__name__)
        else:
            self.log = log.getChild("Plot")

        # Configure comboboxes and plot.
        self.plotWidget.showGrid(x=grid, y=grid)
        self.setup_plot()
        self.keys = ["index", ""]
        self.getXkeys()
        self.getYkeys()

        self.restore_configuration(configuration=kwargs)

        self.setX()

    def _setup_actions(self) -> None:
        """Set up all the actions."""
        self.actionly = QtGui.QAction("ly")  # type: ignore
        self.actionly.setToolTip("Show a yellow line.")
        self.actionly.setCheckable(True)
        self.actionlg = QtGui.QAction("lg")  # type: ignore
        self.actionlg.setToolTip("Show a green line.")
        self.actionlg.setCheckable(True)
        self.actionv = QtGui.QAction("v")  # type: ignore
        self.actionv.setToolTip("Show the value with a larger fontsize.")
        self.actionv.setCheckable(True)

        # Connect actions to slots
        self.actionly.toggled.connect(self.toggleLineY)
        self.actionlg.toggled.connect(self.toggleLineG)
        self.actionv.toggled.connect(self.toggleV)

    def _setup_ui(self) -> None:
        """Generate the UI elements."""
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.addAction(self.actionlg)
        self.plotWidget.addAction(self.actionly)
        self.toolbar = QtWidgets.QToolBar(self)
        self.toolbar.setVisible(False)
        self.pbOptions = QtWidgets.QToolButton()
        self.pbOptions.setText("...")
        self.pbOptions.setCheckable(True)
        self.pbOptions.setToolTip("Show plot options (Ctrl + D).")
        self.pbOptions.setShortcut("Ctrl+D")
        self.bbX = QtWidgets.QComboBox()
        self.bbX.setMaxVisibleItems(15)
        self.bbX.setToolTip("X axis.")
        self.sbAutoCut = QtWidgets.QSpinBox()
        self.sbAutoCut.setMaximum(100000)
        self.sbAutoCut.setToolTip("Show the last number of values. If 0, show all values.")
        self.lbValue = QtWidgets.QLabel("last value")
        self.lbValue.setToolTip("Last value of the current axis.")

        # # Connect widgets to slots
        self.bbX.activated.connect(self.setX)
        self.sbAutoCut.valueChanged.connect(self.setAutoCut)
        self.pbOptions.toggled.connect(self.toolbar.setVisible)

    def _layout(self) -> None:
        """Organize the elements into a layout."""
        raise NotImplementedError

    def setup_plot(self):
        """Configure the plotting area."""
        self.plotWidget.setLabel('bottom', "index")

    def closeEvent(self, event):
        """Close the plot."""
        try:
            self.main_window.timer.timeout.disconnect(self.update)
            self.main_window.signals.closing.disconnect(self.close)  # type: ignore
        except TypeError:
            pass  # Already disconnected.
        self.clear_plot()
        event.accept()

    def get_configuration(self) -> dict[str, Any]:
        """Get the current plot configuration."""
        configuration = {
            "type": type(self).__name__,
            "x_key": self.bbX.currentText(),
            "autoCut": self.autoCut,
            "ly": self.lineY.value() if self.actionly.isChecked() else False,
            "lg": self.lineG.value() if self.actionlg.isChecked() else False,
        }
        return configuration

    def restore_configuration(self, configuration: dict[str, Any]) -> None:
        for key, value in configuration.items():
            if key == "x_key":
                self.bbX.setCurrentText(value)
            elif key == "autoCut":
                self.sbAutoCut.setValue(value)
            elif key == "ly":
                if value is not False:
                    self.toggleLineY(True, start=value)
                    self.actionly.setChecked(True)
            elif key == "lg":
                if value is not False:
                    self.toggleLineG(True, start=value)
                    self.actionlg.setChecked(True)

    @pyqtSlot()
    def update(self):
        """Update the plots."""
        raise NotImplementedError

    def clear_plot(self):
        """Clear the plots."""
        raise NotImplementedError

    def generate_axis_label(self, key: str) -> str:
        """Get the units string of `key`."""
        units = self.main_window.current_units.get(key, None)
        if units is None:
            return key
        elif isinstance(units, str):
            return f"{key} ({units})"
        elif isinstance(units, pint.Quantity):
            return f"{key} ({units:~})"
        else:
            return f"{key} ({units})"

    def setKeyNames(self, comboBox):
        """Set the names for the `comboBox`."""
        current = comboBox.currentText()
        comboBox.clear()
        if comboBox == self.bbX:
            comboBox.addItem('index')
        comboBox.addItems(self.main_window.lists.keys())
        comboBox.setCurrentText(current)

    def getXkeys(self):
        """Get the available keys for the x axis."""
        self.setKeyNames(self.bbX)

    @pyqtSlot()
    def setX(self) -> None:
        """Adjust the current x label."""
        text = self.bbX.currentText()
        self.keys[0] = text
        self.plotWidget.setLabel('bottom', text=self.generate_axis_label(text))
        self.update()

    def getYkeys(self):
        """Get the available keys for the y axis."""
        raise NotImplementedError()

    @pyqtSlot(int)
    def setAutoCut(self, value) -> None:
        """Set the current auto cut value."""
        self.autoCut = value

    @pyqtSlot()
    def updateKeys(self) -> None:
        """Update the combobox keys."""
        self.getXkeys()
        self.getYkeys()

    # Action slots
    @pyqtSlot(bool)
    def toggleLineY(self, checked, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineY.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineY = self.plotWidget.addLine(y=start, pen='y', movable=True)

    @pyqtSlot(bool)
    def toggleLineG(self, checked: bool, start: float = 0) -> None:
        """Toggle to show a horizontal line."""
        try:
            self.lineG.setVisible(checked)
        except AttributeError:
            if checked:
                self.lineG = self.plotWidget.addLine(y=start, pen='g', movable=True)

    @pyqtSlot(bool)
    def toggleV(self, checked: bool) -> None:
        """Make the font size large."""
        font = QtGui.QFont()
        if checked:
            font.setPointSize(48)
            self.lbValue.setFont(font)
        else:
            self.lbValue.setFont(font)
