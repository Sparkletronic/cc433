import unittest

from cc433.bitbuffer import BitBuffer
from cc433.devices import acurite
from cc433.devices.acurite import (
    ACURITE_6045_BYTELEN,
    DECODE_ABORT_LENGTH,
    DECODE_FAIL_MIC,
    DECODE_FAIL_SANITY,
    acurite_6045_decode_bytes,
    acurite_get_channel,
    acurite_txr_check,
    acurite_txr_decode,
    add_bytes,
    make_acurite_6045m_device,
    parity8,
    parity_bytes,
)
from tests._helpers import add_bytes as add_bytes_to_bitbuffer

RAW_6045M = bytes.fromhex("c048af12116aebc0ef")


# Define the TestAcurite class, which groups related state and behavior for this stage.
class TestAcurite(unittest.TestCase):
    # Define test_acurite_get_channel__maps_two_high_bits(), a named step in the decoding/support pipeline.
    def test_acurite_get_channel__maps_two_high_bits(self):
        self.assertEqual(acurite_get_channel(0x00), "C")
        self.assertEqual(acurite_get_channel(0x40), "E")
        self.assertEqual(acurite_get_channel(0x80), "B")
        self.assertEqual(acurite_get_channel(0xC0), "A")

    # Define test_add_bytes__sums_requested_prefix(), a named step in the decoding/support pipeline.
    def test_add_bytes__sums_requested_prefix(self):
        self.assertEqual(add_bytes([1, 2, 3], 2), 3)

    # Define test_parity8__returns_odd_parity_bit(), a named step in the decoding/support pipeline.
    def test_parity8__returns_odd_parity_bit(self):
        self.assertEqual(parity8(0x00), 0)
        self.assertEqual(parity8(0x01), 1)
        self.assertEqual(parity8(0x03), 0)

    # Define test_parity_bytes__xors_byte_parities(), a named step in the decoding/support pipeline.
    def test_parity_bytes__xors_byte_parities(self):
        self.assertEqual(parity_bytes(bytes([0x01, 0x02]), 2), 0)
        self.assertEqual(parity_bytes(bytes([0x01, 0x03]), 2), 1)

    # Define test_acurite_txr_check__accepts_known_6045m_row(), a named step in the decoding/support pipeline.
    def test_acurite_txr_check__accepts_known_6045m_row(self):
        self.assertEqual(acurite_txr_check(RAW_6045M, len(RAW_6045M)), 0)

    # Define test_acurite_txr_check__rejects_short_row(), a named step in the decoding/support pipeline.
    def test_acurite_txr_check__rejects_short_row(self):
        self.assertEqual(acurite_txr_check(RAW_6045M[:5], 5), DECODE_ABORT_LENGTH)

    # Define test_acurite_txr_check__rejects_bad_checksum(), a named step in the decoding/support pipeline.
    def test_acurite_txr_check__rejects_bad_checksum(self):
        bad = bytearray(RAW_6045M)
        bad[-1] ^= 1
        self.assertEqual(acurite_txr_check(bad, len(bad)), DECODE_FAIL_MIC)

    # Define test_acurite_txr_check__rejects_invalid_channel_e(), a named step in the decoding/support pipeline.
    def test_acurite_txr_check__rejects_invalid_channel_e(self):
        bad = bytearray(RAW_6045M)
        bad[0] = (bad[0] & 0x3F) | 0x40
        bad[-1] = sum(bad[:-1]) & 0xFF
        self.assertEqual(acurite_txr_check(bad, len(bad)), DECODE_FAIL_SANITY)

    # Define test_acurite_6045_decode_bytes__decodes_known_6045m_fields(), a named step in the decoding/support pipeline.
    def test_acurite_6045_decode_bytes__decodes_known_6045m_fields(self):
        ret, data = acurite_6045_decode_bytes(RAW_6045M)
        self.assertEqual(ret, 1)
        self.assertEqual(data["id"], 72)
        self.assertEqual(data["channel"], "A")
        self.assertAlmostEqual(data["temperature_F"], 80.2)
        self.assertEqual(data["humidity"], 18)
        self.assertEqual(data["strike_count"], 215)
        self.assertEqual(data["storm_dist"], 0)
        self.assertEqual(data["raw_msg"], "C048AF12116AEBC0EF")

    # Define test_acurite_6045_decode_bytes__rejects_humidity_over_100(), a named step in the decoding/support pipeline.
    def test_acurite_6045_decode_bytes__rejects_humidity_over_100(self):
        bad = bytearray(RAW_6045M)
        bad[3] = 101
        ret, data = acurite_6045_decode_bytes(bad)
        self.assertEqual(ret, DECODE_FAIL_SANITY)
        self.assertIsNone(data)

    # Define test_acurite_txr_decode__decodes_known_raw_row_without_invert(), a named step in the decoding/support pipeline.
    def test_acurite_txr_decode__decodes_known_raw_row_without_invert(self):
        bb = add_bytes_to_bitbuffer(BitBuffer(), RAW_6045M)
        device = make_acurite_6045m_device(invert_before_decode=False)
        self.assertEqual(acurite_txr_decode(device, bb), 1)
        self.assertEqual(device.decoded[0]["raw_msg"], "C048AF12116AEBC0EF")

    # Define test_acurite_txr_decode__decodes_complemented_row_with_invert(), a named step in the decoding/support pipeline.
    def test_acurite_txr_decode__decodes_complemented_row_with_invert(self):
        pre_invert = bytes((~b) & 0xFF for b in RAW_6045M)
        bb = add_bytes_to_bitbuffer(BitBuffer(), pre_invert)
        device = make_acurite_6045m_device(invert_before_decode=True)
        self.assertEqual(acurite_txr_decode(device, bb), 1)
        self.assertEqual(device.decoded[0]["raw_msg"], "C048AF12116AEBC0EF")

    # Define test_acurite_txr_decode__rejects_unknown_message_type(), a named step in the decoding/support pipeline.
    def test_acurite_txr_decode__rejects_unknown_message_type(self):
        bad = bytearray(RAW_6045M)
        bad[2] = (bad[2] & 0xC0) | 0x01
        bad[-1] = sum(bad[:-1]) & 0xFF
        bb = add_bytes_to_bitbuffer(BitBuffer(), bad)
        device = make_acurite_6045m_device(invert_before_decode=False)
        self.assertEqual(acurite_txr_decode(device, bb), DECODE_FAIL_SANITY)

    # Define test_make_acurite_6045m_device__uses_cc433_pwm_parameters(), a named step in the decoding/support pipeline.
    def test_make_acurite_6045m_device__uses_cc433_pwm_parameters(self):
        device = make_acurite_6045m_device()
        self.assertEqual(device.short_width_us, 220)
        self.assertEqual(device.long_width_us, 408)
        self.assertEqual(device.sync_width_us, 620)
        self.assertEqual(device.gap_limit_us, 500)
        self.assertEqual(device.reset_limit_us, 4000)
        self.assertIs(device.decode_fn, acurite_txr_decode)


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
