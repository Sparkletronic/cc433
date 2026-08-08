import unittest

from cc433.test_vectors.acurite_cc1101_capture_01 import make_pulse_data, print_summary
from cc433.test_vectors import test_v0_8_pipeline


# Define the TestAcuriteCc1101Capture01 class, which groups related state and behavior for this stage.
class TestAcuriteCc1101Capture01(unittest.TestCase):
    # Define test_make_pulse_data__returns_aligned_pulse_data_fixture(), a named step in the decoding/support pipeline.
    def test_make_pulse_data__returns_aligned_pulse_data_fixture(self):
        pd = make_pulse_data()
        pd.assert_invariants()
        self.assertGreater(pd.num_pulses, 0)

    # Define test_print_summary__prints_without_error(), a named step in the decoding/support pipeline.
    def test_print_summary__prints_without_error(self):
        self.assertIsNone(print_summary())


# Define the TestV08PipelineCompatibilityTests class, which groups related state and behavior for this stage.
class TestV08PipelineCompatibilityTests(unittest.TestCase):
    # Define test_make_edges_from_pairs__alternates_pulse_and_gap_levels(), a named step in the decoding/support pipeline.
    def test_make_edges_from_pairs__alternates_pulse_and_gap_levels(self):
        edges = test_v0_8_pipeline.make_edges_from_pairs([(1, 2)], pulse_level=0)
        self.assertEqual(edges, [(0, 1), (1, 2)])

    # Define test_check_known_raw_acurite_decode__passes(), a named step in the decoding/support pipeline.
    def test_check_known_raw_acurite_decode__passes(self):
        self.assertEqual(test_v0_8_pipeline.check_known_raw_acurite_decode(), 1)

    # Define test_check_edge_detector_pwm_path__returns_ook_and_rows(), a named step in the decoding/support pipeline.
    def test_check_edge_detector_pwm_path__returns_ook_and_rows(self):
        kind, rows = test_v0_8_pipeline.check_edge_detector_pwm_path()
        self.assertEqual(kind, 1)
        self.assertGreater(rows, 0)

    # Define test_run_all__passes(), a named step in the decoding/support pipeline.
    def test_run_all__passes(self):
        self.assertTrue(test_v0_8_pipeline.run_all())


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
