"""Modbus RTU monitor.

Operates in passive sniffing mode (no master polling, RX-only as required
for this version): frames are detected purely from inter-byte silence on
the bus (the protocol's 3.5 character silent period) and validated against
the trailing CRC16. MinimalModbus (listed in requirements.txt) targets
active master/slave polling and is reserved for the future TX expansion.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

from communication.serial_manager import SerialManager, SerialSettings
from protocols.crc import check_modbus_crc
from protocols.parser import FrameAccumulator, Packet

PROTOCOL_NAME = "Modbus RTU"


@dataclass
class ModbusPacket(Packet):
    slave_address: int = 0
    function_code: int = 0
    crc_ok: bool = False


class ModbusReader(QObject):
    packetReceived = Signal(object)
    connected = Signal()
    disconnected = Signal()
    errorOccurred = Signal(str)
    reconnecting = Signal(int)

    def __init__(self, settings: SerialSettings, idle_timeout: float = 0.01, auto_reconnect: bool = True, parent=None):
        super().__init__(parent)
        self._manager = SerialManager(settings, auto_reconnect=auto_reconnect)
        self._accumulator = FrameAccumulator(idle_timeout=idle_timeout)
        self._manager.rawDataReceived.connect(self._on_raw_data)
        self._manager.connected.connect(self.connected)
        self._manager.disconnected.connect(self.disconnected)
        self._manager.errorOccurred.connect(self.errorOccurred)
        self._manager.reconnecting.connect(self.reconnecting)

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(10)
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
            self._emit_modbus_packet(packet)

    def _check_idle_flush(self):
        packet = self._accumulator.flush_if_idle()
        if packet:
            self._emit_modbus_packet(packet)

    def _emit_modbus_packet(self, packet: Packet):
        raw = packet.raw
        slave = raw[0] if len(raw) >= 1 else 0
        function_code = raw[1] if len(raw) >= 2 else 0
        modbus_packet = ModbusPacket(
            timestamp=packet.timestamp,
            protocol=PROTOCOL_NAME,
            raw=raw,
            slave_address=slave,
            function_code=function_code,
            crc_ok=check_modbus_crc(raw),
        )
        self.packetReceived.emit(modbus_packet)
