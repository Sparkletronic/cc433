import unittest

from cc433.pulse_data import PD_MAX_PULSES, PulseData


# Define the TestPulseData class, which groups related state and behavior for this stage.
class TestPulseData(unittest.TestCase):
    # Define test___init____sets_empty_aligned_arrays(), a named step in the decoding/support pipeline.
    def test___init____sets_empty_aligned_arrays(self):
        pd = PulseData(sample_rate=123)
        self.assertEqual(pd.sample_rate, 123)
        self.assertEqual(pd.num_pulses, 0)
        self.assertEqual(pd.pulse, [])
        self.assertEqual(pd.gap, [])

    # Define test_clear__preserves_sample_rate_and_empties_data(), a named step in the decoding/support pipeline.
    def test_clear__preserves_sample_rate_and_empties_data(self):
        pd = PulseData(sample_rate=123)
        pd.append(1, 2)
        pd.clear()
        self.assertEqual(pd.sample_rate, 123)
        self.assertEqual(pd.num_pulses, 0)

    # Define test_append__adds_aligned_pulse_gap_row(), a named step in the decoding/support pipeline.
    def test_append__adds_aligned_pulse_gap_row(self):
        pd = PulseData()
        pd.append(220, 408)
        self.assertEqual(pd.num_pulses, 1)
        self.assertEqual(pd.pulse, [220])
        self.assertEqual(pd.gap, [408])

    # Define test_append__raises_when_full(), a named step in the decoding/support pipeline.
    def test_append__raises_when_full(self):
        pd = PulseData()
        pd.num_pulses = PD_MAX_PULSES
        # Use a context manager so the resource is opened and closed in a controlled way.
        with self.assertRaises(RuntimeError):
            pd.append(1, 1)

    # Define test_pop__removes_last_row(), a named step in the decoding/support pipeline.
    def test_pop__removes_last_row(self):
        pd = PulseData()
        pd.append(1, 2)
        self.assertEqual(pd.pop(), (1, 2))
        self.assertEqual(pd.num_pulses, 0)

    # Define test_pop__empty_returns_zero_pair(), a named step in the decoding/support pipeline.
    def test_pop__empty_returns_zero_pair(self):
        self.assertEqual(PulseData().pop(), (0, 0))

    # Define test_normalize__trims_to_shortest_aligned_length(), a named step in the decoding/support pipeline.
    def test_normalize__trims_to_shortest_aligned_length(self):
        pd = PulseData()
        pd.num_pulses = 3
        pd.pulse = [1, 2]
        pd.gap = [3]
        self.assertEqual(pd.sync_lengths(), 1)
        self.assertEqual(pd.pulse, [1])
        self.assertEqual(pd.gap, [3])

    # Define test_assert_invariants__passes_when_aligned(), a named step in the decoding/support pipeline.
    def test_assert_invariants__passes_when_aligned(self):
        pd = PulseData()
        pd.append(1, 2)
        pd.assert_invariants()

    # Define test_assert_invariants__raises_when_unaligned(), a named step in the decoding/support pipeline.
    def test_assert_invariants__raises_when_unaligned(self):
        pd = PulseData()
        pd.num_pulses = 1
        # Use a context manager so the resource is opened and closed in a controlled way.
        with self.assertRaises(AssertionError):
            pd.assert_invariants()

    # Define test_shift__clears_when_not_more_than_half_full(), a named step in the decoding/support pipeline.
    def test_shift__clears_when_not_more_than_half_full(self):
        pd = PulseData()
        pd.append(1, 2)
        pd.shift()
        self.assertEqual(pd.num_pulses, 0)

    # Define test_shift__drops_first_half_when_more_than_half_full(), a named step in the decoding/support pipeline.
    def test_shift__drops_first_half_when_more_than_half_full(self):
        pd = PulseData()
        count = PD_MAX_PULSES // 2 + 1
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for i in range(count):
            pd.append(i, i + 1)
        pd.shift()
        self.assertEqual(pd.num_pulses, 1)
        self.assertEqual(pd.offset, PD_MAX_PULSES // 2)

    # Define test_dump__prints_without_error(), a named step in the decoding/support pipeline.
    def test_dump__prints_without_error(self):
        pd = PulseData()
        pd.append(1, 2)
        pd.dump()


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
