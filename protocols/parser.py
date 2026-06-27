"""Generic packet model and byte-stream framing shared by all serial protocols."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Packet:
    timestamp: float
    protocol: str
    raw: bytes
    direction: str = "RX"

    @property
    def size(self) -> int:
        return len(self.raw)

    def to_ascii(self) -> str:
        return self.raw.decode("ascii", errors="replace")

    def to_hex(self) -> str:
        return " ".join(f"{b:02X}" for b in self.raw)

    def to_dec(self) -> str:
        return " ".join(str(b) for b in self.raw)

    def to_bin(self) -> str:
        return " ".join(f"{b:08b}" for b in self.raw)

    def formatted(self, fmt: str) -> str:
        fmt = fmt.upper()
        if fmt == "ASCII":
            return self.to_ascii()
        if fmt == "HEX":
            return self.to_hex()
        if fmt == "DEC":
            return self.to_dec()
        if fmt == "BIN":
            return self.to_bin()
        raise ValueError(f"Unknown format: {fmt}")

    def timestamp_str(self) -> str:
        ms = int((self.timestamp % 1) * 1000)
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp)) + f".{ms:03d}"


class FrameAccumulator:
    """Splits a raw byte stream into packets using an inter-byte silence window.

    This is the standard approach for sniffing protocols (UART/RS232/RS485/
    Modbus RTU) that have no explicit delimiter: a new frame is assumed to
    have started once the line has been idle for ``idle_timeout`` seconds.
    """

    def __init__(self, idle_timeout: float = 0.05):
        self.idle_timeout = idle_timeout
        self._buffer = bytearray()
        self._last_byte_time: Optional[float] = None

    def feed(self, data: bytes, now: Optional[float] = None) -> Optional[Packet]:
        now = now if now is not None else time.time()
        flushed = None
        if self._buffer and self._last_byte_time is not None and (now - self._last_byte_time) > self.idle_timeout:
            flushed = self._flush(self._last_byte_time)
        self._buffer.extend(data)
        self._last_byte_time = now
        return flushed

    def flush_if_idle(self, now: Optional[float] = None) -> Optional[Packet]:
        now = now if now is not None else time.time()
        if self._buffer and self._last_byte_time is not None and (now - self._last_byte_time) > self.idle_timeout:
            return self._flush(self._last_byte_time)
        return None

    def _flush(self, ts: float) -> Packet:
        raw = bytes(self._buffer)
        self._buffer.clear()
        return Packet(timestamp=ts, protocol="", raw=raw)


class LineAccumulator:
    """Splits an incoming byte stream into packets on a terminator (e.g. SCPI '\\n')."""

    def __init__(self, terminator: bytes = b"\n"):
        self.terminator = terminator
        self._buffer = bytearray()

    def feed(self, data: bytes, now: Optional[float] = None) -> list[Packet]:
        now = now if now is not None else time.time()
        self._buffer.extend(data)
        packets = []
        while self.terminator in self._buffer:
            idx = self._buffer.index(self.terminator)
            raw = bytes(self._buffer[:idx])
            del self._buffer[: idx + len(self.terminator)]
            packets.append(Packet(timestamp=now, protocol="", raw=raw))
        return packets
