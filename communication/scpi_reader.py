"""SCPI monitor: ASCII line-based responses over a serial connection."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from communication.serial_manager import SerialManager, SerialSettings
from protocols.parser import LineAccumulator

PROTOCOL_NAME = "SCPI"


class ScpiReader(QObject):
    packetReceived = Signal(object)
    connected = Signal()
    disconnected = Signal()
    errorOccurred = Signal(str)
    reconnecting = Signal(int)

    def __init__(self, settings: SerialSettings, terminator: bytes = b"\n", auto_reconnect: bool = True, parent=None):
        super().__init__(parent)
        self._manager = SerialManager(settings, auto_reconnect=auto_reconnect)
        self._accumulator = LineAccumulator(terminator=terminator)
        self._manager.rawDataReceived.connect(self._on_raw_data)
        self._manager.connected.connect(self.connected)
        self._manager.disconnected.connect(self.disconnected)
        self._manager.errorOccurred.connect(self.errorOccurred)
        self._manager.reconnecting.connect(self.reconnecting)

    def start(self):
        self._manager.start()

    def stop(self):
        self._manager.stop()

    def pause(self):
        self._manager.pause()

    def resume(self):
        self._manager.resume()

    @staticmethod
    def list_ports():
        return SerialManager.list_ports()

    def _on_raw_data(self, data: bytes, timestamp: float):
        for packet in self._accumulator.feed(data, timestamp):
            packet.protocol = PROTOCOL_NAME
            self.packetReceived.emit(packet)
