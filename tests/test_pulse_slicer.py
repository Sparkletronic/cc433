import unittest

from cc433.pulse_data import PulseData
from cc433.pulse_slicer import Device, OOK_PULSE_PPM, _account_event, pulse_slicer_pwm, pulse_slicer_ppm


# Define the TestDevice class, which groups related state and behavior for this stage.
class TestDevice(unittest.TestCase):
    # Define test___init____stores_decoder_configuration(), a named step in the decoding/support pipeline.
    def test___init____stores_decoder_configuration(self):
        device = Device("name", 220, 408, sync_width_us=620, gap_limit_us=500, reset_limit_us=4000, tolerance_us=0)
        self.assertEqual(device.name, "name")
        self.assertEqual(device.short_width_us, 220)
        self.assertEqual(device.long_width_us, 408)
        self.assertEqual(device.sync_width_us, 620)
        self.assertEqual(device.gap_limit_us, 500)
        self.assertEqual(device.reset_limit_us, 4000)


# Define the TestPulseSlicerPwm class, which groups related state and behavior for this stage.
class TestPulseSlicerPwm(unittest.TestCase):
    # Define test__account_event__calls_decode_fn_and_counts_success(), a named step in the decoding/support pipeline.
    def test__account_event__calls_decode_fn_and_counts_success(self):
        # Define decode_fn(), a named step in the decoding/support pipeline.
        def decode_fn(device, bits):
            device.seen_bits = bits.bits_per_row[:bits.num_rows]
            # Return the result to the caller so the next pipeline stage can continue.
            return 1

        device = Device("d", 220, 408, decode_fn=decode_fn)
        from cc433.bitbuffer import BitBuffer
        bits = BitBuffer(); bits.add_bit(1)
        self.assertEqual(_account_event(device, bits), 1)
        self.assertEqual(device.decode_events, 1)
        self.assertEqual(device.decode_ok, 1)
        self.assertEqual(device.decode_messages, 1)

    # Define test_pulse_slicer_pwm__sample_rate_too_low_returns_zero(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_pwm__sample_rate_too_low_returns_zero(self):
        pd = PulseData(sample_rate=1)
        pd.append(220, 4000)
        device = Device("d", 220, 408, sync_width_us=620, gap_limit_us=500, reset_limit_us=4000)
        self.assertEqual(pulse_slicer_pwm(pd, device), 0)

    # Define test_pulse_slicer_pwm__classifies_short_as_one_long_as_zero_and_sync(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_pwm__classifies_short_as_one_long_as_zero_and_sync(self):
        captured = []

        # Define decode_fn(), a named step in the decoding/support pipeline.
        def decode_fn(_device, bits):
            captured.append((bits.bits_per_row[:bits.num_rows], bits.hex_rows()))
            # Return the result to the caller so the next pipeline stage can continue.
            return 1

        pd = PulseData(sample_rate=1000000)
        pd.append(620, 620)     # sync: empty row with sync count
        pd.append(220, 408)     # one
        pd.append(408, 220)     # zero
        pd.append(220, 5000)    # one and reset event
        device = Device("d", 220, 408, sync_width_us=620, gap_limit_us=500, reset_limit_us=4000, decode_fn=decode_fn)

        self.assertEqual(pulse_slicer_pwm(pd, device), 1)
        self.assertEqual(captured[0][0], [3])
        self.assertEqual(captured[0][1], ["A0"])

    # Define test_pulse_slicer_pwm__gap_limit_us_adds_row(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_pwm__gap_limit_us_adds_row(self):
        captured = []

        # Define decode_fn(), a named step in the decoding/support pipeline.
        def decode_fn(_device, bits):
            captured.append(bits.bits_per_row[:bits.num_rows])
            # Return the result to the caller so the next pipeline stage can continue.
            return 1

        pd = PulseData()
        pd.append(220, 600)
        pd.append(408, 5000)
        device = Device("d", 220, 408, sync_width_us=620, gap_limit_us=500, reset_limit_us=4000, decode_fn=decode_fn)
        pulse_slicer_pwm(pd, device)
        self.assertEqual(captured[0], [1, 1])


# Define the TestPulseSlicerPpm class, which groups related state and behavior for this stage.
class TestPulseSlicerPpm(unittest.TestCase):
    # Define _make_ppm_pulses(), a named step in the decoding/support pipeline.
    def _make_ppm_pulses(self, bit_string, include_infactory_preamble=False, trailing_reset=16000):
        pd = PulseData(sample_rate=1000000)

        # Check this condition so only the matching signal/data case is handled here.
        if include_infactory_preamble:
            # inFactory observed preamble: roughly 1000/1000 repeated,
            # followed by a 500/8000 sync-prefix reset before data.
            # Iterate through each item so the pipeline can process one measured/test value at a time.
            for _ in range(4):
                pd.append(1000, 1000)
            pd.append(500, 8000)

        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for bit in bit_string:
            pd.append(500, 4000 if bit == "1" else 2000)

        # Check this condition so only the matching signal/data case is handled here.
        if trailing_reset is not None:
            pd.append(500, trailing_reset)

        # Return the result to the caller so the next pipeline stage can continue.
        return pd

    # Define _capture_40_bit_rows_device(), a named step in the decoding/support pipeline.
    def _capture_40_bit_rows_device(self):
        captured = []

        # Define decode_fn(), a named step in the decoding/support pipeline.
        def decode_fn(_device, bits):
            rows = bits.bits_per_row[:bits.num_rows]
            hex_rows = bits.hex_rows()
            captured.append((rows, hex_rows))
            # Return the result to the caller so the next pipeline stage can continue.
            return 1 if 40 in rows else 0

        device = Device(
            "inFactory ppm test",
            short_width_us=2000,
            long_width_us=4000,
            sync_width_us=500,
            gap_limit_us=0,
            reset_limit_us=5000,
            tolerance_us=750,
            decode_fn=decode_fn,
            modulation=OOK_PULSE_PPM,
            enable_lead_in=False,
        )
        # Return the result to the caller so the next pipeline stage can continue.
        return device, captured

    # Define test_pulse_slicer_ppm__classifies_clean_infactory_40_bit_row(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_ppm__classifies_clean_infactory_40_bit_row(self):
        bits = "1010" * 10
        device, captured = self._capture_40_bit_rows_device()
        pd = self._make_ppm_pulses(bits)

        self.assertEqual(pulse_slicer_ppm(pd, device), 1)
        self.assertEqual(captured[-1][0], [40])
        self.assertEqual(captured[-1][1], ["AAAAAAAAAA"])

    # Define test_pulse_slicer_ppm__ignores_preamble_and_still_emits_40_bit_data_row(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_ppm__ignores_preamble_and_still_emits_40_bit_data_row(self):
        bits = "11001010" * 5
        device, captured = self._capture_40_bit_rows_device()
        pd = self._make_ppm_pulses(bits, include_infactory_preamble=True)

        self.assertEqual(pulse_slicer_ppm(pd, device), 1)
        self.assertIn(([40], ["CACACACACA"]), captured)

    # Define test_pulse_slicer_ppm__emits_41_bit_row_when_extra_distortion_gap_is_bit_like(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_ppm__emits_41_bit_row_when_extra_distortion_gap_is_bit_like(self):
        bits = ("1010" * 10) + "1"
        device, captured = self._capture_40_bit_rows_device()
        pd = self._make_ppm_pulses(bits)

        self.assertEqual(pulse_slicer_ppm(pd, device), 0)
        self.assertEqual(captured[-1][0], [41])
        self.assertEqual(captured[-1][1], ["AAAAAAAAAA80"])


# Define the TestPulseSlicerPpmInfactoryCc433Fixture class, which groups related state and behavior for this stage.
class TestPulseSlicerPpmInfactoryCc433Fixture(unittest.TestCase):
    # Define _fixture_pulse_data(), a named step in the decoding/support pipeline.
    def _fixture_pulse_data(self):
        from tests.fixtures.infactory_cc433_success import SAMPLE_RATE, PULSE_GAP_ROWS

        pd = PulseData(sample_rate=SAMPLE_RATE)
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for pulse, gap in PULSE_GAP_ROWS:
            pd.append(pulse, gap)
        # Return the result to the caller so the next pipeline stage can continue.
        return pd

    # Define test_pulse_slicer_ppm__cc433_success_fixture_emits_40_bit_row(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_ppm__cc433_success_fixture_emits_40_bit_row(self):
        from tests.fixtures.infactory_cc433_success import EXPECTED_HEX_ROWS, EXPECTED_ROWS

        captured = []

        # Define decode_fn(), a named step in the decoding/support pipeline.
        def decode_fn(_device, bits):
            captured.append((bits.bits_per_row[:bits.num_rows], bits.hex_rows()))
            # Return the result to the caller so the next pipeline stage can continue.
            return 1

        device = Device(
            "inFactory ppm cc433 fixture",
            short_width_us=2000,
            long_width_us=4000,
            sync_width_us=500,
            gap_limit_us=0,
            reset_limit_us=5000,
            tolerance_us=750,
            decode_fn=decode_fn,
            modulation=OOK_PULSE_PPM,
        )

        self.assertEqual(pulse_slicer_ppm(self._fixture_pulse_data(), device), 1)
        self.assertEqual(captured[-1][0], EXPECTED_ROWS)
        self.assertEqual(captured[-1][1], EXPECTED_HEX_ROWS)

    # Define test_pulse_slicer_ppm__cc433_success_fixture_decodes_infactory(), a named step in the decoding/support pipeline.
    def test_pulse_slicer_ppm__cc433_success_fixture_decodes_infactory(self):
        from cc433.devices.infactory import make_infactory_device
        from tests.fixtures.infactory_cc433_success import EXPECTED_DECODE

        device = make_infactory_device()

        self.assertEqual(pulse_slicer_ppm(self._fixture_pulse_data(), device), 1)
        self.assertEqual(device.decoded[-1], EXPECTED_DECODE)


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
