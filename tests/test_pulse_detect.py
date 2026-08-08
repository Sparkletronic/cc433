import unittest

from cc433.pulse_detect import (
    PULSE_DATA_OOK,
    PulseDetect,
    PulseDetectEdges,
    PD_EDGE_MAX_TRACKED_PULSE_SAMPLES,
    c_div,
    pulse_detect_create,
    pulse_detect_package,
    pulse_detect_reset,
    pulse_detect_set_levels,
    widths_to_pulse_data,
)
from cc433.synthetic import bits_to_pwm_pairs, make_envelope_from_pairs


# Define the TestPulseDetectCompatibilityFunctions class, which groups related state and behavior for this stage.
class TestPulseDetectCompatibilityFunctions(unittest.TestCase):
    # Define test_c_div__truncates_toward_zero_like_c99(), a named step in the decoding/support pipeline.
    def test_c_div__truncates_toward_zero_like_c99(self):
        self.assertEqual(c_div(7, 3), 2)
        self.assertEqual(c_div(-7, 3), -2)

    # Define test_pulse_detect_create__returns_pulse_detect(), a named step in the decoding/support pipeline.
    def test_pulse_detect_create__returns_pulse_detect(self):
        self.assertIsInstance(pulse_detect_create(), PulseDetect)

    # Define test_pulse_detect_reset__resets_detector_state(), a named step in the decoding/support pipeline.
    def test_pulse_detect_reset__resets_detector_state(self):
        det = PulseDetect()
        det.ook_state = 99
        pulse_detect_reset(det)
        self.assertEqual(det.ook_state, 0)

    # Define test_pulse_detect_set_levels__updates_level_configuration(), a named step in the decoding/support pipeline.
    def test_pulse_detect_set_levels__updates_level_configuration(self):
        det = PulseDetect()
        pulse_detect_set_levels(det, fixed_high_level=-1.0, verbosity=2)
        self.assertEqual(det.verbosity, 2)
        self.assertNotEqual(det.ook_fixed_high_level, 0)

    # Define test_pulse_detect_package__honors_length_argument(), a named step in the decoding/support pipeline.
    def test_pulse_detect_package__honors_length_argument(self):
        det = PulseDetect()
        status, pulses = pulse_detect_package(det, [0] * 20, length=10)
        self.assertEqual(status, 0)
        self.assertEqual(pulses.start_ago, 10)


# Define the TestPulseDetect class, which groups related state and behavior for this stage.
class TestPulseDetect(unittest.TestCase):
    # Define test___init____sets_levels_and_resets_state(), a named step in the decoding/support pipeline.
    def test___init____sets_levels_and_resets_state(self):
        det = PulseDetect(verbosity=1)
        self.assertEqual(det.verbosity, 1)
        self.assertEqual(det.ook_state, 0)

    # Define test_set_levels__can_use_magnitude_estimates(), a named step in the decoding/support pipeline.
    def test_set_levels__can_use_magnitude_estimates(self):
        det = PulseDetect()
        det.set_levels(use_mag_est=True, fixed_high_level=-1.0)
        self.assertEqual(det.use_mag_est, 1)
        self.assertNotEqual(det.ook_fixed_high_level, 0)

    # Define test_reset__clears_counters_and_estimates(), a named step in the decoding/support pipeline.
    def test_reset__clears_counters_and_estimates(self):
        det = PulseDetect()
        det.data_counter = 12
        det.ook_high_estimate = 99
        det.reset()
        self.assertEqual(det.data_counter, 0)
        self.assertEqual(det.ook_high_estimate, 0)

    # Define test_package__detects_synthetic_ook_pulses(), a named step in the decoding/support pipeline.
    def test_package__detects_synthetic_ook_pulses(self):
        pairs = bits_to_pwm_pairs("1010")
        env = make_envelope_from_pairs(pairs)
        det = PulseDetect()
        status, pulses = det.package(env, sample_rate=1000000)
        self.assertEqual(status, PULSE_DATA_OOK)
        self.assertGreater(pulses.num_pulses, 0)


# Define the TestPulseDetectEdges class, which groups related state and behavior for this stage.
class TestPulseDetectEdges(unittest.TestCase):
    # Define _no_lead_in_device(), a named step in the decoding/support pipeline.
    def _no_lead_in_device(self):
        # Define the DummyDevice class, which groups related state and behavior for this stage.
        class DummyDevice:
            enable_lead_in = False
            reset_limit_us = 10000
            tolerance_us = 0
        # Return the result to the caller so the next pipeline stage can continue.
        return DummyDevice()

    # Define test___init____sets_pulse_level(), a named step in the decoding/support pipeline.
    def test___init____sets_pulse_level(self):
        det = PulseDetectEdges(pulse_level=0)
        self.assertEqual(det.pulse_level, 0)

    # Define test_reset__clears_pending_state(), a named step in the decoding/support pipeline.
    def test_reset__clears_pending_state(self):
        det = PulseDetectEdges()
        det.pending_pulse = 123
        det.reset()
        self.assertEqual(det.pending_pulse, 0)

    # Define test__us_to_samples__converts_using_sample_rate(), a named step in the decoding/support pipeline.
    def test__us_to_samples__converts_using_sample_rate(self):
        det = PulseDetectEdges(sample_rate=2000000)
        self.assertEqual(det._us_to_samples(10, 2000000), 20)

    # Define test__append_pair__adds_pair_to_current_pulses(), a named step in the decoding/support pipeline.
    def test__append_pair__adds_pair_to_current_pulses(self):
        det = PulseDetectEdges()
        det._append_pair(det._pulses, 220, 408)
        self.assertEqual(list(zip(det._pulses.pulse, det._pulses.gap)), [(220, 408)])


    # Define test__track_max_pulse__ignores_edge_adapter_outliers(), a named step in the decoding/support pipeline.
    def test__track_max_pulse__ignores_edge_adapter_outliers(self):
        det = PulseDetectEdges()
        det._track_max_pulse(500)
        det._track_max_pulse(PD_EDGE_MAX_TRACKED_PULSE_SAMPLES + 1)
        self.assertEqual(det.max_pulse_samples, 500)


    # Define test_package__zero_width_pulse_preserves_previous_pair_without_merging_gaps(), a named step in the decoding/support pipeline.
    def test_package__zero_width_pulse_preserves_previous_pair_without_merging_gaps(self):
        det = PulseDetectEdges(pulse_level=1, device=self._no_lead_in_device())
        edges = [
            (1, 500),
            (0, 3988),
            (1, 0),
            (0, 2245),
            (1, 500),
            (0, 16000),
        ]
        kind, pulses = det.package(edges)
        self.assertEqual(kind, PULSE_DATA_OOK)
        self.assertGreaterEqual(pulses.num_pulses, 2)
        self.assertEqual(pulses.pulse[0], 500)
        self.assertEqual(pulses.gap[0], 3988)
        self.assertNotEqual(pulses.gap[0], 3988 + 2245)

    # Define test_package__huge_active_pulse_resets_detector(), a named step in the decoding/support pipeline.
    def test_package__huge_active_pulse_resets_detector(self):
        det = PulseDetectEdges(pulse_level=1, device=self._no_lead_in_device())
        edges = [
            (1, 500),
            (0, 500),
            (1, PD_EDGE_MAX_TRACKED_PULSE_SAMPLES + 28000),
            (0, 33055),
        ]
        kind, pulses = det.package(edges)
        self.assertEqual(kind, 0)
        self.assertEqual(det.ook_state, 0)
        self.assertEqual(det._pulses.num_pulses, 0)

    @unittest.skip("Private merge behavior needs a fixture copied from a specific rtl_433 edge case before enabling.")
    # Define test__merge_short_gap_into_pulse__merges_short_gap_into_previous_pulse(), a named step in the decoding/support pipeline.
    def test__merge_short_gap_into_pulse__merges_short_gap_into_previous_pulse(self):
        pass

    # Define test__finish_package__returns_ook_when_enough_pulses(), a named step in the decoding/support pipeline.
    def test__finish_package__returns_ook_when_enough_pulses(self):
        det = PulseDetectEdges()
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for _ in range(16):
            det._append_pair(det._pulses, 220, 408)
        kind, pulses = det._finish_package(det._pulses)
        self.assertEqual(kind, PULSE_DATA_OOK)
        self.assertEqual(pulses.num_pulses, 16)

    # Define test__gap_ends_package__detects_long_gap(), a named step in the decoding/support pipeline.
    def test__gap_ends_package__detects_long_gap(self):
        det = PulseDetectEdges(device=self._no_lead_in_device())
        self.assertTrue(det._gap_ends_package(100001, 1))
        self.assertFalse(det._gap_ends_package(9999, 1))

    # Define test_package__pairs_edges_with_matching_pulse_level(), a named step in the decoding/support pipeline.
    def test_package__pairs_edges_with_matching_pulse_level(self):
        det = PulseDetectEdges(pulse_level=0, device=self._no_lead_in_device())
        edges = [(0, 220), (1, 408)] * 16
        kind, pulses = det.package(edges)
        self.assertEqual(kind, 0)
        self.assertEqual(pulses.num_pulses, 15)

    # Define test_flush__finishes_pending_package(), a named step in the decoding/support pipeline.
    def test_flush__finishes_pending_package(self):
        det = PulseDetectEdges(pulse_level=0, device=self._no_lead_in_device())
        det.package([(0, 220), (1, 408)] * 16)
        kind, pulses = det.flush()
        self.assertEqual(kind, PULSE_DATA_OOK)
        self.assertEqual(pulses.num_pulses, 16)

    # Define test_widths_to_pulse_data__pairs_alternating_widths(), a named step in the decoding/support pipeline.
    def test_widths_to_pulse_data__pairs_alternating_widths(self):
        pd = widths_to_pulse_data([1, 2, 3, 4])
        self.assertEqual(list(zip(pd.pulse, pd.gap)), [(1, 2), (3, 4)])


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
