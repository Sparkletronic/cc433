import unittest

from tests._helpers import import_or_skip

engine = import_or_skip("cc433.acquisition_engine")


# Define the TestAcquisitionEngineFunctions class, which groups related state and behavior for this stage.
class TestAcquisitionEngineFunctions(unittest.TestCase):
    @unittest.skip("AcquisitionEngine construction requires rp2 PIO hardware.")
    # Define test___init____requires_pio_hardware_and_pin_or_radio(), a named step in the decoding/support pipeline.
    def test___init____requires_pio_hardware_and_pin_or_radio(self):
        pass

    @unittest.skip("start requires rp2 PIO hardware.")
    # Define test_start__activates_state_machine(), a named step in the decoding/support pipeline.
    def test_start__activates_state_machine(self):
        pass

    @unittest.skip("stop requires rp2 PIO hardware.")
    # Define test_stop__deactivates_state_machine(), a named step in the decoding/support pipeline.
    def test_stop__deactivates_state_machine(self):
        pass

    @unittest.skip("_remaining_to_us requires a constructed AcquisitionEngine instance.")
    # Define test__remaining_to_us__converts_pio_counter_to_microseconds(), a named step in the decoding/support pipeline.
    def test__remaining_to_us__converts_pio_counter_to_microseconds(self):
        pass

    @unittest.skip("drain_edges requires rp2 PIO hardware.")
    # Define test_drain_edges__returns_level_duration_tuples(), a named step in the decoding/support pipeline.
    def test_drain_edges__returns_level_duration_tuples(self):
        pass


    # Define test_append_edge_duration__merges_short_glitches_into_previous(), a named step in the decoding/support pipeline.
    def test_append_edge_duration__merges_short_glitches_into_previous(self):
        out = []
        engine.append_edge_duration(out, 1, 200, deglitch_us=30)
        engine.append_edge_duration(out, 0, 12, deglitch_us=30)
        engine.append_edge_duration(out, 1, 190, deglitch_us=30)
        self.assertEqual(out, [[1, 402]])

    # Define test_clean_edge_durations__merges_adjacent_same_level(), a named step in the decoding/support pipeline.
    def test_clean_edge_durations__merges_adjacent_same_level(self):
        edges = [(1, 100), (1, 50), (0, 200), (0, 25), (1, 300)]
        self.assertEqual(
            engine.clean_edge_durations(edges, deglitch_us=30),
            [(1, 150), (0, 225), (1, 300)],
        )

    # Define test_clean_edge_durations__drops_non_positive_durations(), a named step in the decoding/support pipeline.
    def test_clean_edge_durations__drops_non_positive_durations(self):
        edges = [(1, 0), (0, -5), (1, 100)]
        self.assertEqual(
            engine.clean_edge_durations(edges, deglitch_us=30),
            [(1, 100)],
        )

    # Define test_summarize_edges__returns_none_and_prints_summary(), a named step in the decoding/support pipeline.
    def test_summarize_edges__returns_none_and_prints_summary(self):
        self.assertIsNone(engine.summarize_edges([(0, 10), (1, 200), (0, 2000)]))

    # Define test_summarize_pulses__returns_none_and_prints_summary(), a named step in the decoding/support pipeline.
    def test_summarize_pulses__returns_none_and_prints_summary(self):
        from cc433.pulse_data import PulseData
        pd = PulseData(); pd.append(220, 408)
        self.assertIsNone(engine.summarize_pulses(pd))

    @unittest.skip("run_pio_capture_loop requires live source/radio hardware.")
    # Define test_run_pio_capture_loop__captures_and_decodes_live_packages(), a named step in the decoding/support pipeline.
    def test_run_pio_capture_loop__captures_and_decodes_live_packages(self):
        pass


# Define the FakeConfigurableSource class, which groups related state and behavior for this stage.
class FakeConfigurableSource:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self):
        self.configured_device = None
        self.debug = None

    # Define configure_for_device(), a named step in the decoding/support pipeline.
    def configure_for_device(self, device):
        self.configured_device = device
        # Return the result to the caller so the next pipeline stage can continue.
        return True


# Define the TestDeviceProfileConfiguration class, which groups related state and behavior for this stage.
class TestDeviceProfileConfiguration(unittest.TestCase):
    # Define test_device_profiles__carry_canonical_acquisition_settings(), a named step in the decoding/support pipeline.
    def test_device_profiles__carry_canonical_acquisition_settings(self):
        from cc433.devices.acurite import make_acurite_6045m_device
        from cc433.devices.infactory import make_infactory_device

        acurite = make_acurite_6045m_device()
        infactory = make_infactory_device()

        self.assertEqual(acurite.capture_max_edges, 512)
        self.assertEqual(acurite.capture_timeout_ms, 75)
        self.assertEqual(acurite.capture_min_duration_us, 0)
        self.assertEqual(acurite.capture_deglitch_us, 30)

        self.assertEqual(infactory.capture_max_edges, 1024)
        self.assertEqual(infactory.capture_timeout_ms, 75)
        self.assertEqual(infactory.capture_min_duration_us, 0)
        self.assertEqual(infactory.capture_deglitch_us, 0)

    # Define test_device_acquisition_value__explicit_argument_overrides_profile(), a named step in the decoding/support pipeline.
    def test_device_acquisition_value__explicit_argument_overrides_profile(self):
        # Define the DeviceLike class, which groups related state and behavior for this stage.
        class DeviceLike:
            capture_max_edges = 512

        self.assertEqual(
            engine._device_acquisition_value(DeviceLike(), "capture_max_edges", 128, 512),
            128,
        )

    # Define test_device_acquisition_value__uses_profile_when_argument_is_none(), a named step in the decoding/support pipeline.
    def test_device_acquisition_value__uses_profile_when_argument_is_none(self):
        # Define the DeviceLike class, which groups related state and behavior for this stage.
        class DeviceLike:
            capture_max_edges = 256

        self.assertEqual(
            engine._device_acquisition_value(DeviceLike(), "capture_max_edges", None, 512),
            256,
        )

    # Define test_new_decoded_items__returns_only_items_added_after_slice(), a named step in the decoding/support pipeline.
    def test_new_decoded_items__returns_only_items_added_after_slice(self):
        # Define the DeviceLike class, which groups related state and behavior for this stage.
        class DeviceLike:
            pass

        device = DeviceLike()
        device.decoded = [{"id": 1}]
        previous_len = engine._decoded_len(device)
        device.decoded.append({"id": 2})

        self.assertEqual(engine._new_decoded_items(device, previous_len), [{"id": 2}])


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
