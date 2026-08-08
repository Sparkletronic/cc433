import unittest

from cc433.cc1101_source import CC1101AsyncOOKSource, edges_to_envelope, edges_to_pulse_data, widths_to_pulse_data


# Define the FakeRadio class, which groups related state and behavior for this stage.
class FakeRadio:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self):
        self.configured = None
        self.started = False
        self.recovered = False
        self._state = 0

    # Define configure_async_ook_43392(), a named step in the decoding/support pipeline.
    def configure_async_ook_43392(self, **kwargs):
        self.configured = kwargs

    # Define start_rx(), a named step in the decoding/support pipeline.
    def start_rx(self):
        self.started = True
        # Return the result to the caller so the next pipeline stage can continue.
        return "started"

    # Define recover_rx(), a named step in the decoding/support pipeline.
    def recover_rx(self):
        self.recovered = True

    # Define gdo0_state(), a named step in the decoding/support pipeline.
    def gdo0_state(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return self._state


# Define the TestCC1101AsyncOOKSource class, which groups related state and behavior for this stage.
class TestCC1101AsyncOOKSource(unittest.TestCase):
    # Define test___init____stores_radio_and_sample_rate(), a named step in the decoding/support pipeline.
    def test___init____stores_radio_and_sample_rate(self):
        radio = FakeRadio()
        source = CC1101AsyncOOKSource(radio, sample_rate=123)
        self.assertIs(source.radio, radio)
        self.assertEqual(source.sample_rate, 123)

    # Define test_configure__delegates_to_radio(), a named step in the decoding/support pipeline.
    def test_configure__delegates_to_radio(self):
        radio = FakeRadio(); source = CC1101AsyncOOKSource(radio)
        source.configure(rx_bw_khz=100, data_rate_kbps=20)
        self.assertEqual(radio.configured, {"rx_bw_khz": 100, "data_rate_kbps": 20})

    # Define test_start_rx__delegates_to_radio(), a named step in the decoding/support pipeline.
    def test_start_rx__delegates_to_radio(self):
        source = CC1101AsyncOOKSource(FakeRadio())
        self.assertEqual(source.start_rx(), "started")

    # Define test_recover_rx__delegates_to_radio(), a named step in the decoding/support pipeline.
    def test_recover_rx__delegates_to_radio(self):
        radio = FakeRadio(); source = CC1101AsyncOOKSource(radio)
        source.recover_rx()
        self.assertTrue(radio.recovered)

    # Define test_widths_to_pulse_data__method_uses_source_sample_rate(), a named step in the decoding/support pipeline.
    def test_widths_to_pulse_data__method_uses_source_sample_rate(self):
        source = CC1101AsyncOOKSource(FakeRadio(), sample_rate=123)
        pd = source.widths_to_pulse_data([1, 2, 3, 4])
        self.assertEqual(pd.sample_rate, 123)
        self.assertEqual(list(zip(pd.pulse, pd.gap)), [(1, 2), (3, 4)])

    # Define test_edges_to_pulse_data__method_uses_source_sample_rate(), a named step in the decoding/support pipeline.
    def test_edges_to_pulse_data__method_uses_source_sample_rate(self):
        source = CC1101AsyncOOKSource(FakeRadio(), sample_rate=123)
        pd = source.edges_to_pulse_data([(0, 1), (1, 2)])
        self.assertEqual(pd.sample_rate, 123)
        self.assertEqual(list(zip(pd.pulse, pd.gap)), [(1, 2)])

    @unittest.skip("capture_edges_poll is hardware/timing dependent; exercise manually on-device.")
    # Define test_capture_edges_poll__polls_radio_gdo0_edges(), a named step in the decoding/support pipeline.
    def test_capture_edges_poll__polls_radio_gdo0_edges(self):
        pass

    # Define test_edges_to_envelope__method_delegates_to_function(), a named step in the decoding/support pipeline.
    def test_edges_to_envelope__method_delegates_to_function(self):
        source = CC1101AsyncOOKSource(FakeRadio())
        env = source.edges_to_envelope([(0, 2), (1, 1)], pulse_level=0, high=9, low=1, lead_in_us=1)
        self.assertEqual(env, [1, 9, 9, 1])

    @unittest.skip("edges_to_pulses_via_detector is an integration path; add fixed edge fixture before enabling.")
    # Define test_edges_to_pulses_via_detector__converts_edges_through_pulse_detector(), a named step in the decoding/support pipeline.
    def test_edges_to_pulses_via_detector__converts_edges_through_pulse_detector(self):
        pass


# Define the TestCC1101SourceFunctions class, which groups related state and behavior for this stage.
class TestCC1101SourceFunctions(unittest.TestCase):
    @unittest.skip("capture_edges_poll is hardware/timing dependent; exercise manually on-device.")
    # Define test_capture_edges_poll__polls_radio_gdo0_edges(), a named step in the decoding/support pipeline.
    def test_capture_edges_poll__polls_radio_gdo0_edges(self):
        pass

    # Define test_edges_to_pulse_data__pairs_selected_pulse_level_with_following_gap(), a named step in the decoding/support pipeline.
    def test_edges_to_pulse_data__pairs_selected_pulse_level_with_following_gap(self):
        pd = edges_to_pulse_data([(0, 220), (1, 408), (0, 408), (1, 220)], pulse_level=0)
        self.assertEqual(list(zip(pd.pulse, pd.gap)), [(220, 408), (408, 220)])

    # Define test_edges_to_pulse_data__drops_pending_pulse_after_large_gap(), a named step in the decoding/support pipeline.
    def test_edges_to_pulse_data__drops_pending_pulse_after_large_gap(self):
        pd = edges_to_pulse_data([(0, 220), (1, 20000), (1, 408)], pulse_level=0, max_gap_us=10000)
        self.assertEqual(pd.num_pulses, 0)

    # Define test_widths_to_pulse_data__pairs_alternating_widths(), a named step in the decoding/support pipeline.
    def test_widths_to_pulse_data__pairs_alternating_widths(self):
        pd = widths_to_pulse_data([1, 2, 3, 4], starts_high=True)
        self.assertEqual(list(zip(pd.pulse, pd.gap)), [(1, 2), (3, 4)])

    # Define test_edges_to_envelope__renders_edges_to_sampled_envelope(), a named step in the decoding/support pipeline.
    def test_edges_to_envelope__renders_edges_to_sampled_envelope(self):
        env = edges_to_envelope([(0, 2), (1, 3)], pulse_level=0, high=9, low=1, lead_in_us=1)
        self.assertEqual(env, [1, 9, 9, 1, 1, 1])


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()

# Define the FakeFlipperRadio class, which groups related state and behavior for this stage.
class FakeFlipperRadio(FakeRadio):
    # Define configure_cc1101_async_ook(), a named step in the decoding/support pipeline.
    def configure_cc1101_async_ook(self, **kwargs):
        self.configured = kwargs


# Define the TestCC1101DeviceProfileConfiguration class, which groups related state and behavior for this stage.
class TestCC1101DeviceProfileConfiguration(unittest.TestCase):
    # Define test_configure__uses_device_cc1101_profile_values(), a named step in the decoding/support pipeline.
    def test_configure__uses_device_cc1101_profile_values(self):
        from cc433.devices.acurite import make_acurite_6045m_device

        device = make_acurite_6045m_device()
        radio = FakeFlipperRadio()
        source = CC1101AsyncOOKSource(radio)

        source.configure(device=device)

        self.assertEqual(radio.configured["rx_bw_khz"], device.cc1101_rx_bw_khz)
        self.assertEqual(radio.configured["data_rate_kbps"], device.cc1101_data_rate_kbps)
        self.assertEqual(radio.configured["registers"], device.cc1101_registers)

    # Define test_configure__explicit_values_override_device_experiment_labels(), a named step in the decoding/support pipeline.
    def test_configure__explicit_values_override_device_experiment_labels(self):
        from cc433.devices.infactory import make_infactory_device

        device = make_infactory_device()
        radio = FakeFlipperRadio()
        source = CC1101AsyncOOKSource(radio)

        source.configure(device=device, rx_bw_khz=406, data_rate_kbps=20)

        self.assertEqual(radio.configured["rx_bw_khz"], 406)
        self.assertEqual(radio.configured["data_rate_kbps"], 20)
        self.assertEqual(radio.configured["registers"], device.cc1101_registers)
