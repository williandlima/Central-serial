import unittest

from protocols.can_parser import CanFrame
from protocols.crc import check_modbus_crc, crc16_modbus_bytes, crc8
from protocols.parser import FrameAccumulator, LineAccumulator, Packet


class PacketFormattingTests(unittest.TestCase):
    def setUp(self):
        self.packet = Packet(timestamp=1700000000.123, protocol="UART", raw=b"\x41\x42\x0a")

    def test_to_ascii(self):
        self.assertEqual(self.packet.to_ascii(), "AB\n")

    def test_to_hex(self):
        self.assertEqual(self.packet.to_hex(), "41 42 0A")

    def test_to_dec(self):
        self.assertEqual(self.packet.to_dec(), "65 66 10")

    def test_to_bin(self):
        self.assertEqual(self.packet.to_bin(), "01000001 01000010 00001010")

    def test_formatted_dispatch(self):
        self.assertEqual(self.packet.formatted("hex"), self.packet.to_hex())

    def test_formatted_invalid(self):
        with self.assertRaises(ValueError):
            self.packet.formatted("XYZ")

    def test_size(self):
        self.assertEqual(self.packet.size, 3)


class FrameAccumulatorTests(unittest.TestCase):
    def test_flushes_after_idle_gap(self):
        acc = FrameAccumulator(idle_timeout=0.05)
        self.assertIsNone(acc.feed(b"\x01\x02", now=0.0))
        # Still within idle window: no flush yet, bytes get appended.
        self.assertIsNone(acc.feed(b"\x03", now=0.01))
        # Gap larger than idle_timeout: previous buffer flushes first.
        packet = acc.feed(b"\x04", now=0.10)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.raw, b"\x01\x02\x03")

    def test_flush_if_idle(self):
        acc = FrameAccumulator(idle_timeout=0.05)
        acc.feed(b"\xaa\xbb", now=0.0)
        self.assertIsNone(acc.flush_if_idle(now=0.02))
        packet = acc.flush_if_idle(now=0.10)
        self.assertEqual(packet.raw, b"\xaa\xbb")
        self.assertIsNone(acc.flush_if_idle(now=0.20))


class LineAccumulatorTests(unittest.TestCase):
    def test_splits_on_terminator(self):
        acc = LineAccumulator(terminator=b"\n")
        packets = acc.feed(b"*IDN?\nMEAS:VOLT 1.2\n")
        self.assertEqual([p.raw for p in packets], [b"*IDN?", b"MEAS:VOLT 1.2"])

    def test_buffers_partial_line(self):
        acc = LineAccumulator(terminator=b"\n")
        self.assertEqual(acc.feed(b"PART"), [])
        packets = acc.feed(b"IAL\n")
        self.assertEqual(packets[0].raw, b"PARTIAL")


class CrcTests(unittest.TestCase):
    def test_crc16_modbus_known_vector(self):
        # 01 03 00 00 00 0A -> CRC 0xC5CD, a widely used textbook Modbus RTU
        # request example.
        frame = bytes.fromhex("01030000000A")
        crc = crc16_modbus_bytes(frame)
        self.assertEqual(crc, b"\xc5\xcd")

    def test_check_modbus_crc_valid(self):
        payload = bytes.fromhex("01030000000A")
        full_frame = payload + crc16_modbus_bytes(payload)
        self.assertTrue(check_modbus_crc(full_frame))

    def test_check_modbus_crc_invalid(self):
        self.assertFalse(check_modbus_crc(b"\x01\x03\x00\x00\x00\x0a\x00\x00"))

    def test_check_modbus_crc_too_short(self):
        self.assertFalse(check_modbus_crc(b"\x01"))

    def test_crc8_deterministic(self):
        self.assertEqual(crc8(b"\x01\x02\x03"), crc8(b"\x01\x02\x03"))
        self.assertNotEqual(crc8(b"\x01\x02\x03"), crc8(b"\x01\x02\x04"))


class CanFrameTests(unittest.TestCase):
    def test_standard_frame_formatting(self):
        frame = CanFrame(
            timestamp=1700000000.0,
            can_id=0x123,
            is_extended=False,
            is_remote=False,
            is_error=False,
            dlc=2,
            data=b"\xaa\xbb",
        )
        self.assertEqual(frame.id_str, "0x123")
        self.assertEqual(frame.frame_type, "DATA")
        self.assertEqual(frame.data_hex, "AA BB")

    def test_extended_frame_id_width(self):
        frame = CanFrame(
            timestamp=1700000000.0,
            can_id=0x18FF50E5,
            is_extended=True,
            is_remote=False,
            is_error=False,
            dlc=8,
            data=bytes.fromhex("1122334455667788"),
        )
        self.assertEqual(frame.id_str, "0x18FF50E5")
        self.assertIn("CAN ID: 0x18FF50E5", frame.format_line())
        self.assertIn("DLC: 8", frame.format_line())

    def test_remote_and_error_frame_type(self):
        remote = CanFrame(1700000000.0, 0x1, False, True, False, 0, b"")
        error = CanFrame(1700000000.0, 0x1, False, False, True, 0, b"")
        self.assertEqual(remote.frame_type, "REMOTE")
        self.assertEqual(error.frame_type, "ERROR")


if __name__ == "__main__":
    unittest.main()
