import unittest

from tests._helpers import import_or_skip


# Define the TestManagedSPI class, which groups related state and behavior for this stage.
class TestManagedSPI(unittest.TestCase):
    @unittest.skip("ManagedSPI imports machine.Pin/SPI and requires MicroPython hardware.")
    # Define test___init____creates_spi_with_pins(), a named step in the decoding/support pipeline.
    def test___init____creates_spi_with_pins(self):
        pass

    @unittest.skip("ManagedSPI imports machine.Pin/SPI and requires MicroPython hardware.")
    # Define test___repr____includes_configuration(), a named step in the decoding/support pipeline.
    def test___repr____includes_configuration(self):
        pass


# Define the TestSpiBusManager class, which groups related state and behavior for this stage.
class TestSpiBusManager(unittest.TestCase):
    @unittest.skip("SpiBusManager requires machine.SPI; enable with a fake machine module or on device.")
    # Define test_get_spi__reuses_existing_key_with_same_configuration(), a named step in the decoding/support pipeline.
    def test_get_spi__reuses_existing_key_with_same_configuration(self):
        pass

    @unittest.skip("SpiBusManager requires machine.SPI; enable with a fake machine module or on device.")
    # Define test_get_spi__rejects_same_key_with_different_configuration(), a named step in the decoding/support pipeline.
    def test_get_spi__rejects_same_key_with_different_configuration(self):
        pass


# Define the TestCC1101Radio class, which groups related state and behavior for this stage.
class TestCC1101Radio(unittest.TestCase):
    @unittest.skip("CC1101Radio imports micropython.const and machine.Pin; test on device or with hardware fakes.")
    # Define test___init____stores_spi_and_pins(), a named step in the decoding/support pipeline.
    def test___init____stores_spi_and_pins(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__log__honors_verbosity(), a named step in the decoding/support pipeline.
    def test__log__honors_verbosity(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__wait_ready__waits_for_miso_ready(), a named step in the decoding/support pipeline.
    def test__wait_ready__waits_for_miso_ready(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__begin__selects_chip_and_waits_ready(), a named step in the decoding/support pipeline.
    def test__begin__selects_chip_and_waits_ready(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__end__deselects_chip(), a named step in the decoding/support pipeline.
    def test__end__deselects_chip(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__select__drives_cs_low(), a named step in the decoding/support pipeline.
    def test__select__drives_cs_low(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test__deselect__drives_cs_high(), a named step in the decoding/support pipeline.
    def test__deselect__drives_cs_high(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_read_config_reg__reads_single_config_register(), a named step in the decoding/support pipeline.
    def test_read_config_reg__reads_single_config_register(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_read_status_reg__reads_single_status_register(), a named step in the decoding/support pipeline.
    def test_read_status_reg__reads_single_status_register(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_write_reg__writes_single_register(), a named step in the decoding/support pipeline.
    def test_write_reg__writes_single_register(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_strobe__sends_command_strobe(), a named step in the decoding/support pipeline.
    def test_strobe__sends_command_strobe(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_reset__issues_reset_sequence(), a named step in the decoding/support pipeline.
    def test_reset__issues_reset_sequence(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_marcstate__reads_marcstate_status(), a named step in the decoding/support pipeline.
    def test_marcstate__reads_marcstate_status(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_dump_basic_status__prints_status_registers(), a named step in the decoding/support pipeline.
    def test_dump_basic_status__prints_status_registers(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_dump_key_config__prints_key_config_registers(), a named step in the decoding/support pipeline.
    def test_dump_key_config__prints_key_config_registers(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_configure_async_ook_43392__writes_async_ook_config(), a named step in the decoding/support pipeline.
    def test_configure_async_ook_43392__writes_async_ook_config(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_start_rx__enters_receive_mode(), a named step in the decoding/support pipeline.
    def test_start_rx__enters_receive_mode(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_idle__enters_idle_mode(), a named step in the decoding/support pipeline.
    def test_idle__enters_idle_mode(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_recover_rx__recovers_receive_mode(), a named step in the decoding/support pipeline.
    def test_recover_rx__recovers_receive_mode(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_gdo0_state__reads_gdo0_pin(), a named step in the decoding/support pipeline.
    def test_gdo0_state__reads_gdo0_pin(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_gdo2_state__reads_gdo2_pin(), a named step in the decoding/support pipeline.
    def test_gdo2_state__reads_gdo2_pin(self):
        pass

    @unittest.skip("CC1101Radio hardware access stub.")
    # Define test_dump_gdo__prints_gdo_pin_states(), a named step in the decoding/support pipeline.
    def test_dump_gdo__prints_gdo_pin_states(self):
        pass


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
