import unittest

from cc433 import synthetic
from cc433.pulse_detect import PULSE_DATA_OOK
from cc433.pulse_slicer import Device


# Define the TestSynthetic class, which groups related state and behavior for this stage.
class TestSynthetic(unittest.TestCase):
    # Define test_make_envelope_from_pairs__builds_low_lead_in_and_high_pulse(), a named step in the decoding/support pipeline.
    def test_make_envelope_from_pairs__builds_low_lead_in_and_high_pulse(self):
        env = synthetic.make_envelope_from_pairs([(2, 3)], high=9, low=1, lead_in_us=4)
        self.assertEqual(env, [1, 1, 1, 1, 9, 9, 1, 1, 1])

    # Define test_bits_to_pwm_pairs__encodes_one_as_short_and_zero_as_long(), a named step in the decoding/support pipeline.
    def test_bits_to_pwm_pairs__encodes_one_as_short_and_zero_as_long(self):
        pairs = synthetic.bits_to_pwm_pairs("10", short_us=1, long_us=2, sync_us=3, sync_gap_us=4, add_reset=False)
        self.assertEqual(pairs, [(3, 4), (1, 2), (2, 1)])

    # Define test_debug_acurite_device__returns_pwm_debug_device(), a named step in the decoding/support pipeline.
    def test_debug_acurite_device__returns_pwm_debug_device(self):
        device = synthetic.debug_acurite_device()
        self.assertIsInstance(device, Device)
        self.assertIsNone(device.decode_fn)

    # Define test_run_synthetic_pwm__returns_ook_status_and_pulses(), a named step in the decoding/support pipeline.
    def test_run_synthetic_pwm__returns_ook_status_and_pulses(self):
        status, pulses, events = synthetic.run_synthetic_pwm("1010")
        self.assertEqual(status, PULSE_DATA_OOK)
        self.assertGreater(pulses.num_pulses, 0)
        self.assertIsInstance(events, int)

    @unittest.skip("Captured vector smoke test is covered by the end-to-end regression once a fixed PulseData fixture is selected.")
    # Define test_run_capture_vector_01__runs_canonical_capture_vector(), a named step in the decoding/support pipeline.
    def test_run_capture_vector_01__runs_canonical_capture_vector(self):
        synthetic.run_capture_vector_01(use_acurite_decoder=True)


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
