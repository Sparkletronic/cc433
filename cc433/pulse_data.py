# -----------------------------------------------------------------------------
# pulse_data.py
# PulseData is the transport object for pulse and gap timing arrays between detector and slicer.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/pulse_data.py
# MicroPython subset of rtl_433 pulse_data.h / pulse_data.c.

PD_MAX_PULSES = 1200 # Protection against runaway memory usage.
PD_MIN_PULSES = 16 # Sanity check before accepting a package.
PD_MIN_PULSE_SAMPLES = 10 # Deglitching.
PD_MAX_GAP_MS = 100 # Safety net. Ignore impossible gaps.
PD_MAX_GAP_RATIO = 10
PD_MAX_PULSE_MS = 100 # Safety net. Ignore impossible widths.


# Define the PulseData class, which groups related state and behavior for this stage.
class PulseData:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, sample_rate=1000000):
        self.offset = 0
        self.sample_rate = sample_rate
        self.depth_bits = 0
        self.start_ago = 0
        self.end_ago = 0
        self.num_pulses = 0
        self.pulse = []
        self.gap = []
        self.ook_low_estimate = 0
        self.ook_high_estimate = 0
        self.fsk_f1_est = 0
        self.fsk_f2_est = 0
        self.freq1_hz = 0.0
        self.freq2_hz = 0.0
        self.centerfreq_hz = 0.0
        self.range_db = 0.0
        self.rssi_db = 0.0
        self.snr_db = 0.0
        self.noise_db = 0.0

    # Define clear(), a named step in the decoding/support pipeline.
    def clear(self):
        sample_rate = self.sample_rate
        self.__init__(sample_rate)

    # Define append(), a named step in the decoding/support pipeline.
    def append(self, pulse_width, gap_width):
        """Append one complete pulse/gap row.

        rtl_433 PulseData stores aligned pulse[n] and gap[n] rows. Keep all
        code on this helper path so num_pulses, pulse[], and gap[] cannot drift
        out of sync.
        """
        # Check this condition so only the matching signal/data case is handled here.
        if self.num_pulses >= PD_MAX_PULSES:
            raise RuntimeError("PulseData full")
        self.pulse.append(int(pulse_width))
        self.gap.append(int(gap_width))
        self.num_pulses += 1

    # Define pop(), a named step in the decoding/support pipeline.
    def pop(self):
        """Remove and return the last complete pulse/gap row."""
        # Check this condition so only the matching signal/data case is handled here.
        if self.num_pulses <= 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return 0, 0
        self.num_pulses -= 1
        pulse_width = self.pulse.pop() if self.pulse else 0
        gap_width = self.gap.pop() if self.gap else 0
        # Return the result to the caller so the next pipeline stage can continue.
        return pulse_width, gap_width

    # Define sync_lengths(), a named step in the decoding/support pipeline.
    def sync_lengths(self):
        """Defensively restore aligned row lengths.

        This should normally be a no-op. It is intentionally available during
        embedded bring-up so diagnostic code can protect the slicer from stale
        experimental PulseData objects.
        """
        n = min(self.num_pulses, len(self.pulse), len(self.gap))
        self.num_pulses = n
        # Check this condition so only the matching signal/data case is handled here.
        if len(self.pulse) != n:
            self.pulse = self.pulse[:n]
        # Check this condition so only the matching signal/data case is handled here.
        if len(self.gap) != n:
            self.gap = self.gap[:n]
        # Return the result to the caller so the next pipeline stage can continue.
        return n

    # Define assert_invariants(), a named step in the decoding/support pipeline.
    def assert_invariants(self):
        # Check this condition so only the matching signal/data case is handled here.
        if self.num_pulses != len(self.pulse) or self.num_pulses != len(self.gap):
            raise AssertionError("PulseData invariant failed")

    # Define shift(), a named step in the decoding/support pipeline.
    def shift(self):
        # rtl_433 shifts out half the fixed array and increments offset by offs.
        offs = PD_MAX_PULSES // 2
        # Check this condition so only the matching signal/data case is handled here.
        if self.num_pulses <= offs:
            self.clear()
            # Return the result to the caller so the next pipeline stage can continue.
            return
        self.pulse = self.pulse[offs:]
        self.gap = self.gap[offs:]
        self.num_pulses -= offs
        self.offset += offs

    # Define dump(), a named step in the decoding/support pipeline.
    def dump(self):
        print("Pulse data: %u pulses" % self.num_pulses)
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for n in range(self.num_pulses):
            p = self.pulse[n]
            g = self.gap[n]
            print("[%3u] Pulse: %4d, Gap: %4d, Period: %4d" % (n, p, g, p + g))
