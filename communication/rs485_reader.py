"""RS485 monitor — multidrop bus, same byte-level framing as UART/RS232."""
from __future__ import annotations

from communication.uart_reader import UartReader


class Rs485Reader(UartReader):
    PROTOCOL_NAME = "RS485"
