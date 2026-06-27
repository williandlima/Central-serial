"""Low level serial port worker running on its own QThread.

Handles connecting, disconnecting, pausing and the raw non-blocking read
loop, including automatic reconnection. Protocol-specific behaviour
(framing, parsing) lives in the ``*_reader`` modules built on top of this.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


@dataclass
class SerialSettings:
    port: str
    baudrate: int = 9600
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: float = serial.STOPBITS_ONE
    xonxoff: bool = False
    rtscts: bool = False


class SerialManager(QThread):
    rawDataReceived = Signal(bytes, float)
    connected = Signal()
    disconnected = Signal()
    errorOccurred = Signal(str)
    reconnecting = Signal(int)

    def __init__(self, settings: SerialSettings, auto_reconnect: bool = True, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.auto_reconnect = auto_reconnect
        self._serial: serial.Serial | None = None
        self._running = False
        self._paused = False

    @staticmethod
    def list_ports() -> list[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def stop(self):
        self._running = False
        self.wait(2000)

    def run(self):
        self._running = True
        while self._running:
            if not self._open_port():
                if not self.auto_reconnect:
                    break
                if not self._wait_before_retry():
                    return
                continue
            self.connected.emit()
            self._read_loop()
            self.disconnected.emit()
            if not self._running or not self.auto_reconnect:
                break

    def _wait_before_retry(self) -> bool:
        for remaining in range(3, 0, -1):
            if not self._running:
                return False
            self.reconnecting.emit(remaining)
            time.sleep(1)
        return True

    def _open_port(self) -> bool:
        try:
            self._serial = serial.Serial(
                port=self.settings.port,
                baudrate=self.settings.baudrate,
                bytesize=self.settings.bytesize,
                parity=self.settings.parity,
                stopbits=self.settings.stopbits,
                xonxoff=self.settings.xonxoff,
                rtscts=self.settings.rtscts,
                timeout=0.1,
            )
            return True
        except serial.SerialException as exc:
            self.errorOccurred.emit(str(exc))
            logger.warning("Failed to open port %s: %s", self.settings.port, exc)
            return False

    def _read_loop(self):
        while self._running:
            if self._serial is None:
                break
            try:
                if self._paused:
                    time.sleep(0.05)
                    continue
                waiting = self._serial.in_waiting
                data = self._serial.read(waiting if waiting else 1)
                if data:
                    self.rawDataReceived.emit(data, time.time())
            except serial.SerialException as exc:
                self.errorOccurred.emit(str(exc))
                logger.warning("Serial read error: %s", exc)
                break
        self._close_port()

    def _close_port(self):
        if self._serial is not None and self._serial.is_open:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
        self._serial = None
