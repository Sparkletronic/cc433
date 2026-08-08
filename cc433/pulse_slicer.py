# -----------------------------------------------------------------------------
# pulse_slicer.py
# Pulse slicers convert measured pulse/gap timings into rows of bits, matching rtl_433 slicer behavior.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/pulse_slicer.py
# MicroPython subset of rtl_433 pulse_slicer.c: pulse_slicer_pwm() only.

from .bitbuffer import BitBuffer
from .debug import (
    LOG_NONE,
    LOG_SLICER,
    LOG_SLICER_DETAIL,
    LOG_DECODER,
    log,
)

INT_MAX = 0x3fffffff
OOK_PULSE_PWM = "OOK_PULSE_PWM"
OOK_PULSE_PPM = "OOK_PULSE_PPM"

# CC1101/PIO acquisition profile currently known to work for Acurite.
# Register values remain in the radio driver; devices carry the selected
# profile name and tunable frontend parameters so experiments can be
# device-specific without changing rtl_433 protocol metadata.
CC1101_ASYNC_OOK_PROFILE = "CC1101_ASYNC_OOK_PROFILE"

PPM_CLASSIFICATION_BELOW_SYNC = "BELOW_SYNC"
PPM_CLASSIFICATION_SYNC = "SYNC"
PPM_CLASSIFICATION_BETWEEN_SYNC_AND_ZERO = "BETWEEN_SYNC_AND_ZERO"
PPM_CLASSIFICATION_BIT_0 = "BIT_0"
PPM_CLASSIFICATION_BETWEEN_ZERO_AND_ONE = "BETWEEN_ZERO_AND_ONE"
PPM_CLASSIFICATION_BIT_1 = "BIT_1"
PPM_CLASSIFICATION_BETWEEN_ONE_AND_RESET = "BETWEEN_ONE_AND_RESET"
PPM_CLASSIFICATION_RESET = "RESET_EOM"
PPM_CLASSIFICATION_SYNC_PRE = "SYNC_PRE"
PPM_CLASSIFICATION_ABOVE_RESET = "ABOVE_RESET"
PPM_CLASSIFICATION_UNKNOWN_ROW = "UNKNOWN_ROW"

# Exact CC1101 register values inherited from configure_cc1101_async_ook().
# The key names intentionally mirror CC1101 register names, while the radio
# driver remains responsible for mapping names to register addresses.
CC1101_ASYNC_OOK_REGISTERS = {
    "ADDR": 0x00,      # Device address (unused in async OOK mode)
    "AGCCTRL0": 0x40,  # AGC hysteresis / filter settings
    "AGCCTRL1": 0x00,  # AGC carrier-sense relative threshold
    "AGCCTRL2": 0x03,  # AGC maximum gain, optimized for OOK reception
    "BSCFG": 0x6C,     # Bit synchronization configuration
    "CHANNR": 0x00,    # Channel number (base channel)
    "DEVIATN": 0x00,   # Frequency deviation (unused for OOK)
    "FIFOTHR": 0x47,   # FIFO thresholds
    "FOCCFG": 0x18,    # Frequency offset compensation configuration
    "FREND0": 0x11,    # Front-end TX configuration
    "FREND1": 0xB6,    # Front-end RX configuration
    "FREQ0": 0x71,     # Frequency control word (433.92 MHz)
    "FREQ1": 0xB0,     # Frequency control word (433.92 MHz)
    "FREQ2": 0x10,     # Frequency control word (433.92 MHz)
    "FSCAL0": 0x1F,    # Frequency synthesizer calibration
    "FSCAL1": 0x00,    # Frequency synthesizer calibration
    "FSCAL2": 0x2A,    # Frequency synthesizer calibration
    "FSCAL3": 0xE9,    # Frequency synthesizer calibration
    "FSCTRL0": 0x00,   # Frequency offset adjustment
    "FSCTRL1": 0x06,   # IF frequency setting
    "IOCFG0": 0x0D,    # GDO0 = asynchronous serial data output
    "IOCFG1": 0x2E,    # GDO1 = high impedance (unused)
    "IOCFG2": 0x2E,    # GDO2 = high impedance (unused)
    "MCSM0": 0x18,     # Auto-calibrate when entering RX/TX; remain in current state
    "MCSM1": 0x30,     # Stay in RX after packet activity
    "MCSM2": 0x07,     # RX timeout behavior
    "MDMCFG0": 0x00,   # Channel spacing exponent/mantissa
    "MDMCFG1": 0x00,   # Channel spacing exponent; no FEC
    "MDMCFG2": 0x30,   # ASK/OOK modulation, async serial mode
    "MDMCFG3": 0x32,   # Data rate mantissa (~3.79 kbps)
    "MDMCFG4": 0x67,   # RX bandwidth (~270 kHz) and data rate exponent
    "PKTCTRL0": 0x32,  # Infinite packet length, packet engine bypassed for async mode
    "PKTCTRL1": 0x04,  # Append status bytes; no address filtering
    "PKTLEN": 0xFF,    # Maximum packet length (unused in async mode)
    "SYNC0": 0x00,     # Sync word low byte (unused)
    "SYNC1": 0x00,     # Sync word high byte (unused)
    "TEST0": 0x09,     # Recommended SmartRF test setting
    "TEST1": 0x35,     # Recommended SmartRF test setting
    "TEST2": 0x81,     # Recommended SmartRF test setting
    "WORCTRL": 0xFB,   # Wake-on-radio control
    "WOREVT0": 0x6B,   # Wake-on-radio event timer low byte
    "WOREVT1": 0x87,   # Wake-on-radio event timer high byte
}


# Define the Device class, which groups related state and behavior for this stage.
class Device:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, name, short_width_us, long_width_us,
                 decode_fn=None, gap_limit_us=0, modulation=OOK_PULSE_PWM,
                 reset_limit_us=0, sync_width_us=0, tolerance_us=0,
                 deglitch_us=0, enable_lead_in=False, min_duration_us=0,
                 capture_max_edges=512, capture_timeout_ms=75,
                 capture_min_duration_us=None, capture_deglitch_us=None,
                 pulse_level=1, cc1101_profile=CC1101_ASYNC_OOK_PROFILE,
                 cc1101_rx_bw_khz=270, cc1101_data_rate_kbps=3.79,
                 cc1101_registers=None):
        # rtl_433 r_device properties. Timing values are in microseconds.
        self.decode_fn = decode_fn
        self.gap_limit_us = gap_limit_us
        self.long_width_us = long_width_us
        self.modulation = modulation
        self.name = name
        self.reset_limit_us = reset_limit_us
        self.short_width_us = short_width_us
        self.sync_width_us = sync_width_us
        self.tolerance_us = tolerance_us

        # CC1101/PIO acquisition properties added by this port.
        # capture_* names are the canonical acquisition profile. The older
        # deglitch_us/min_duration_us aliases are retained for compatibility
        # with existing callers while the call sites migrate.
        # Check this condition so only the matching signal/data case is handled here.
        if capture_deglitch_us is None:
            capture_deglitch_us = deglitch_us
        # Check this condition so only the matching signal/data case is handled here.
        if capture_min_duration_us is None:
            capture_min_duration_us = min_duration_us

        self.capture_deglitch_us = capture_deglitch_us
        self.capture_max_edges = capture_max_edges
        self.capture_min_duration_us = capture_min_duration_us
        self.capture_timeout_ms = capture_timeout_ms
        self.deglitch_us = capture_deglitch_us
        self.enable_lead_in = enable_lead_in
        self.min_duration_us = capture_min_duration_us
        self.pulse_level = pulse_level

        # CC1101 RF/frontend acquisition properties added by this port.
        # These are not rtl_433 decoder timings. They control whether the radio
        # produces a clean async edge stream before the rtl_433-like pipeline.
        self.cc1101_profile = cc1101_profile
        self.cc1101_rx_bw_khz = cc1101_rx_bw_khz
        self.cc1101_data_rate_kbps = cc1101_data_rate_kbps
        # Check this condition so only the matching signal/data case is handled here.
        if cc1101_registers is None:
            cc1101_registers = CC1101_ASYNC_OOK_REGISTERS
        self.cc1101_registers = dict(cc1101_registers)

        # Runtime decode counters added by this port.
        self.decode_events = 0
        self.decode_messages = 0
        self.decode_ok = 0


# Define _account_event(), a named step in the decoding/support pipeline.
def _account_event(device, bits, demod_name="pulse_slicer_pwm"):
    device.decode_events += 1
    # Check this condition so only the matching signal/data case is handled here.
    if device.decode_fn:
        ret = device.decode_fn(device, bits)
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        print(demod_name, bits.bits_per_row, bits.hex_rows())
        ret = 0
    # Check this condition so only the matching signal/data case is handled here.
    if ret > 0:
        device.decode_ok += 1
        device.decode_messages += ret
    # Return the result to the caller so the next pipeline stage can continue.
    return ret if ret > 0 else 0


# Define _bitbuffer_state(), a named step in the decoding/support pipeline.
def _bitbuffer_state(bits):
    # Return the result to the caller so the next pipeline stage can continue.
    return (bits.num_rows, tuple(bits.bits_per_row))


# Define _log(), a named step in the decoding/support pipeline.
def _log(debug, level, *args):
    log("[pulse_slicer]", debug, level, *args)


# Define _ppm_classification(), a named step in the decoding/support pipeline.
def _ppm_classification(gap_samples, zero_lower_samples, zero_upper_samples,
                         one_lower_samples, one_upper_samples,
                         sync_lower_samples, sync_upper_samples,
                         reset_limit_samples):
    # Check this condition so only the matching signal/data case is handled here.
    if sync_lower_samples < gap_samples < sync_upper_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_SYNC
    # Check this condition so only the matching signal/data case is handled here.
    if zero_lower_samples < gap_samples < zero_upper_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_BIT_0
    # Check this condition so only the matching signal/data case is handled here.
    if one_lower_samples < gap_samples < one_upper_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_BIT_1
    # Check this condition so only the matching signal/data case is handled here.
    if reset_limit_samples > 0 and gap_samples >= reset_limit_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_RESET
    # Check this condition so only the matching signal/data case is handled here.
    if reset_limit_samples > 0 and gap_samples < reset_limit_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_UNKNOWN_ROW

    # Check this condition so only the matching signal/data case is handled here.
    if gap_samples <= sync_lower_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_BELOW_SYNC
    # Check this condition so only the matching signal/data case is handled here.
    if sync_upper_samples <= gap_samples <= zero_lower_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_BETWEEN_SYNC_AND_ZERO
    # Check this condition so only the matching signal/data case is handled here.
    if zero_upper_samples <= gap_samples <= one_lower_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_BETWEEN_ZERO_AND_ONE
    # Check this condition so only the matching signal/data case is handled here.
    if one_upper_samples <= gap_samples:
        # Return the result to the caller so the next pipeline stage can continue.
        return PPM_CLASSIFICATION_ABOVE_RESET

    # Return the result to the caller so the next pipeline stage can continue.
    return PPM_CLASSIFICATION_BETWEEN_ONE_AND_RESET


# Define _current_row_bits(), a named step in the decoding/support pipeline.
def _current_row_bits(bits):
    # Check this condition so only the matching signal/data case is handled here.
    if bits.num_rows <= 0:
        # Return the result to the caller so the next pipeline stage can continue.
        return 0
    # Return the result to the caller so the next pipeline stage can continue.
    return bits.bits_per_row[bits.num_rows - 1]


# Define _log_ppm_classification(), a named step in the decoding/support pipeline.
def _log_ppm_classification(debug, pulse_index, gap_samples, classification, row_bits=None):
    # Check this condition so only the matching signal/data case is handled here.
    if row_bits is None:
        _log(
            debug,
            LOG_SLICER_DETAIL,
            "ppm",
            "idx", pulse_index,
            "gap_samples", gap_samples,
            "classification", classification,
        )
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        _log(
            debug,
            LOG_SLICER_DETAIL,
            "ppm",
            "idx", pulse_index,
            "gap_samples", gap_samples,
            "classification", classification,
            "row_bits", row_bits,
        )

# Define pulse_slicer_pwm(), a named step in the decoding/support pipeline.
def pulse_slicer_pwm(pulses, device, debug=LOG_NONE):
    samples_per_us = pulses.sample_rate / 1000000.0
    short_width_samples = int(device.short_width_us * samples_per_us)
    long_width_samples = int(device.long_width_us * samples_per_us)
    reset_limit_samples = int(device.reset_limit_us * samples_per_us)
    gap_limit_samples = int(device.gap_limit_us * samples_per_us)
    sync_width_samples = int(device.sync_width_us * samples_per_us)
    tolerance_samples = int(device.tolerance_us * samples_per_us)

    # Check this condition so only the matching signal/data case is handled here.
    if ((device.short_width_us > 0 and short_width_samples <= 0) or
        (device.long_width_us > 0 and long_width_samples <= 0) or
        (device.reset_limit_us > 0 and reset_limit_samples <= 0) or
        (device.gap_limit_us > 0 and gap_limit_samples <= 0) or
        (device.sync_width_us > 0 and sync_width_samples <= 0) or
        (device.tolerance_us > 0 and tolerance_samples <= 0)):
        _log(debug, LOG_SLICER, "sample rate too low for protocol", device.name)
        # Return the result to the caller so the next pipeline stage can continue.
        return 0

    events = 0
    bits = BitBuffer()

    # Check this condition so only the matching signal/data case is handled here.
    if tolerance_samples > 0:
        one_lower_samples = short_width_samples - tolerance_samples
        one_upper_samples = short_width_samples + tolerance_samples
        zero_lower_samples = long_width_samples - tolerance_samples
        zero_upper_samples = long_width_samples + tolerance_samples
        sync_lower_samples = sync_upper_samples = 0
        # Check this condition so only the matching signal/data case is handled here.
        if sync_width_samples > 0:
            sync_lower_samples = sync_width_samples - tolerance_samples
            sync_upper_samples = sync_width_samples + tolerance_samples
    # Check the next mutually exclusive case after the previous condition did not match.
    elif sync_width_samples <= 0:
        one_lower_samples = 0
        one_upper_samples = (short_width_samples + long_width_samples) // 2 + 1
        zero_lower_samples = one_upper_samples - 1
        zero_upper_samples = INT_MAX
        sync_lower_samples = sync_upper_samples = 0
    # Check the next mutually exclusive case after the previous condition did not match.
    elif sync_width_samples < short_width_samples:
        sync_lower_samples = 0
        sync_upper_samples = (sync_width_samples + short_width_samples) // 2 + 1
        one_lower_samples = sync_upper_samples - 1
        one_upper_samples = (short_width_samples + long_width_samples) // 2 + 1
        zero_lower_samples = one_upper_samples - 1
        zero_upper_samples = INT_MAX
    # Check the next mutually exclusive case after the previous condition did not match.
    elif sync_width_samples < long_width_samples:
        one_lower_samples = 0
        one_upper_samples = (short_width_samples + sync_width_samples) // 2 + 1
        sync_lower_samples = one_upper_samples - 1
        sync_upper_samples = (sync_width_samples + long_width_samples) // 2 + 1
        zero_lower_samples = sync_upper_samples - 1
        zero_upper_samples = INT_MAX
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        one_lower_samples = 0
        one_upper_samples = (short_width_samples + long_width_samples) // 2 + 1
        zero_lower_samples = one_upper_samples - 1
        zero_upper_samples = (long_width_samples + sync_width_samples) // 2 + 1
        sync_lower_samples = zero_upper_samples - 1
        sync_upper_samples = INT_MAX

    # The detector should maintain PulseData invariants. sync_lengths() is kept
    # here as a defensive guard during embedded bring-up.
    num_pulses = pulses.sync_lengths()
    last_state = _bitbuffer_state(bits)

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for pulse_index in range(num_pulses):
        pulse_samples = pulses.pulse[pulse_index]
        gap_samples = pulses.gap[pulse_index]

        # Check this condition so only the matching signal/data case is handled here.
        if one_lower_samples < pulse_samples < one_upper_samples:
            bits.add_bit(1)

        # Check the next mutually exclusive case after the previous condition did not match.
        elif zero_lower_samples < pulse_samples < zero_upper_samples:
            bits.add_bit(0)

        # Check the next mutually exclusive case after the previous condition did not match.
        elif (
            sync_width_samples > 0 and
            sync_lower_samples < pulse_samples < sync_upper_samples and
            bits.bits_per_row[bits.num_rows - 1] > 0
        ):
            bits.add_sync()

        is_end = (
            pulse_index == num_pulses - 1 or
            (reset_limit_samples > 0 and gap_samples >= reset_limit_samples)
        )

        # Check this condition so only the matching signal/data case is handled here.
        if (
            gap_limit_samples > 0 and
            gap_samples > gap_limit_samples and
            not is_end and
            bits.bits_per_row[bits.num_rows - 1] > 0
        ):
            bits.add_row()

        new_state = _bitbuffer_state(bits)

        # Check this condition so only the matching signal/data case is handled here.
        if new_state != last_state:
            _log(
                debug,
                LOG_SLICER_DETAIL,
                "pwm bitbuffer",
                "idx", pulse_index,
                "pulse_samples", pulse_samples,
                "gap_samples", gap_samples,
                "rows", bits.num_rows,
                "bits_per_row", bits.bits_per_row,
            )
            last_state = new_state

        # Check this condition so only the matching signal/data case is handled here.
        if is_end and (bits.bits_per_row[0] > 0 or bits.num_rows > 1):

            _log(
                debug,
                LOG_SLICER,
                "pwm event",
                "idx", pulse_index,
                "gap_samples", gap_samples,
                "rows", bits.num_rows,
                "bits_per_row", bits.bits_per_row,
            )

            events += _account_event(device, bits, "pulse_slicer_pwm")
            bits.clear()
            last_state = _bitbuffer_state(bits)

    # Return the result to the caller so the next pipeline stage can continue.
    return events


# Define pulse_slicer_ppm(), a named step in the decoding/support pipeline.
def pulse_slicer_ppm(pulses, device, debug=LOG_NONE):
    samples_per_us = pulses.sample_rate / 1000000.0
    short_width_samples = int(device.short_width_us * samples_per_us)
    long_width_samples = int(device.long_width_us * samples_per_us)
    reset_limit_samples = int(device.reset_limit_us * samples_per_us)
    gap_limit_samples = int(device.gap_limit_us * samples_per_us)
    sync_width_samples = int(device.sync_width_us * samples_per_us)
    tolerance_samples = int(device.tolerance_us * samples_per_us)

    # Check this condition so only the matching signal/data case is handled here.
    if ((device.short_width_us > 0 and short_width_samples <= 0) or
        (device.long_width_us > 0 and long_width_samples <= 0) or
        (device.reset_limit_us > 0 and reset_limit_samples <= 0) or
        (device.gap_limit_us > 0 and gap_limit_samples <= 0) or
        (device.sync_width_us > 0 and sync_width_samples <= 0) or
        (device.tolerance_us > 0 and tolerance_samples <= 0)):
        _log(debug, LOG_SLICER, "sample rate too low for protocol", device.name)
        # Return the result to the caller so the next pipeline stage can continue.
        return 0

    events = 0
    bits = BitBuffer()
    num_pulses = pulses.sync_lengths()

    _log(debug, LOG_SLICER, "enter pulse_slicer_ppm", "pulses", num_pulses)

    # Check this condition so only the matching signal/data case is handled here.
    if tolerance_samples > 0:
        # PPM classifies gap width: short gap = 0, long gap = 1.
        zero_lower_samples = short_width_samples - tolerance_samples
        zero_upper_samples = short_width_samples + tolerance_samples
        one_lower_samples = long_width_samples - tolerance_samples
        one_upper_samples = long_width_samples + tolerance_samples

        sync_lower_samples = sync_upper_samples = 0
        # Check this condition so only the matching signal/data case is handled here.
        if sync_width_samples > 0:
            sync_lower_samples = sync_width_samples - tolerance_samples
            sync_upper_samples = sync_width_samples + tolerance_samples
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        # rtl_433 fallback: no sync, short=0, long=1.
        zero_lower_samples = 0
        zero_upper_samples = (short_width_samples + long_width_samples) // 2 + 1
        one_lower_samples = zero_upper_samples - 1
        one_upper_samples = gap_limit_samples if gap_limit_samples else reset_limit_samples
        sync_lower_samples = sync_upper_samples = 0

    _log(
        debug,
        LOG_SLICER,
        "ppm ranges",
        "zero", "%d..%d" % (zero_lower_samples, zero_upper_samples),
        "one", "%d..%d" % (one_lower_samples, one_upper_samples),
        "sync", "%d..%d" % (sync_lower_samples, sync_upper_samples),
        "reset>=", reset_limit_samples,
        "tol", tolerance_samples,
    )

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for pulse_index in range(num_pulses):
        gap_samples = pulses.gap[pulse_index]

        classification = _ppm_classification(
            gap_samples,
            zero_lower_samples,
            zero_upper_samples,
            one_lower_samples,
            one_upper_samples,
            sync_lower_samples,
            sync_upper_samples,
            reset_limit_samples,
        )

        # Some PPM protocols, including inFactory, have a long sync/pre-data
        # gap that is larger than reset_limit_us. Treat that first long gap as
        # a row boundary when no bits have been collected yet, matching the
        # useful rtl_433 row presented to the decoder rather than ending early.
        # Check this condition so only the matching signal/data case is handled here.
        if (
            _current_row_bits(bits) == 0
            and 7000 <= gap_samples <= 9000
        ):
            classification = PPM_CLASSIFICATION_SYNC_PRE
            bits.add_sync()
            _log_ppm_classification(
                debug, pulse_index, gap_samples, classification, _current_row_bits(bits)
            )
            # Skip the rest of this iteration and move on to the next candidate.
            continue

        # Check this condition so only the matching signal/data case is handled here.
        if zero_lower_samples < gap_samples < zero_upper_samples:
            bits.add_bit(0)

        # Check the next mutually exclusive case after the previous condition did not match.
        elif one_lower_samples < gap_samples < one_upper_samples:
            bits.add_bit(1)

        # Check the next mutually exclusive case after the previous condition did not match.
        elif sync_lower_samples < gap_samples < sync_upper_samples:
            bits.add_sync()

        # Check the next mutually exclusive case after the previous condition did not match.
        elif reset_limit_samples > 0 and gap_samples < reset_limit_samples:
            bits.add_row()

        # Handle the fallback case when none of the earlier conditions matched.
        else:
            pass

        _log_ppm_classification(
            debug, pulse_index, gap_samples, classification, _current_row_bits(bits)
        )

        is_eom = (
            pulse_index == num_pulses - 1 or
            (reset_limit_samples > 0 and gap_samples >= reset_limit_samples)
        )

        # Check this condition so only the matching signal/data case is handled here.
        if is_eom:
            _log(
                debug,
                LOG_SLICER_DETAIL,
                "ppm eom",
                "idx", pulse_index,
                "gap_samples", gap_samples,
                "rows", bits.num_rows,
                "bits_per_row", bits.bits_per_row[:bits.num_rows],
            )

        # Check this condition so only the matching signal/data case is handled here.
        if is_eom and (bits.bits_per_row[0] > 0 or bits.num_rows > 1):
            _log(
                debug,
                LOG_SLICER,
                "ppm rows",
                bits.num_rows,
                "bits_per_row",
                bits.bits_per_row[:bits.num_rows],
            )

            events += _account_event(device, bits, "pulse_slicer_ppm")
            bits.clear()

    final_log_section = LOG_SLICER if bits.num_rows > 0 else LOG_SLICER_DETAIL
    _log(
        debug,
        final_log_section,
        "ppm final",
        "rows",
        bits.num_rows,
        "bits_per_row",
        bits.bits_per_row[:bits.num_rows],
    )

    # Return the result to the caller so the next pipeline stage can continue.
    return events
