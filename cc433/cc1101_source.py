# -----------------------------------------------------------------------------
# cc1101_source.py
# CC1101 capture source helpers that adapt radio edge data into the project capture interface.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/cc1101_source.py
# Receiver-specific hook for CC1101 async OOK.
# This module is intentionally outside the rtl_433-like demod/device core.

from .pulse_data import PulseData
from .pulse_detect import PulseDetect
from .pulse_slicer import CC1101_ASYNC_OOK_PROFILE


# Define the CC1101AsyncOOKSource class, which groups related state and behavior for this stage.
class CC1101AsyncOOKSource:
    """Thin wrapper around the user's CC1101Radio driver.

    The rtl_433-like core starts at PulseData or sampled envelope data. This
    # Define the only configures and starts the CC1101 in async OOK mode, then provides class, which groups related state and behavior for this stage.
    class only configures and starts the CC1101 in async OOK mode, then provides
    conversions for already-captured GDO0 data. It does not decode protocols.
    """

    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, radio, sample_rate=1000000):
        self.radio = radio
        self.sample_rate = sample_rate

    # Define configure(), a named step in the decoding/support pipeline.
    def configure(self, device=None, rx_bw_khz=None, data_rate_kbps=None):
        """Configure CC1101 acquisition using device-profile frontend settings.

        rx_bw_khz/data_rate_kbps remain accepted as explicit overrides for
        manual experiments. When a device is supplied, its CC1101 profile is
        used so acquisition tuning can vary per device without changing
        rtl_433 protocol metadata.
        """
        profile = getattr(device, "cc1101_profile", CC1101_ASYNC_OOK_PROFILE)
        bw = rx_bw_khz if rx_bw_khz is not None else getattr(device, "cc1101_rx_bw_khz", 270)
        dr = data_rate_kbps if data_rate_kbps is not None else getattr(device, "cc1101_data_rate_kbps", 3.79)

        # Check this condition so only the matching signal/data case is handled here.
        if profile == CC1101_ASYNC_OOK_PROFILE:
            # Check this condition so only the matching signal/data case is handled here.
            if hasattr(self.radio, "configure_cc1101_async_ook"):
                self.radio.configure_cc1101_async_ook(
                    rx_bw_khz=bw,
                    data_rate_kbps=dr,
                    registers=getattr(device, "cc1101_registers", None),
                )
            # Handle the fallback case when none of the earlier conditions matched.
            else:
                self.radio.configure_async_ook_43392(rx_bw_khz=bw, data_rate_kbps=dr)
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            self.radio.configure_async_ook_43392(rx_bw_khz=bw, data_rate_kbps=dr)

    # Define start_rx(), a named step in the decoding/support pipeline.
    def start_rx(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return self.radio.start_rx()

    # Define recover_rx(), a named step in the decoding/support pipeline.
    def recover_rx(self):
        self.radio.recover_rx()

    # Define widths_to_pulse_data(), a named step in the decoding/support pipeline.
    def widths_to_pulse_data(self, widths, starts_high=True):
        # Return the result to the caller so the next pipeline stage can continue.
        return widths_to_pulse_data(widths, starts_high, self.sample_rate)

    # Define edges_to_pulse_data(), a named step in the decoding/support pipeline.
    def edges_to_pulse_data(self, edges, pulse_level=0, max_gap_us=10000):
        # Return the result to the caller so the next pipeline stage can continue.
        return edges_to_pulse_data(edges, pulse_level, self.sample_rate, max_gap_us)

    # Define capture_edges_poll(), a named step in the decoding/support pipeline.
    def capture_edges_poll(self, duration_ms=5000, max_edges=600):
        # Return the result to the caller so the next pipeline stage can continue.
        return capture_edges_poll(self.radio, duration_ms, max_edges)

    # Define edges_to_envelope(), a named step in the decoding/support pipeline.
    def edges_to_envelope(self, edges, pulse_level=0, high=5000, low=50,
                          lead_in_us=2000, max_samples=60000):
        # Return the result to the caller so the next pipeline stage can continue.
        return edges_to_envelope(edges, pulse_level, high, low, lead_in_us, max_samples)

    # Define edges_to_pulses_via_detector(), a named step in the decoding/support pipeline.
    def edges_to_pulses_via_detector(self, edges, pulse_level=0, high=5000,
                                     low=50, lead_in_us=2000, max_samples=60000):
        env = self.edges_to_envelope(edges, pulse_level, high, low, lead_in_us, max_samples)
        det = PulseDetect()
        # Return the result to the caller so the next pipeline stage can continue.
        return det.package(env, sample_rate=self.sample_rate, sample_offset=0)


# Define capture_edges_poll(), a named step in the decoding/support pipeline.
def capture_edges_poll(radio, duration_ms=5000, max_edges=600):
    """Poll CC1101 GDO0 and return (level, duration_us) edge durations.

    This is a smoke-test capture path only. It can miss edges under MicroPython
    load; a PIO capture source should replace it for serious captures.
    """
    import time

    out = []
    last = radio.gdo0_state()
    last_t = time.ticks_us()
    start = time.ticks_ms()

    # Continue looping while the runtime condition says more capture or processing work remains.
    while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
        # Check this condition so only the matching signal/data case is handled here.
        if max_edges is not None and len(out) >= max_edges:
            # Stop this loop because the current package or condition is complete.
            break
        now = radio.gdo0_state()
        # Check this condition so only the matching signal/data case is handled here.
        if now != last:
            t = time.ticks_us()
            out.append((last, time.ticks_diff(t, last_t)))
            last = now
            last_t = t

    # Return the result to the caller so the next pipeline stage can continue.
    return out


# Define edges_to_pulse_data(), a named step in the decoding/support pipeline.
def edges_to_pulse_data(edges, pulse_level=0, sample_rate=1000000, max_gap_us=10000):
    """Convert (level, duration_us) edges directly into PulseData.

    This bypasses PulseDetect and is useful for inspecting receiver polarity and
    raw timing. On the current CC1101 async OOK path, Acurite pulses appear as
    level 0 durations, so pulse_level=0 is the default.
    """
    pd = PulseData(sample_rate=sample_rate)
    pending_pulse = None

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for level, dur in edges:
        # Check this condition so only the matching signal/data case is handled here.
        if dur > max_gap_us:
            pending_pulse = None
            # Skip the rest of this iteration and move on to the next candidate.
            continue

        # Check this condition so only the matching signal/data case is handled here.
        if level == pulse_level:
            pending_pulse = dur
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            # Check this condition so only the matching signal/data case is handled here.
            if pending_pulse is not None:
                pd.append(pending_pulse, dur)
                pending_pulse = None

    # Return the result to the caller so the next pipeline stage can continue.
    return pd


# Define widths_to_pulse_data(), a named step in the decoding/support pipeline.
def widths_to_pulse_data(widths, starts_high=True, sample_rate=1000000):
    """Convert alternating high/low GDO widths into rtl_433-style PulseData.

    This bypasses pulse_detect.py and is retained only for low-level manual
    inspection. For rtl_433-like testing, prefer edges_to_envelope() followed by
    PulseDetect.package().
    """
    pd = PulseData(sample_rate)
    i = 0 if starts_high else 1
    # Continue looping while the runtime condition says more capture or processing work remains.
    while i + 1 < len(widths):
        pd.append(widths[i], widths[i + 1])
        i += 2
    # Return the result to the caller so the next pipeline stage can continue.
    return pd


# Define edges_to_envelope(), a named step in the decoding/support pipeline.
def edges_to_envelope(edges, pulse_level=0, high=5000, low=50,
                      lead_in_us=2000, max_samples=60000):
    """Convert (level, duration_us) GDO0 edges to a sampled OOK envelope.

    This is the CC1101-specific boundary. rtl_433 consumes envelope samples;
    CC1101 GDO0 gives already-sliced logic levels. This function reconstructs a
    simple envelope stream so PulseDetect can still own pulse/gap construction.

    On the user's current CC1101 setup, Acurite OOK pulses appeared active-low,
    so pulse_level=0 is the useful default for that receiver path.
    """
    total = lead_in_us
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for _level, dur in edges:
        total += dur
        # Check this condition so only the matching signal/data case is handled here.
        if total > max_samples:
            total = max_samples
            # Stop this loop because the current package or condition is complete.
            break

    env = [low] * total
    pos = lead_in_us
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for level, dur in edges:
        value = high if level == pulse_level else low
        end = pos + dur
        # Check this condition so only the matching signal/data case is handled here.
        if end > total:
            end = total
        # Continue looping while the runtime condition says more capture or processing work remains.
        while pos < end:
            env[pos] = value
            pos += 1
        # Check this condition so only the matching signal/data case is handled here.
        if pos >= total:
            # Stop this loop because the current package or condition is complete.
            break
    # Return the result to the caller so the next pipeline stage can continue.
    return env
