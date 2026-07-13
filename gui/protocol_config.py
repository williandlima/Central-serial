"""Protocol-specific configuration widgets, switched based on the selected protocol."""
from __future__ import annotations

import serial
from PySide6.QtWidgets import QComboBox, QFormLayout, QStackedWidget, QWidget

SERIAL_PROTOCOLS = ("UART", "RS232", "RS485", "Modbus RTU", "SCPI", "ASCII Custom", "Binary Custom")
CAN_PROTOCOLS = ("CAN Bus",)

BAUD_RATES = (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400)
CAN_BITRATES_KBPS = (125, 250, 500, 1000)


class SerialConfigPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems([str(b) for b in BAUD_RATES])
        self.baudrate_combo.setCurrentText("9600")
        self.baudrate_combo.setEditable(True)

        self.parity_combo = QComboBox()
        self.parity_combo.addItem("None", serial.PARITY_NONE)
        self.parity_combo.addItem("Even", serial.PARITY_EVEN)
        self.parity_combo.addItem("Odd", serial.PARITY_ODD)
        self.parity_combo.addItem("Mark", serial.PARITY_MARK)
        self.parity_combo.addItem("Space", serial.PARITY_SPACE)

        self.databits_combo = QComboBox()
        self.databits_combo.addItem("5", serial.FIVEBITS)
        self.databits_combo.addItem("6", serial.SIXBITS)
        self.databits_combo.addItem("7", serial.SEVENBITS)
        self.databits_combo.addItem("8", serial.EIGHTBITS)
        self.databits_combo.setCurrentText("8")

        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItem("1", serial.STOPBITS_ONE)
        self.stopbits_combo.addItem("1.5", serial.STOPBITS_ONE_POINT_FIVE)
        self.stopbits_combo.addItem("2", serial.STOPBITS_TWO)

        self.flowcontrol_combo = QComboBox()
        self.flowcontrol_combo.addItems(["None", "XON/XOFF", "RTS/CTS"])

        layout.addRow("Baud rate:", self.baudrate_combo)
        layout.addRow("Paridade:", self.parity_combo)
        layout.addRow("Bits de dados:", self.databits_combo)
        layout.addRow("Stop bits:", self.stopbits_combo)
        layout.addRow("Controle de fluxo:", self.flowcontrol_combo)

    def to_dict(self) -> dict:
        return {
            "baudrate": int(self.baudrate_combo.currentText()),
            "parity": self.parity_combo.currentData(),
            "bytesize": self.databits_combo.currentData(),
            "stopbits": self.stopbits_combo.currentData(),
            "xonxoff": self.flowcontrol_combo.currentText() == "XON/XOFF",
            "rtscts": self.flowcontrol_combo.currentText() == "RTS/CTS",
        }


class CanConfigPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.interface_combo = QComboBox()
        self.interface_combo.addItems(["socketcan", "pcan", "vector", "ixxat", "kvaser", "virtual"])
        self.interface_combo.setEditable(True)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["can0", "can1", "PCAN_USBBUS1"])
        self.channel_combo.setEditable(True)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems([f"{b} kbps" for b in CAN_BITRATES_KBPS])
        self.bitrate_combo.setCurrentText("500 kbps")

        self.frame_type_combo = QComboBox()
        self.frame_type_combo.addItem("CAN 2.0A (11 bits)", False)
        self.frame_type_combo.addItem("CAN 2.0B (29 bits)", True)

        layout.addRow("Interface CAN:", self.interface_combo)
        layout.addRow("Canal:", self.channel_combo)
        layout.addRow("Baud rate:", self.bitrate_combo)
        layout.addRow("Tipo de frame:", self.frame_type_combo)

    def to_dict(self) -> dict:
        bitrate_kbps = int(self.bitrate_combo.currentText().split()[0])
        return {
            "interface": self.interface_combo.currentText(),
            "channel": self.channel_combo.currentText(),
            "bitrate": bitrate_kbps * 1000,
            "is_extended": self.frame_type_combo.currentData(),
        }


class ProtocolConfigStack(QStackedWidget):
    """Switches between the serial and CAN configuration pages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_page = SerialConfigPage()
        self.can_page = CanConfigPage()
        self.addWidget(self.serial_page)
        self.addWidget(self.can_page)

    def show_for_protocol(self, protocol: str):
        if protocol in CAN_PROTOCOLS:
            self.setCurrentWidget(self.can_page)
        else:
            self.setCurrentWidget(self.serial_page)

    def current_config(self) -> dict:
        return self.currentWidget().to_dict()
