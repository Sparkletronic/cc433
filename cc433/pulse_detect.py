# -----------------------------------------------------------------------------
# pulse_detect.py
# Pulse detector groups raw edge timings into complete OOK pulse packages before bit slicing.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/pulse_detect.py
# Start a protected block because this operation may not be available on every runtime.
try:
    from micropython import const
# Handle the error path without crashing the capture or test run.
except ImportError:
    const = lambda x: x

# MicroPython OOK-only subset of rtl_433 pulse_detect.c.
# Source model: pulse_detect_package() OOK branch. FSK is intentionally omitted.

from .pulse_data import (
    PulseData,
    PD_MAX_PULSES,
    PD_MIN_PULSES,
    PD_MIN_PULSE_SAMPLES,
    PD_MAX_GAP_MS,
    PD_MAX_GAP_RATIO,
)
from .baseband import (
    db_to_amp,
    db_to_mag,
    db_to_amp_f,
    db_to_mag_f,
    OOK_MAX_HIGH_LEVEL,
)

PD_OOK_STATE_IDLE = 0
PD_OOK_STATE_PULSE = 1
PD_OOK_STATE_GAP_START = 2
PD_OOK_STATE_GAP = 3

OOK_EST_HIGH_RATIO = 64
OOK_EST_LOW_RATIO = 1024

FSK_PULSE_DETECT_OLD = 0
FSK_PULSE_DETECT_NEW = 1
FSK_PULSE_DETECT_AUTO = 2

PULSE_DATA_OOK = 1
PULSE_DATA_FSK = 2

PD_EDGE_LEAD_IN_SAMPLES = OOK_EST_LOW_RATIO
PD_EDGE_LEAD_IN_MAX_SAMPLES = OOK_EST_LOW_RATIO + 1

PD_MIN_GAP_MS = 10

# ============================================================
# DEBUG LEVELS
# ============================================================

from .debug import (
    LOG_NONE,
    LOG_DETECT,
    LOG_EOP,
    LOG_FRAMING,
    LOG_FRAMING_DETAIL,
    coerce_debug,
    log_enabled,
    log,
)

PD_EDGE_MAX_START_PULSE_SAMPLES = 3000
PD_EDGE_MAX_START_GAP_SAMPLES = 3000
PD_EDGE_MAX_TRACKED_PULSE_SAMPLES = 3000

PD_EDGE_MIN_START_PULSE_SAMPLES = 150
PD_EDGE_MIN_START_GAP_SAMPLES   = 150

PD_SKIP_REASON_LEAD_IN_NOT_READY = "lead_in_not_ready"
PD_SKIP_REASON_START_PULSE_TOO_SHORT = "start_pulse_too_short"
PD_SKIP_REASON_START_PULSE_TOO_LONG = "start_pulse_too_long"
PD_SKIP_REASON_START_PULSE_TOO_LONG_DURING_START = "start_pulse_too_long_during_start"
PD_SKIP_REASON_START_GAP_TOO_LONG = "start_gap_too_long"
PD_SKIP_REASON_START_GAP_RESET = "start_gap_reset"

# Define c_div(), a named step in the decoding/support pipeline.
def c_div(n, d):
    """C99-style integer division truncated toward zero."""
    # Check this condition so only the matching signal/data case is handled here.
    if n >= 0:
        # Return the result to the caller so the next pipeline stage can continue.
        return n // d
    # Return the result to the caller so the next pipeline stage can continue.
    return -((-n) // d)


# Define pulse_detect_create(), a named step in the decoding/support pipeline.
def pulse_detect_create():
    """rtl_433-name compatibility helper."""
    # Return the result to the caller so the next pipeline stage can continue.
    return PulseDetect()


# Define pulse_detect_reset(), a named step in the decoding/support pipeline.
def pulse_detect_reset(pulse_detect):
    """rtl_433-name compatibility helper."""
    pulse_detect.reset()


# Define pulse_detect_set_levels(), a named step in the decoding/support pipeline.
def pulse_detect_set_levels(pulse_detect, use_mag_est=False, fixed_high_level=0.0,
                            min_high_level=-12.1442, high_low_ratio=9.0, verbosity=0):
    """rtl_433-name compatibility helper."""
    pulse_detect.set_levels(use_mag_est, fixed_high_level, min_high_level, high_low_ratio, verbosity)


# Define pulse_detect_package(), a named step in the decoding/support pipeline.
def pulse_detect_package(pulse_detect, envelope_data, fm_data=None, length=None,
                         sample_rate=1000000, sample_offset=0,
                         pulses=None, fsk_pulses=None, fpdm=FSK_PULSE_DETECT_NEW):
    """rtl_433-name compatibility wrapper around PulseDetect.package()."""
    # Check this condition so only the matching signal/data case is handled here.
    if length is not None:
        envelope_data = envelope_data[:length]
        # Check this condition so only the matching signal/data case is handled here.
        if fm_data is not None:
            fm_data = fm_data[:length]
    # Return the result to the caller so the next pipeline stage can continue.
    return pulse_detect.package(envelope_data, fm_data, sample_rate, sample_offset,
                                pulses, fsk_pulses, fpdm)


# Define the PulseDetect class, which groups related state and behavior for this stage.
class PulseDetect:
    """Stateful OOK pulse detector mirroring rtl_433 pulse_detect_t.

    This consumes sampled amplitude/magnitude envelope values. It is not a
    direct edge-duration decoder. For CC1101 GDO0 edge captures, use
    PulseDetectEdges below; both classes intentionally expose package()-style
    chunk/drain behavior.
    """

    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, use_mag_est=False, fixed_high_level=0.0,
                 min_high_level=-12.1442, high_low_ratio=9.0, verbosity=0,
                 debug=LOG_NONE):
        self.debug = coerce_debug(debug)
        self.set_levels(use_mag_est, fixed_high_level, min_high_level, high_low_ratio, verbosity)
        self.reset()

    # Define set_levels(), a named step in the decoding/support pipeline.
    def set_levels(self, use_mag_est=False, fixed_high_level=0.0,
                   min_high_level=-12.1442, high_low_ratio=9.0, verbosity=0):
        self.use_mag_est = 1 if use_mag_est else 0
        # Check this condition so only the matching signal/data case is handled here.
        if self.use_mag_est:
            self.ook_fixed_high_level = db_to_mag(fixed_high_level) if fixed_high_level < 0.0 else 0
            self.ook_min_high_level = db_to_mag(min_high_level)
            self.ook_high_low_ratio = db_to_mag_f(high_low_ratio)
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            self.ook_fixed_high_level = db_to_amp(fixed_high_level) if fixed_high_level < 0.0 else 0
            self.ook_min_high_level = db_to_amp(min_high_level)
            self.ook_high_low_ratio = db_to_amp_f(high_low_ratio)
        self.verbosity = verbosity

    # Define _log(), a named step in the decoding/support pipeline.
    def _log(self, level, *args):
        log("[PulseDetect]", self.debug, level, *args)

    # Define reset(), a named step in the decoding/support pipeline.
    def reset(self):
        self.ook_state = PD_OOK_STATE_IDLE
        self.pulse_length = 0
        self.max_pulse = 0
        self.data_counter = 0
        self.lead_in_counter = 0
        self.ook_low_estimate = 0
        self.ook_high_estimate = 0

    # Define package(), a named step in the decoding/support pipeline.
    def package(self, envelope_data, fm_data=None, sample_rate=1000000,
                sample_offset=0, pulses=None, fsk_pulses=None, fpdm=FSK_PULSE_DETECT_NEW):

        # Check this condition so only the matching signal/data case is handled here.
        if pulses is None:
            pulses = PulseData(sample_rate)
        # Check this condition so only the matching signal/data case is handled here.
        if fsk_pulses is None:
            fsk_pulses = PulseData(sample_rate)
        # Check this condition so only the matching signal/data case is handled here.
        if fm_data is None:
            fm_data = [0] * len(envelope_data)

        length = len(envelope_data)
        samples_per_millisecond = sample_rate // 1000
        self.ook_high_estimate = max(self.ook_high_estimate, self.ook_min_high_level)

        # Check this condition so only the matching signal/data case is handled here.
        if self.data_counter == 0:
            pulses.start_ago += length
            fsk_pulses.start_ago += length

        eop_on_spurious = 0

        # Continue looping while the runtime condition says more capture or processing work remains.
        while self.data_counter < length:
            am_n = int(envelope_data[self.data_counter])
            ook_threshold = (self.ook_low_estimate + min(self.ook_high_estimate, OOK_MAX_HIGH_LEVEL)) // 2
            # Check this condition so only the matching signal/data case is handled here.
            if self.ook_fixed_high_level != 0:
                ook_threshold = self.ook_fixed_high_level
            ook_hysteresis = ook_threshold // 8

            # Check this condition so only the matching signal/data case is handled here.
            if self.ook_state == PD_OOK_STATE_IDLE:
                # Check this condition so only the matching signal/data case is handled here.
                if am_n > (ook_threshold + ook_hysteresis) and self.lead_in_counter > OOK_EST_LOW_RATIO:
                    pulses.clear()
                    fsk_pulses.clear()
                    pulses.sample_rate = sample_rate
                    fsk_pulses.sample_rate = sample_rate
                    pulses.offset = sample_offset + self.data_counter
                    fsk_pulses.offset = sample_offset + self.data_counter
                    pulses.start_ago = length - self.data_counter
                    fsk_pulses.start_ago = length - self.data_counter
                    self.pulse_length = 0
                    self.max_pulse = 0
                    self.ook_state = PD_OOK_STATE_PULSE
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    ook_low_delta = am_n - self.ook_low_estimate
                    self.ook_low_estimate += c_div(ook_low_delta, OOK_EST_LOW_RATIO)
                    self.ook_low_estimate += 1 if ook_low_delta > 0 else -1
                    self.ook_high_estimate = self.ook_high_low_ratio * self.ook_low_estimate
                    self.ook_high_estimate = max(self.ook_high_estimate, self.ook_min_high_level)
                    # Check this condition so only the matching signal/data case is handled here.
                    if self.lead_in_counter <= OOK_EST_LOW_RATIO:
                        self.lead_in_counter += 1

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_PULSE:
                self.pulse_length += 1
                # Check this condition so only the matching signal/data case is handled here.
                if am_n < (ook_threshold - ook_hysteresis):
                    # Check this condition so only the matching signal/data case is handled here.
                    if self.pulse_length < PD_MIN_PULSE_SAMPLES:
                        # Check this condition so only the matching signal/data case is handled here.
                        if pulses.num_pulses <= 1:
                            self.ook_state = PD_OOK_STATE_IDLE
                        # Handle the fallback case when none of the earlier conditions matched.
                        else:
                            eop_on_spurious = 1
                            self.ook_state = PD_OOK_STATE_GAP
                    # Handle the fallback case when none of the earlier conditions matched.
                    else:
                        # Check this condition so only the matching signal/data case is handled here.
                        if pulses.num_pulses == len(pulses.pulse):
                            pulses.pulse.append(self.pulse_length)
                            pulses.gap.append(0)
                        # Handle the fallback case when none of the earlier conditions matched.
                        else:
                            pulses.pulse[pulses.num_pulses] = self.pulse_length
                            # Check this condition so only the matching signal/data case is handled here.
                            if pulses.num_pulses == len(pulses.gap):
                                pulses.gap.append(0)
                            # Handle the fallback case when none of the earlier conditions matched.
                            else:
                                pulses.gap[pulses.num_pulses] = 0
                        self.max_pulse = max(self.pulse_length, self.max_pulse)
                        self.pulse_length = 0
                        self.ook_state = PD_OOK_STATE_GAP_START
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    self.ook_high_estimate += c_div(am_n, OOK_EST_HIGH_RATIO) - c_div(self.ook_high_estimate, OOK_EST_HIGH_RATIO)
                    self.ook_high_estimate = max(self.ook_high_estimate, self.ook_min_high_level)
                    pulses.fsk_f1_est += c_div(int(fm_data[self.data_counter]), OOK_EST_HIGH_RATIO) - c_div(pulses.fsk_f1_est, OOK_EST_HIGH_RATIO)

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_GAP_START:
                self.pulse_length += 1

                # Check this condition so only the matching signal/data case is handled here.
                if am_n > (ook_threshold + ook_hysteresis):

                    # Check this condition so only the matching signal/data case is handled here.
                    if log_enabled(self.debug, LOG_DETECT):
                        self._log(
                            LOG_DETECT,
                            "gap_start->pulse",
                            "pulse_length", self.pulse_length
                        )

                    self.pulse_length += pulses.pulse[pulses.num_pulses]
                    self.ook_state = PD_OOK_STATE_PULSE

                # Check the next mutually exclusive case after the previous condition did not match.
                elif self.pulse_length >= PD_MIN_PULSE_SAMPLES:

                    # Check this condition so only the matching signal/data case is handled here.
                    if log_enabled(self.debug, LOG_DETECT):
                        self._log(
                            LOG_DETECT,
                            "gap_start->gap",
                            "pulse_length", self.pulse_length
                        )

                    self.ook_state = PD_OOK_STATE_GAP

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_GAP:
                self.pulse_length += 1
                # Check this condition so only the matching signal/data case is handled here.
                if am_n > (ook_threshold + ook_hysteresis):
                    # Check this condition so only the matching signal/data case is handled here.
                    if pulses.num_pulses == len(pulses.gap):
                        pulses.gap.append(self.pulse_length)
                    # Handle the fallback case when none of the earlier conditions matched.
                    else:
                        pulses.gap[pulses.num_pulses] = self.pulse_length
                    pulses.num_pulses += 1

                    # Check this condition so only the matching signal/data case is handled here.
                    if pulses.num_pulses >= PD_MAX_PULSES:
                        self.ook_state = PD_OOK_STATE_IDLE
                        pulses.ook_low_estimate = self.ook_low_estimate
                        pulses.ook_high_estimate = self.ook_high_estimate
                        pulses.end_ago = length - self.data_counter
                        # Return the result to the caller so the next pipeline stage can continue.
                        return PULSE_DATA_OOK, pulses

                    self.pulse_length = 0
                    self.ook_state = PD_OOK_STATE_PULSE

                # Check this condition so only the matching signal/data case is handled here.
                if (eop_on_spurious or
                    (self.pulse_length > (PD_MAX_GAP_RATIO * self.max_pulse) and
                     self.pulse_length > (PD_MIN_GAP_MS * samples_per_millisecond)) or
                    self.pulse_length > (PD_MAX_GAP_MS * samples_per_millisecond)):
                    # Check this condition so only the matching signal/data case is handled here.
                    if pulses.num_pulses == len(pulses.gap):
                        pulses.gap.append(self.pulse_length)
                    # Handle the fallback case when none of the earlier conditions matched.
                    else:
                        pulses.gap[pulses.num_pulses] = self.pulse_length
                    pulses.num_pulses += 1
                    self.ook_state = PD_OOK_STATE_IDLE
                    pulses.ook_low_estimate = self.ook_low_estimate
                    pulses.ook_high_estimate = self.ook_high_estimate
                    pulses.end_ago = length - self.data_counter
                    # Return the result to the caller so the next pipeline stage can continue.
                    return PULSE_DATA_OOK, pulses

            # Handle the fallback case when none of the earlier conditions matched.
            else:
                self.ook_state = PD_OOK_STATE_IDLE

            self.data_counter += 1

        self.data_counter = 0
        # Return the result to the caller so the next pipeline stage can continue.
        return 0, pulses



# Define the PulseDetectEdges class, which groups related state and behavior for this stage.
class PulseDetectEdges:
    """Digital-edge OOK package detector for CC1101 async GDO0.

    rtl_433's pulse_detect_package() receives sampled envelope values and builds
    PulseData while doing thresholding, short-pulse rejection, short-gap merge,
    max-pulse tracking, and end-of-package detection. CC1101 async GDO0 has
    already thresholded the envelope into a logic level, so this class consumes
    edge durations instead of amplitude samples but preserves the same pipeline
    role and package()-style chunking.

    Important invariant for the edge path:
        PulseData rows are appended only when a complete pulse/gap pair exists.

    This avoids fragile half-row bookkeeping where num_pulses, pulse[], and
    gap[] can drift out of sync.
    """

    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, pulse_level=1, sample_rate=1000000,
                 device=None, debug=LOG_NONE):
        self.pulse_level = pulse_level
        self.sample_rate = sample_rate
        self._device = device
        self.debug = coerce_debug(debug)
        self.reset()

    # Define reset(), a named step in the decoding/support pipeline.
    def reset(self):
        self.ook_state = PD_OOK_STATE_IDLE
        self.pulse_length = 0
        self.gap_length = 0
        self.pending_pulse = 0
        self.max_pulse_samples = 0

        self.largest_gap_seen = 0
        self.second_largest_gap_seen = 0

        self.current_offset = 0
        self._pulses = PulseData(self.sample_rate)
        self._eop_on_spurious = 0
        self.start_pulse = 0
        self.lead_in_counter = 0
        
        self.consumed_edges = 0

    # Define _log(), a named step in the decoding/support pipeline.
    def _log(self, level, *args):
        log("[PulseDetectEdges]", self.debug, level, *args)

    # Define _log_start_reject(), a named step in the decoding/support pipeline.
    def _log_start_reject(self, level, skip_reason, **fields):
        args = ["start reject", "reject_reason", skip_reason]
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for name, value in fields.items():
            args.extend((name, value))
        self._log(level, *args)

    # Define _lead_in_ready(), a named step in the decoding/support pipeline.
    def _lead_in_ready(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return self.lead_in_counter > PD_EDGE_LEAD_IN_SAMPLES

    # Define _lead_in_enabled(), a named step in the decoding/support pipeline.
    def _lead_in_enabled(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return getattr(self._device, "enable_lead_in", True)

    # Define _add_idle_lead_in(), a named step in the decoding/support pipeline.
    def _add_idle_lead_in(self, duration_samples):
        # Check this condition so only the matching signal/data case is handled here.
        if duration_samples <= 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return
        self.lead_in_counter += duration_samples
        # Check this condition so only the matching signal/data case is handled here.
        if self.lead_in_counter > PD_EDGE_LEAD_IN_MAX_SAMPLES:
            self.lead_in_counter = PD_EDGE_LEAD_IN_MAX_SAMPLES

    # Define _clear_lead_in_on_activity(), a named step in the decoding/support pipeline.
    def _clear_lead_in_on_activity(self):
        self.lead_in_counter = 0

    # Define observe_idle(), a named step in the decoding/support pipeline.
    def observe_idle(self, duration_us, sample_rate=None):
        # Check this condition so only the matching signal/data case is handled here.
        if sample_rate is None:
            sample_rate = self.sample_rate
        duration_samples = self._us_to_samples(duration_us, sample_rate)
        self._add_idle_lead_in(duration_samples)
        self._log(LOG_DETECT, "lead-in idle",
                  "duration_samples", duration_samples,
                  "counter", self.lead_in_counter)

    # Define _track_gap(), a named step in the decoding/support pipeline.
    def _track_gap(self, gap_len_samples):
        # Check this condition so only the matching signal/data case is handled here.
        if gap_len_samples > self.largest_gap_seen:
            self.second_largest_gap_seen = self.largest_gap_seen
            self.largest_gap_seen = gap_len_samples
        # Check the next mutually exclusive case after the previous condition did not match.
        elif gap_len_samples > self.second_largest_gap_seen:
            self.second_largest_gap_seen = gap_len_samples

    # Define _us_to_samples(), a named step in the decoding/support pipeline.
    def _us_to_samples(self, duration_us, sample_rate):
        # Check this condition so only the matching signal/data case is handled here.
        if sample_rate == 1000000:
            # Return the result to the caller so the next pipeline stage can continue.
            return int(duration_us)
        # Return the result to the caller so the next pipeline stage can continue.
        return int((int(duration_us) * sample_rate + 500000) // 1000000)

    # Define _track_max_pulse(), a named step in the decoding/support pipeline.
    def _track_max_pulse(self, pulse_len_samples):
        """Track max pulse for EOP without letting edge-source junk poison it.

        rtl_433's sampled-envelope detector obtains max_pulse_samples after amplitude
        qualification. The CC1101 edge adapter can see long idle/chatter spans
        as pulse-level durations. Keep those rows in PulseData for diagnostics,
        but do not let them disable normal long-gap EOP detection.
        """
        # Check this condition so only the matching signal/data case is handled here.
        if pulse_len_samples <= 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return
        # Check this condition so only the matching signal/data case is handled here.
        if pulse_len_samples > PD_EDGE_MAX_TRACKED_PULSE_SAMPLES:
            self._log(LOG_DETECT, "max_pulse_samples ignore",
                      "pulse", pulse_len_samples,
                      "limit", PD_EDGE_MAX_TRACKED_PULSE_SAMPLES,
                      "current", self.max_pulse_samples)
            # Return the result to the caller so the next pipeline stage can continue.
            return
        # Check this condition so only the matching signal/data case is handled here.
        if pulse_len_samples > self.max_pulse_samples:
            old = self.max_pulse_samples
            self.max_pulse_samples = pulse_len_samples
            self._log(LOG_DETECT, "max_pulse_samples update", old, "->", self.max_pulse_samples)

    # Define _append_pair(), a named step in the decoding/support pipeline.
    def _append_pair(self, pulses, pulse_len_samples, gap_len_samples):
        """Append one complete rtl_433 PulseData row."""
        # Check this condition so only the matching signal/data case is handled here.
        if pulse_len_samples <= 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return
        self._track_gap(int(gap_len_samples))
        pulses.append(int(pulse_len_samples), int(gap_len_samples))
        self._log(LOG_DETECT, "append pair",
                  "idx", pulses.num_pulses - 1,
                  "pulse", int(pulse_len_samples),
                  "gap", int(gap_len_samples))
        self._track_max_pulse(int(pulse_len_samples))

    # Define _merge_short_gap_into_pulse(), a named step in the decoding/support pipeline.
    def _merge_short_gap_into_pulse(self, duration_samples):
        """A short gap followed by a pulse is treated as pulse continuation."""
        self.pulse_length = self.pending_pulse + self.gap_length + duration_samples
        self.pending_pulse = 0
        self.gap_length = 0
        self.ook_state = PD_OOK_STATE_PULSE

    # Define _finish_package(), a named step in the decoding/support pipeline.
    def _finish_package(self, pulses, length_remaining=0, reason="eop"):
        self._log(LOG_FRAMING_DETAIL | LOG_DETECT, "finish package", reason,
                  "num_pulses", pulses.num_pulses,
                  "max_pulse_samples", self.max_pulse_samples,
                  "largest_gap", self.largest_gap_seen,
                  "second_gap", self.second_largest_gap_seen,
                  "end_ago", length_remaining)
        self.ook_state = PD_OOK_STATE_IDLE
        self.pulse_length = 0
        self.gap_length = 0
        self.pending_pulse = 0
        self.start_pulse = 0
        self.max_pulse_samples = 0
        self._eop_on_spurious = 0
        pulses.ook_low_estimate = 0
        pulses.ook_high_estimate = 1
        pulses.end_ago = length_remaining
        out = pulses
        self._pulses = PulseData(pulses.sample_rate)
        self.largest_gap_seen = 0
        self.second_largest_gap_seen = 0
        # Return the result to the caller so the next pipeline stage can continue.
        return PULSE_DATA_OOK, out

    # Define _microseconds_to_samples(), a named step in the decoding/support pipeline.
    def _microseconds_to_samples(self, microseconds, samples_per_microsecond):
        # Return the result to the caller so the next pipeline stage can continue.
        return int(microseconds * samples_per_microsecond)

    # Define _min_eop_gap_samples(), a named step in the decoding/support pipeline.
    def _min_eop_gap_samples(self, samples_per_microsecond):
        """Return the detector's minimum ratio-EOP gap in samples.

        Device timing fields are expressed in microseconds. This helper converts
        them to samples so _gap_ends_package() can stay entirely in the sample
        domain. If no device/reset_limit_us is configured, fall back to the
        rtl_433 detector minimum gap of PD_MIN_GAP_MS.
        """
        device = self._device
        reset_limit_us = getattr(device, "reset_limit_us", 0) if device else 0
        tolerance_us = getattr(device, "tolerance_us", 0) if device else 0

        # Check this condition so only the matching signal/data case is handled here.
        if reset_limit_us > 0:
            effective_reset_limit_us = reset_limit_us - tolerance_us
            # Check this condition so only the matching signal/data case is handled here.
            if effective_reset_limit_us <= 0:
                effective_reset_limit_us = reset_limit_us
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            effective_reset_limit_us = PD_MIN_GAP_MS * 1000

        # Return the result to the caller so the next pipeline stage can continue.
        return self._microseconds_to_samples(
            effective_reset_limit_us,
            samples_per_microsecond,
        )

    # Define _gap_ends_package(), a named step in the decoding/support pipeline.
    def _gap_ends_package(self, gap_len_samples, samples_per_microsecond):
        min_gap = self._min_eop_gap_samples(samples_per_microsecond)
        max_gap = (PD_MAX_GAP_MS * 1000 * samples_per_microsecond)
        ratio_limit = PD_MAX_GAP_RATIO * self.max_pulse_samples if self.max_pulse_samples > 0 else 0
        device_reset_ok = gap_len_samples >= min_gap
        min_gap_ok = gap_len_samples > min_gap
        ratio_ok = self.max_pulse_samples > 0 and gap_len_samples > ratio_limit
        max_gap_ok = gap_len_samples > max_gap

        # Check this condition so only the matching signal/data case is handled here.
        if self._eop_on_spurious:
            self._log(LOG_EOP, "eop decision",
                      "gap", gap_len_samples, "max_pulse_samples", self.max_pulse_samples,
                      "spurious", 1, "decision", "yes", "reason", "spurious")
            # Return the result to the caller so the next pipeline stage can continue.
            return True

        # Check this condition so only the matching signal/data case is handled here.
        if device_reset_ok:
            self._log(
                LOG_EOP,
                "device reset gap seen",
                "gap", gap_len_samples,
                "device_reset_min", min_gap,
                "max_pulse_samples", self.max_pulse_samples,
                "ratio_limit", ratio_limit,
                "ratio_ok", int(ratio_ok),
                "min_gap_ok", int(min_gap_ok),
                "max_gap_ok", int(max_gap_ok),
                "decision",
                "eop" if (ratio_ok and min_gap_ok) or max_gap_ok else "continue",
                "note", "not detector EOP",
            )

        # Check this condition so only the matching signal/data case is handled here.
        if ratio_ok and min_gap_ok:
            self._log(LOG_EOP, "eop decision",
                      "gap", gap_len_samples, "max_pulse_samples", self.max_pulse_samples,
                      "ratio_limit", ratio_limit, "min_gap", min_gap,
                      "ratio_ok", int(ratio_ok), "min_gap_ok", int(min_gap_ok),
                      "decision", "yes", "reason", "ratio")
            # Return the result to the caller so the next pipeline stage can continue.
            return True

        # Check this condition so only the matching signal/data case is handled here.
        if max_gap_ok:
            self._log(LOG_EOP, "eop decision",
                      "gap", gap_len_samples, "max_pulse_samples", self.max_pulse_samples,
                      "max_gap", max_gap,
                      "decision", "yes", "reason", "max_gap")
            # Return the result to the caller so the next pipeline stage can continue.
            return True

        # Check this condition so only the matching signal/data case is handled here.
        if gap_len_samples >= min_gap or log_enabled(self.debug, LOG_DETECT):
            self._log(LOG_EOP, "eop decision",
                      "gap", gap_len_samples, "max_pulse_samples", self.max_pulse_samples,
                      "ratio_limit", ratio_limit, "min_gap", min_gap,
                      "max_gap", max_gap,
                      "device_reset_ok", int(device_reset_ok),
                      "ratio_ok", int(ratio_ok), "min_gap_ok", int(min_gap_ok),
                      "max_gap_ok", int(max_gap_ok),
                      "decision", "no")
        
        # Return the result to the caller so the next pipeline stage can continue.
        return False

    # Define _reset_to_idle(), a named step in the decoding/support pipeline.
    def _reset_to_idle(self, pulses=None):
        self._log(LOG_DETECT, "reset to idle",
                  "state", self.ook_state,
                  "pulse", self.pulse_length,
                  "gap", self.gap_length,
                  "pending", self.pending_pulse)
        self.ook_state = PD_OOK_STATE_IDLE
        self.pulse_length = 0
        self.gap_length = 0
        self.pending_pulse = 0
        self.start_pulse = 0
        self._eop_on_spurious = 0
        # Check this condition so only the matching signal/data case is handled here.
        if pulses is not None:
            pulses.clear()
            self._pulses = pulses

    # Define package(), a named step in the decoding/support pipeline.
    def package(self, edges, sample_rate=None, sample_offset=0, pulses=None, debug=LOG_NONE):
        """Process one chunk of (level, duration_us) edges.

        Returns (kind, pulses), matching rtl_433 pulse_detect_package() style.
        kind is 0 if no complete package was emitted, or PULSE_DATA_OOK when
        a package boundary has been detected.
        """
        self.consumed_edges = 0
        
        # Check this condition so only the matching signal/data case is handled here.
        if sample_rate is None:
            sample_rate = self.sample_rate
        # Check this condition so only the matching signal/data case is handled here.
        if pulses is None:
            pulses = self._pulses
        # Check this condition so only the matching signal/data case is handled here.
        if pulses.sample_rate != sample_rate:
            pulses.sample_rate = sample_rate

        samples_per_microsecond = sample_rate / 1000000.0

        chunk_samples = 0
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for _level, dur_us in edges:
            chunk_samples += self._us_to_samples(dur_us, sample_rate)

        # Check this condition so only the matching signal/data case is handled here.
        if self.ook_state == PD_OOK_STATE_IDLE and pulses.num_pulses == 0:
            pulses.start_ago += chunk_samples

        pos = 0

        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for edge_index, (level, dur_us) in enumerate(edges):
            duration_samples = self._us_to_samples(dur_us, sample_rate)
            # Check this condition so only the matching signal/data case is handled here.
            if duration_samples <= 0:
                self._log(
                    LOG_DETECT,
                    "zero duration_samples edge",
                    "level", level,
                    "state", self.ook_state,
                    "edge_index", edge_index,
                    "pulses", pulses.num_pulses,
                    "pending_pulse", self.pending_pulse,
                    "gap_length", self.gap_length,
                )
                
                # Treat zero-length pulse edges as noise.
                # Do not allow the next gap to extend the current gap.
                # Check this condition so only the matching signal/data case is handled here.
                if (
                    level == self.pulse_level
                    and self.ook_state == PD_OOK_STATE_GAP
                ):
                    # Check this condition so only the matching signal/data case is handled here.
                    if self.pending_pulse and self.gap_length >= PD_MIN_PULSE_SAMPLES:
                        self._log(
                            LOG_DETECT,
                            "closing pair before zero pulse",
                            "pulse", self.pending_pulse,
                            "gap", self.gap_length,
                        )
                        self._append_pair(pulses, self.pending_pulse, self.gap_length)
                    # Handle the fallback case when none of the earlier conditions matched.
                    else:
                        self._log(
                            LOG_DETECT,
                            "discarding gap due to zero pulse",
                            self.gap_length,
                        )

                    # Do not merge the gap before the zero-width pulse with the
                    # following gap. The zero-width pulse is a capture artifact,
                    # but the preceding complete pulse/gap pair is still useful.
                    self.pending_pulse = 0
                    self.gap_length = 0
                    self.ook_state = PD_OOK_STATE_GAP_START

                self.consumed_edges = edge_index + 1
                # Skip the rest of this iteration and move on to the next candidate.
                continue

            is_pulse = level == self.pulse_level

            # Check this condition so only the matching signal/data case is handled here.
            if self.ook_state == PD_OOK_STATE_IDLE:
                # Check this condition so only the matching signal/data case is handled here.
                if is_pulse:
                    lead_in_enabled = self._lead_in_enabled()
                    lead_in_not_ready = lead_in_enabled and not self._lead_in_ready()

                    # Check this condition so only the matching signal/data case is handled here.
                    if lead_in_not_ready:
                        self._log_start_reject(
                            LOG_DETECT,
                            PD_SKIP_REASON_LEAD_IN_NOT_READY,
                            pulse=duration_samples,
                            lead_in=self.lead_in_counter,
                            edge_index=edge_index,
                            state=self.ook_state,
                        )
                        self.consumed_edges = edge_index + 1
                        pos += duration_samples
                        # Skip the rest of this iteration and move on to the next candidate.
                        continue

                    self._clear_lead_in_on_activity()

                    start_pulse_too_long = (
                        duration_samples > PD_EDGE_MAX_START_PULSE_SAMPLES
                    )

                    # Check this condition so only the matching signal/data case is handled here.
                    if start_pulse_too_long:
                        self._log_start_reject(
                            LOG_DETECT,
                            PD_SKIP_REASON_START_PULSE_TOO_LONG,
                            pulse=duration_samples,
                            max_pulse=PD_EDGE_MAX_START_PULSE_SAMPLES,
                            enable_lead_in=lead_in_enabled,
                            edge_index=edge_index,
                            state=self.ook_state,
                        )
                        self._clear_lead_in_on_activity()
                        self.consumed_edges = edge_index + 1
                        pos += duration_samples
                        # Skip the rest of this iteration and move on to the next candidate.
                        continue

                    # Check this condition so only the matching signal/data case is handled here.
                    if lead_in_enabled:
                        start_pulse_too_short = (
                            duration_samples < PD_EDGE_MIN_START_PULSE_SAMPLES
                        )

                        # Check this condition so only the matching signal/data case is handled here.
                        if start_pulse_too_short:
                            self._log_start_reject(
                                LOG_DETECT,
                                PD_SKIP_REASON_START_PULSE_TOO_SHORT,
                                pulse=duration_samples,
                                min_pulse=PD_EDGE_MIN_START_PULSE_SAMPLES,
                                enable_lead_in=lead_in_enabled,
                                edge_index=edge_index,
                                state=self.ook_state,
                            )
                            self.consumed_edges = edge_index + 1
                            pos += duration_samples
                            # Skip the rest of this iteration and move on to the next candidate.
                            continue

                    self._log(LOG_DETECT, "candidate start pulse", duration_samples,
                              "level", level, "pos", sample_offset + pos)

                    # Check this condition so only the matching signal/data case is handled here.
                    if duration_samples < PD_EDGE_MIN_START_PULSE_SAMPLES:
                        self._log_start_reject(
                            LOG_DETECT,
                            PD_SKIP_REASON_START_PULSE_TOO_SHORT,
                            pulse=duration_samples,
                            min_pulse=PD_EDGE_MIN_START_PULSE_SAMPLES,
                            enable_lead_in=lead_in_enabled,
                            edge_index=edge_index,
                            state=self.ook_state,
                        )
                        self.pending_pulse = 0
                        self.gap_length = 0
                        self.start_pulse = 0
                        self.consumed_edges = edge_index + 1
                        pos += duration_samples
                        # Skip the rest of this iteration and move on to the next candidate.
                        continue

                    self.start_pulse = duration_samples
                    self.pending_pulse = duration_samples
                    self.pulse_length = 0
                    self.gap_length = 0
                    self.max_pulse_samples = 0
                    self._eop_on_spurious = 0
                    
                    self._log(
                        LOG_DETECT,
                        "start package context",
                        "pulse", self.pending_pulse,
                        "start_pulse", duration_samples,
                        "sample_offset", sample_offset + pos,
                        "edge_index", edge_index,
                        "lead_in", self.lead_in_counter,
                    )
                    
                    self.ook_state = PD_OOK_STATE_GAP_START
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    self._add_idle_lead_in(duration_samples)

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_PULSE:
                # Check this condition so only the matching signal/data case is handled here.
                if is_pulse:
                    self.pulse_length += duration_samples
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    # Check this condition so only the matching signal/data case is handled here.
                    if self.pulse_length < PD_MIN_PULSE_SAMPLES:
                        # Mirror rtl_433's behavior: early tiny pulses are idle
                        # chatter; later tiny pulses probably terminate a package.
                        # Check this condition so only the matching signal/data case is handled here.
                        if pulses.num_pulses <= 1:
                            self._log(LOG_DETECT, "tiny early pulse -> idle", self.pulse_length)
                            self._reset_to_idle(pulses)
                        # Handle the fallback case when none of the earlier conditions matched.
                        else:
                            self._log(LOG_DETECT, "tiny pulse -> eop on spurious", self.pulse_length)
                            self._eop_on_spurious = 1
                            self.pending_pulse = 0
                            self.gap_length = duration_samples
                            self.ook_state = PD_OOK_STATE_GAP
                    # Handle the fallback case when none of the earlier conditions matched.
                    else:
                        # Check this condition so only the matching signal/data case is handled here.
                        if self.pulse_length > PD_EDGE_MAX_START_PULSE_SAMPLES:
                            self._log(
                                LOG_DETECT,
                                "huge active pulse -> idle reset",
                                "edge_index", edge_index,
                                "pulse_length", self.pulse_length,
                                "max_allowed", PD_EDGE_MAX_START_PULSE_SAMPLES,
                                "gap_duration", duration_samples,
                                "state", self.ook_state,
                                "pulses", pulses.num_pulses,
                                "max_pulse_samples", self.max_pulse_samples,
                            )
                            self._reset_to_idle(pulses)
                            self.consumed_edges = edge_index + 1
                            pos += duration_samples
                            # Skip the rest of this iteration and move on to the next candidate.
                            continue

                        self.pending_pulse = self.pulse_length
                        self.pulse_length = 0
                        self.gap_length = duration_samples

                        # Check this condition so only the matching signal/data case is handled here.
                        if self.gap_length >= PD_MIN_PULSE_SAMPLES:
                            self.ook_state = PD_OOK_STATE_GAP

                            eop = self._gap_ends_package(
                                self.gap_length,
                                samples_per_microsecond,
                            )

                            # Check this condition so only the matching signal/data case is handled here.
                            if eop:
                                self._append_pair(pulses, self.pending_pulse, self.gap_length)
                                self.pending_pulse = 0
                                self.gap_length = 0
                                self.consumed_edges = edge_index + 1
                                # Return the result to the caller so the next pipeline stage can continue.
                                return self._finish_package(
                                    pulses,
                                    chunk_samples - pos,
                                    reason="first_gap_eop",
                                )

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_GAP_START:
                # Check this condition so only the matching signal/data case is handled here.
                if self.pending_pulse:
                    # Check this condition so only the matching signal/data case is handled here.
                    if is_pulse:
                        # Consecutive pulse-level duration_samples before a real gap;
                        # merge it into the candidate/continued pulse.
                        self.pending_pulse += duration_samples

                        start_pulse_too_long = (
                            self.pending_pulse > PD_EDGE_MAX_START_PULSE_SAMPLES
                        )

                        # Check this condition so only the matching signal/data case is handled here.
                        if start_pulse_too_long:
                            self._log_start_reject(
                                LOG_DETECT,
                                PD_SKIP_REASON_START_PULSE_TOO_LONG_DURING_START,
                                pulse=self.pending_pulse,
                                max_pulse=PD_EDGE_MAX_START_PULSE_SAMPLES,
                                edge_index=edge_index,
                                state=self.ook_state,
                            )
                            self._reset_to_idle(pulses)
                        self.consumed_edges = edge_index + 1
                        pos += duration_samples
                        # Skip the rest of this iteration and move on to the next candidate.
                        continue

                    self.gap_length += duration_samples

                    lead_in_enabled = self._lead_in_enabled()
                    start_gap_too_long = (
                        lead_in_enabled
                        and self.gap_length > PD_EDGE_MAX_START_GAP_SAMPLES
                    )

                    # Check this condition so only the matching signal/data case is handled here.
                    if start_gap_too_long:
                        self._log_start_reject(
                            LOG_DETECT,
                            PD_SKIP_REASON_START_GAP_TOO_LONG,
                            pulse=self.pending_pulse,
                            gap=self.gap_length,
                            max_gap=PD_EDGE_MAX_START_GAP_SAMPLES,
                            edge_index=edge_index,
                            state=self.ook_state,
                        )
                        self._reset_to_idle(pulses)
                        self.consumed_edges = edge_index + 1
                        pos += duration_samples
                        # Skip the rest of this iteration and move on to the next candidate.
                        continue

                    # Check this condition so only the matching signal/data case is handled here.
                    if (
                        self.pending_pulse >= PD_EDGE_MIN_START_PULSE_SAMPLES
                        and self.gap_length >= PD_EDGE_MIN_START_GAP_SAMPLES
                    ):
                        device = self._device
                        reset_limit_us = getattr(device, "reset_limit_us", 0) if device else 0
                        tolerance_us = getattr(device, "tolerance_us", 0) if device else 0

                        # Check this condition so only the matching signal/data case is handled here.
                        if reset_limit_us > 0:
                            start_reset_gap = reset_limit_us - tolerance_us
                            # Check this condition so only the matching signal/data case is handled here.
                            if start_reset_gap <= 0:
                                start_reset_gap = reset_limit_us

                            start_reset_gap_samples = self._us_to_samples(start_reset_gap, sample_rate)

                            # Check this condition so only the matching signal/data case is handled here.
                            if self.gap_length >= start_reset_gap_samples:
                                self._log_start_reject(
                                    LOG_DETECT,
                                    PD_SKIP_REASON_START_GAP_RESET,
                                    pulse=self.pending_pulse,
                                    gap=self.gap_length,
                                    reset_gap=start_reset_gap_samples,
                                    edge_index=edge_index,
                                    state=self.ook_state,
                                )
                                self._reset_to_idle(pulses)
                                self.consumed_edges = edge_index + 1
                                pos += duration_samples
                                # Skip the rest of this iteration and move on to the next candidate.
                                continue

                        pulses.clear()
                        pulses.sample_rate = sample_rate
                        pulses.offset = sample_offset + pos - self.pending_pulse
                        pulses.start_ago = chunk_samples - pos
                        self._track_max_pulse(self.pending_pulse)
                        self._eop_on_spurious = 0
                        self.ook_state = PD_OOK_STATE_GAP
                        self.largest_gap_seen = 0
                        self.second_largest_gap_seen = 0
                        self._log(LOG_DETECT, "start package",
                                  "pulse", self.pending_pulse,
                                  "gap", self.gap_length,
                                  "offset", pulses.offset)

                    self.consumed_edges = edge_index + 1
                    pos += duration_samples
                    # Skip the rest of this iteration and move on to the next candidate.
                    continue

                # Check this condition so only the matching signal/data case is handled here.
                if is_pulse:
                    # Spurious short gap: restore pulse + gap + current pulse.
                    self._merge_short_gap_into_pulse(duration_samples)
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    self.gap_length += duration_samples
                    # Check this condition so only the matching signal/data case is handled here.
                    if self.gap_length >= PD_MIN_PULSE_SAMPLES:
                        self.ook_state = PD_OOK_STATE_GAP

            # Check the next mutually exclusive case after the previous condition did not match.
            elif self.ook_state == PD_OOK_STATE_GAP:
                # Check this condition so only the matching signal/data case is handled here.
                if is_pulse:
                    
                    # Check this condition so only the matching signal/data case is handled here.
                    if duration_samples > PD_EDGE_MAX_START_PULSE_SAMPLES:
                        self._log(
                            LOG_DETECT,
                            "huge pulse after gap before append",
                            "edge_index", edge_index,
                            "duration_samples", duration_samples,
                            "pending_pulse", self.pending_pulse,
                            "gap_length", self.gap_length,
                            "state", self.ook_state,
                            "pulses", pulses.num_pulses,
                            "max_pulse_samples", self.max_pulse_samples,
                        )
                    
                    self._append_pair(pulses, self.pending_pulse, self.gap_length)
                    self.pending_pulse = 0
                    self.gap_length = 0

                    # Check this condition so only the matching signal/data case is handled here.
                    if pulses.num_pulses >= PD_MAX_PULSES:
                        self.consumed_edges = edge_index + 1
                        # Return the result to the caller so the next pipeline stage can continue.
                        return self._finish_package(pulses, chunk_samples - pos,
                                                    reason="max_pulses")

                    self.pulse_length = duration_samples

                    # Check this condition so only the matching signal/data case is handled here.
                    if self.pulse_length > PD_EDGE_MAX_START_PULSE_SAMPLES:
                        self._log(
                            LOG_DETECT,
                            "huge pulse becomes active pulse",
                            "edge_index", edge_index,
                            "pulse_length", self.pulse_length,
                            "state", self.ook_state,
                            "pulses", pulses.num_pulses,
                            "max_pulse_samples", self.max_pulse_samples,
                        )

                    self.ook_state = PD_OOK_STATE_PULSE
                # Handle the fallback case when none of the earlier conditions matched.
                else:
                    self.gap_length += duration_samples

                    eop = self._gap_ends_package(
                        self.gap_length,
                        samples_per_microsecond,
                    )

                    # Check this condition so only the matching signal/data case is handled here.
                    if eop:
                        self._append_pair(pulses, self.pending_pulse, self.gap_length)
                        self.pending_pulse = 0
                        self.gap_length = 0
                        self.consumed_edges = edge_index + 1
                        # Return the result to the caller so the next pipeline stage can continue.
                        return self._finish_package(
                            pulses,
                            chunk_samples - pos,
                            reason="long_gap",
                        )

            # Handle the fallback case when none of the earlier conditions matched.
            else:
                self._log(LOG_DETECT, "unknown state -> idle", self.ook_state)
                self._reset_to_idle(pulses)

            self.consumed_edges = edge_index + 1
            pos += duration_samples

        self._pulses = pulses
        # Return the result to the caller so the next pipeline stage can continue.
        return 0, pulses

    # Define flush(), a named step in the decoding/support pipeline.
    def flush(self):
        """Force out the current package if one is in progress."""
        pulses = self._pulses
        # Check this condition so only the matching signal/data case is handled here.
        if self.ook_state in (PD_OOK_STATE_GAP, PD_OOK_STATE_GAP_START):
            # Check this condition so only the matching signal/data case is handled here.
            if self.pending_pulse:
                self._append_pair(pulses, self.pending_pulse, self.gap_length)
            # Return the result to the caller so the next pipeline stage can continue.
            return self._finish_package(pulses, 0, reason="flush_gap")
        # Check this condition so only the matching signal/data case is handled here.
        if self.ook_state == PD_OOK_STATE_PULSE and self.pulse_length >= PD_MIN_PULSE_SAMPLES:
            # No following gap was observed; preserve a trailing pulse with gap 0.
            self._append_pair(pulses, self.pulse_length, 0)
            # Return the result to the caller so the next pipeline stage can continue.
            return self._finish_package(pulses, 0, reason="flush_pulse")
        # Check this condition so only the matching signal/data case is handled here.
        if pulses.num_pulses > 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return self._finish_package(pulses, 0, reason="flush_existing")
        # Return the result to the caller so the next pipeline stage can continue.
        return 0, pulses

# Backward-compatible helper. Not part of rtl_433; retained only for manual tests.
# Define widths_to_pulse_data(), a named step in the decoding/support pipeline.
def widths_to_pulse_data(widths, starts_high=True, sample_rate=1000000):
    pd = PulseData(sample_rate)
    i = 0 if starts_high else 1
    # Continue looping while the runtime condition says more capture or processing work remains.
    while i + 1 < len(widths):
        pd.append(widths[i], widths[i + 1])
        i += 2
    # Return the result to the caller so the next pipeline stage can continue.
    return pd
