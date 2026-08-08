import unittest

from cc433.bitbuffer import BitBuffer
from cc433.devices.acurite import make_acurite_6045m_device
from tests._helpers import add_bytes

RAW_REPLAY_6045M = bytes.fromhex("c048af12116aebc0ef")
PRE_INVERT_REPLAY_6045M = bytes((~b) & 0xFF for b in RAW_REPLAY_6045M)


# Define the TestAcurite6045MRegression class, which groups related state and behavior for this stage.
class TestAcurite6045MRegression(unittest.TestCase):
    # Define test_known_replay_raw_row__decodes_to_cc433_reference_fields(), a named step in the decoding/support pipeline.
    def test_known_replay_raw_row__decodes_to_cc433_reference_fields(self):
        bb = add_bytes(BitBuffer(), RAW_REPLAY_6045M)
        device = make_acurite_6045m_device(invert_before_decode=False)
        self.assertEqual(device.decode_fn(device, bb), 1)
        decoded = device.decoded[0]
        self.assertEqual(decoded["raw_msg"], "C048AF12116AEBC0EF")
        self.assertEqual(decoded["id"], 72)
        self.assertEqual(decoded["channel"], "A")
        self.assertAlmostEqual(decoded["temperature_F"], 80.2)
        self.assertEqual(decoded["humidity"], 18)
        self.assertEqual(decoded["strike_count"], 215)
        self.assertEqual(decoded["storm_dist"], 0)

    # Define test_known_replay_pre_invert_row__decodes_to_same_raw_message(), a named step in the decoding/support pipeline.
    def test_known_replay_pre_invert_row__decodes_to_same_raw_message(self):
        bb = add_bytes(BitBuffer(), PRE_INVERT_REPLAY_6045M)
        device = make_acurite_6045m_device(invert_before_decode=True)
        self.assertEqual(device.decode_fn(device, bb), 1)
        self.assertEqual(device.decoded[0]["raw_msg"], "C048AF12116AEBC0EF")

    @unittest.skip("Enable after recording the exact PulseData pulse[]/gap[] fixture from the Flipper replay.")
    # Define test_known_replay_pulses__slicer_invert_and_decode_match_cc433_raw_message(), a named step in the decoding/support pipeline.
    def test_known_replay_pulses__slicer_invert_and_decode_match_cc433_raw_message(self):
        pass


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
