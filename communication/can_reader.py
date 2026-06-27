"""CAN bus monitor built on python-can."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import can
from PySide6.QtCore import QThread, Signal

from protocols.can_parser import CanFrame

logger = logging.getLogger(__name__)


@dataclass
class CanSettings:
    interface: str
    channel: str
    bitrate: int
    is_extended: bool = False


class CanReader(QThread):
    frameReceived = Signal(object)
    connected = Signal()
    disconnected = Signal()
    errorOccurred = Signal(str)
    reconnecting = Signal(int)

    def __init__(self, settings: CanSettings, auto_reconnect: bool = True, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.auto_reconnect = auto_reconnect
        self._bus: can.BusABC | None = None
        self._running = False
        self._paused = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        self.wait(2000)

    def run(self):
        self._running = True
        while self._running:
            if not self._open_bus():
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

    def _open_bus(self) -> bool:
        try:
            self._bus = can.interface.Bus(
                channel=self.settings.channel,
                interface=self.settings.interface,
                bitrate=self.settings.bitrate,
            )
            return True
        except can.CanError as exc:
            self.errorOccurred.emit(str(exc))
            logger.warning("Failed to open CAN bus %s: %s", self.settings.channel, exc)
            return False

    def _read_loop(self):
        while self._running:
            if self._paused:
                time.sleep(0.05)
                continue
            try:
                msg = self._bus.recv(timeout=0.2)
            except can.CanError as exc:
                self.errorOccurred.emit(str(exc))
                logger.warning("CAN read error: %s", exc)
                break
            if msg is not None:
                self.frameReceived.emit(CanFrame.from_python_can(msg))
        self._close_bus()

    def _close_bus(self):
        if self._bus is not None:
            try:
                self._bus.shutdown()
            except Exception as exc:
                logger.debug("Error shutting down CAN bus: %s", exc)
        self._bus = None
