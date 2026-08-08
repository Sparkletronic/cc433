# -----------------------------------------------------------------------------
# synthetic.py
# Synthetic helpers build fake pulse streams so the decoder can be tested without real RF hardware.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/synthetic.py
# Small MicroPython test helpers for validating the rtl_433-style pipeline.
# These are not part of rtl_433; they only create controlled test input.

from .pulse_detect import PulseDetect
from .pulse_slicer import Device, pulse_slicer_pwm


# Define make_envelope_from_pairs(), a named step in the decoding/support pipeline.
def make_envelope_from_pairs(pairs, high=5000, low=50, lead_in_us=2000):
    """Build a 1 MHz synthetic OOK envelope from (pulse_us, gap_us) pairs.

    This preallocates the list to avoid repeated reallocations on MicroPython.
    """
    total = lead_in_us
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for pulse_us, gap_us in pairs:
        total += pulse_us + gap_us

    env = [low] * total
    pos = lead_in_us
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for pulse_us, gap_us in pairs:
        end = pos + pulse_us
        # Continue looping while the runtime condition says more capture or processing work remains.
        while pos < end:
            env[pos] = high
            pos += 1
        pos += gap_us
    # Return the result to the caller so the next pipeline stage can continue.
    return env


# Define bits_to_pwm_pairs(), a named step in the decoding/support pipeline.
def bits_to_pwm_pairs(bits, short_us=220, long_us=408, sync_us=620,
                      sync_gap_us=620, reset_gap_us=20000,
                      add_sync=True, add_reset=True):
    """Encode bits using rtl_433 PWM semantics: short pulse=1, long pulse=0."""
    pairs = []
    # Check this condition so only the matching signal/data case is handled here.
    if add_sync:
        pairs.append((sync_us, sync_gap_us))

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for bit in bits:
        # Check this condition so only the matching signal/data case is handled here.
        if bit == "1" or bit == 1:
            pairs.append((short_us, long_us))
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            pairs.append((long_us, short_us))

    # Check this condition so only the matching signal/data case is handled here.
    if add_reset:
        # This intentionally adds a final short pulse before the package-ending
        # long gap, matching how sampled OOK packages often terminate. The PWM
        # slicer will see that final pulse as one extra 1 bit.
        pairs.append((short_us, reset_gap_us))
    # Return the result to the caller so the next pipeline stage can continue.
    return pairs


# Define debug_acurite_device(), a named step in the decoding/support pipeline.
def debug_acurite_device():
    # Return the result to the caller so the next pipeline stage can continue.
    return Device(
        name="Acurite 6045M debug",
        short_width_us=220,
        long_width_us=408,
        decode_fn=None,
        gap_limit_us=500,
        reset_limit_us=4000,
        sync_width_us=620,
        tolerance_us=0,
    )


# Define run_synthetic_pwm(), a named step in the decoding/support pipeline.
def run_synthetic_pwm(bits="101010101100110011110000"):
    """Run a known bit pattern through PulseDetect -> PulseData -> PWM slicer."""
    pairs = bits_to_pwm_pairs(bits)
    det = PulseDetect()
    status, pulses = det.package(
        envelope_data=make_envelope_from_pairs(pairs),
        sample_rate=1000000,
        sample_offset=0,
    )
    print("status:", status)
    pulses.dump()
    events = pulse_slicer_pwm(pulses, debug_acurite_device())
    print("events:", events)
    # Return the result to the caller so the next pipeline stage can continue.
    return status, pulses, events


# Define run_capture_vector_01(), a named step in the decoding/support pipeline.
def run_capture_vector_01(use_acurite_decoder=False):
    """Run the canonical CC1101 PulseData capture through PWM slicer.

    With use_acurite_decoder=False, this prints bitbuffer rows for inspection.
    With True, it uses the Acurite 6045M device decoder.
    """
    from .test_vectors.acurite_cc1101_capture_01 import make_pulse_data
    # Check this condition so only the matching signal/data case is handled here.
    if use_acurite_decoder:
        from .devices.acurite import make_acurite_6045m_device
        device = make_acurite_6045m_device()
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        device = debug_acurite_device()

    pulses = make_pulse_data()
    print("capture vector pulses:", pulses.num_pulses)
    events = pulse_slicer_pwm(pulses, device)
    print("events:", events)
    # Return the result to the caller so the next pipeline stage can continue.
    return pulses, events
