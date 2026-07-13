"""RS232 monitor — same framing as UART, kept as its own module per the
project's protocol-per-file architecture (allows future RS232-specific
handling without touching the other readers)."""
from __future__ import annotations

from communication.uart_reader import UartReader


class Rs232Reader(UartReader):
    PROTOCOL_NAME = "RS232"
