"""CAN frame model and formatting utilities."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class CanFrame:
    timestamp: float
    can_id: int
    is_extended: bool
    is_remote: bool
    is_error: bool
    dlc: int
    data: bytes

    @property
    def frame_type(self) -> str:
        if self.is_error:
            return "ERROR"
        if self.is_remote:
            return "REMOTE"
        return "DATA"

    @property
    def id_str(self) -> str:
        width = 8 if self.is_extended else 3
        return f"0x{self.can_id:0{width}X}"

    @property
    def data_hex(self) -> str:
        return " ".join(f"{b:02X}" for b in self.data)

    def timestamp_str(self) -> str:
        ms = int((self.timestamp % 1) * 1000)
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp)) + f".{ms:03d}"

    def format_line(self) -> str:
        return (
            f"TIME: {self.timestamp_str()}  CAN ID: {self.id_str}  "
            f"FRAME: {self.frame_type}  DLC: {self.dlc}  DATA: {self.data_hex}"
        )

    @classmethod
    def from_python_can(cls, msg) -> "CanFrame":
        return cls(
            timestamp=msg.timestamp or time.time(),
            can_id=msg.arbitration_id,
            is_extended=msg.is_extended_id,
            is_remote=msg.is_remote_frame,
            is_error=msg.is_error_frame,
            dlc=msg.dlc,
            data=bytes(msg.data),
        )
