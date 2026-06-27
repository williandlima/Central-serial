"""UART monitor: generic byte-stream protocol framed by inter-byte silence.

RS232 and RS485 readers reuse this same framing strategy since, electrically,
they only differ in physical layer — subclasses simply override
``PROTOCOL_NAME`` (and may tune ``idle_timeout`` for bus-specific timing).
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from communication.serial_manager import SerialManager, SerialSettings
from protocols.parser import FrameAccumulator


class UartReader(QObject):
    PROTOCOL_NAME = "UART"

    packetReceived = Signal(object)
    connected = Signal()
    disconnected = Signal()
    errorOccurred = Signal(str)
    reconnecting = Signal(int)

    def __init__(self, settings: SerialSettings, idle_timeout: float = 0.05, auto_reconnect: bool = True, parent=None):
        super().__init__(parent)
        self._manager = SerialManager(settings, auto_reconnect=auto_reconnect)
        self._accumulator = FrameAccumulator(idle_timeout=idle_timeout)
        self._manager.rawDataReceived.connect(self._on_raw_data)
        self._manager.connected.connect(self.connected)
        self._manager.disconnected.connect(self.disconnected)
        self._manager.errorOccurred.connect(self.errorOccurred)
        self._manager.reconnecting.connect(self.reconnecting)

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(20)
        self._flush_timer.timeout.connect(self._check_idle_flush)
        self._flush_timer.start()

    def start(self):
        self._manager.start()

    def stop(self):
        self._flush_timer.stop()
        self._manager.stop()

    def pause(self):
        self._manager.pause()

    def resume(self):
        self._manager.resume()

    @staticmethod
    def list_ports():
        return SerialManager.list_ports()

    def _on_raw_data(self, data: bytes, timestamp: float):
        packet = self._accumulator.feed(data, timestamp)
        if packet:
            packet.protocol = self.PROTOCOL_NAME
            self.packetReceived.emit(packet)

    def _check_idle_flush(self):
        packet = self._accumulator.flush_if_idle()
        if packet:
            packet.protocol = self.PROTOCOL_NAME
            self.packetReceived.emit(packet)
