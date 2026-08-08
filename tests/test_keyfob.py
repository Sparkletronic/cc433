import unittest

from cc433.bitbuffer import BitBuffer
from cc433.devices.keyfob import keyfob_decode, make_keyfob_device, DECODE_ABORT_LENGTH


# Define the TestKeyfobDecode class, which groups related state and behavior for this stage.
class TestKeyfobDecode(unittest.TestCase):
    # Define _buffer_from_rtl_code(), a named step in the decoding/support pipeline.
    def _buffer_from_rtl_code(self, hex_code, bits=25):
        # rtl_433 displays a 25-bit row as 7 hex nibbles, e.g. {25}59d7f78.
        # Add bits from the displayed stream, then stop at the declared width.
        bit_stream = "".join(bin(int(ch, 16))[2:].zfill(4) for ch in hex_code)
        bb = BitBuffer()
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for bit in bit_stream[:bits]:
            bb.add_bit(1 if bit == "1" else 0)
        # Return the result to the caller so the next pipeline stage can continue.
        return bb

    # Define test_keyfob_decode__maps_up_stop_down(), a named step in the decoding/support pipeline.
    def test_keyfob_decode__maps_up_stop_down(self):
        cases = [
            ("59d7f78", "up", 0x59D7F, 0x0F, 0x78),
            ("59d7fb8", "stop", 0x59D7F, 0x17, 0xB8),
            ("59d7fd8", "down", 0x59D7F, 0x1B, 0xD8),
        ]

        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for raw_msg, button, remote_id, command, display_command in cases:
            device = make_keyfob_device()
            bb = self._buffer_from_rtl_code(raw_msg)
            self.assertEqual(keyfob_decode(device, bb), 1)
            self.assertEqual(len(device.decoded), 1)
            decoded = device.decoded[0]
            self.assertEqual(decoded["model"], "Keyfob-1202M")
            self.assertEqual(decoded["raw_msg"], raw_msg.upper())
            self.assertEqual(decoded["id"], remote_id)
            self.assertEqual(decoded["command"], command)
            self.assertEqual(decoded["display_command"], display_command)
            self.assertEqual(decoded["button"], button)

    # Define test_keyfob_decode__emits_unknown_command(), a named step in the decoding/support pipeline.
    def test_keyfob_decode__emits_unknown_command(self):
        device = make_keyfob_device()
        bb = self._buffer_from_rtl_code("59d7f18")

        self.assertEqual(keyfob_decode(device, bb), 1)
        self.assertEqual(device.decoded[0]["button"], "unknown")
        self.assertEqual(device.decoded[0]["command"], 0x03)
        self.assertEqual(device.decoded[0]["display_command"], 0x18)

    # Define test_keyfob_decode__rejects_non_25_bit_rows(), a named step in the decoding/support pipeline.
    def test_keyfob_decode__rejects_non_25_bit_rows(self):
        device = make_keyfob_device()
        bb = self._buffer_from_rtl_code("59d7f78", bits=24)

        self.assertEqual(keyfob_decode(device, bb), DECODE_ABORT_LENGTH)
        self.assertFalse(hasattr(device, "decoded"))


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
