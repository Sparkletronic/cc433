import unittest

from cc433 import baseband


# Define the TestBaseband class, which groups related state and behavior for this stage.
class TestBaseband(unittest.TestCase):
    # Define test__pow10__returns_power_of_ten(), a named step in the decoding/support pipeline.
    def test__pow10__returns_power_of_ten(self):
        self.assertEqual(baseband._pow10(2), 100)

    # Define test_amp_to_db__positive_value_is_inverse_of_db_to_amp_approximately(), a named step in the decoding/support pipeline.
    def test_amp_to_db__positive_value_is_inverse_of_db_to_amp_approximately(self):
        amp = baseband.db_to_amp(-10.0)
        self.assertAlmostEqual(baseband.amp_to_db(amp), -10.0, delta=0.5)

    # Define test_mag_to_db__positive_value_is_inverse_of_db_to_mag_approximately(), a named step in the decoding/support pipeline.
    def test_mag_to_db__positive_value_is_inverse_of_db_to_mag_approximately(self):
        mag = baseband.db_to_mag(-10.0)
        self.assertAlmostEqual(baseband.mag_to_db(mag), -10.0, delta=0.5)

    # Define test_db_to_amp__returns_integer_amplitude(), a named step in the decoding/support pipeline.
    def test_db_to_amp__returns_integer_amplitude(self):
        self.assertIsInstance(baseband.db_to_amp(0.0), int)
        self.assertGreater(baseband.db_to_amp(0.0), 0)

    # Define test_db_to_mag__returns_integer_magnitude(), a named step in the decoding/support pipeline.
    def test_db_to_mag__returns_integer_magnitude(self):
        self.assertIsInstance(baseband.db_to_mag(0.0), int)
        self.assertGreater(baseband.db_to_mag(0.0), 0)

    # Define test_db_to_amp_f__rounds_scaled_ratio(), a named step in the decoding/support pipeline.
    def test_db_to_amp_f__rounds_scaled_ratio(self):
        self.assertEqual(baseband.db_to_amp_f(0.0), 1)

    # Define test_db_to_mag_f__rounds_scaled_ratio(), a named step in the decoding/support pipeline.
    def test_db_to_mag_f__rounds_scaled_ratio(self):
        self.assertEqual(baseband.db_to_mag_f(0.0), 1)

    # Define test_min___returns_smaller_value(), a named step in the decoding/support pipeline.
    def test_min___returns_smaller_value(self):
        self.assertEqual(baseband.min_(2, 3), 2)

    # Define test_max___returns_larger_value(), a named step in the decoding/support pipeline.
    def test_max___returns_larger_value(self):
        self.assertEqual(baseband.max_(2, 3), 3)


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
