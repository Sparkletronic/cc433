"""
Acquire RF edge transitions and deliver them to the decoding pipeline.

The AcquisitionEngine is the hardware boundary of cc433. It configures the
radio, captures asynchronous OOK transitions from the CC1101, and converts
them into timestamped edge durations consumed by PulseDetectEdges.

Everything downstream operates on protocol timing rather than radio-specific
details.
"""

# Start a protected block because this operation may not be available on every runtime.
try:
    from micropython import const
# Handle the error path without crashing the capture or test run.
except ImportError:
    const = lambda x: x

import rp2
import gc
import machine

# The loop is two PIO instructions per duration count while the pin remains at
# the same level. With sm_freq=2_000_000, one count is approximately 1 us.
# The program waits for a HIGH, captures HIGH duration, captures LOW duration,
# and repeats. Python receives alternating HIGH, LOW durations.


# ============================================================================
# PIO Program
# ============================================================================

@rp2.asm_pio()

def _edge_duration_capture():
    pull(block)
    mov(y, osr)

    wait(1, pin, 0)

    label("high_start")
    mov(x, y)
    label("high_loop")
    jmp(pin, "high_still")
    jmp("high_done")
    label("high_still")
    jmp(x_dec, "high_loop")
    label("high_done")
    mov(isr, x)
    push(block)

    label("low_start")
    mov(x, y)
    label("low_loop")
    jmp(pin, "low_done")
    jmp(x_dec, "low_loop")
    label("low_done")
    mov(isr, x)
    push(block)
    jmp("high_start")

from .debug import (
    LOG_NONE,
    LOG_RF,
    LOG_CAPTURE,
    LOG_DETECT,
    LOG_EOP,
    LOG_FRAMING,
    LOG_SLICER,
    LOG_DECODER,
    LOG_STATS,
    LOG_SLICER_DETAIL,
    LOG_CAPTURE_DETAIL,
    LOG_FRAMING_DETAIL,
    LOG_PIPELINE_OVERVIEW,
    format_debug_mask,
    coerce_debug,
    log_enabled,
    configure_logging,
    get_log_state,
    restore_log_state,
    log,
)

def _log(debug, level, *args):
    log("[PIO]", debug, level, *args)


# ============================================================================
# Edge Utilities
# ============================================================================

CAPTURE_OVERVIEW_MIN_EDGES = const(16)

def _log_capture_summary(debug, chunk_index, edge_count, max_edges, capture_full):

    if (
        edge_count >= CAPTURE_OVERVIEW_MIN_EDGES
        or capture_full
        or log_enabled(debug, LOG_CAPTURE_DETAIL)
    ):
        _log(
            debug,
            LOG_CAPTURE,
            "capture",
            "chunk", chunk_index,
            "edges", edge_count,
            "max_edges", max_edges,
            "full", capture_full,
        )

def append_edge_duration(out, level, duration, deglitch_us, debug=LOG_NONE):
    """Append one edge duration using Flipper-style deglitch/merge rules.

    This belongs in the CC1101/PIO front end, before rtl_433-shaped
    PulseData exists. It intentionally does not change pulse slicing,
    bitbuffer behavior, or any device decoder.

    Rules mirror the useful parts of Flipper's RAW capture model:
    - ignore non-positive durations;
    - merge very short glitches into the previous duration;
    - merge adjacent durations with the same level.

    out stores mutable [level, duration_us] rows so repeated merges are cheap
    on MicroPython.
    """

    if duration <= 0:
        _log(debug, LOG_CAPTURE_DETAIL, "drop non-positive edge", level, duration)

        return

    level = int(level)
    duration = int(duration)

    if not out:
        out.append([level, duration])

        return

    prev = out[-1]
    prev_level = prev[0]

    if deglitch_us and duration < deglitch_us:
        _log(debug, LOG_CAPTURE_DETAIL, "merge glitch", (level, duration), "into", prev)
        prev[1] += duration

        return

    if level == prev_level:
        _log(debug, LOG_CAPTURE_DETAIL, "merge same-level edge", (level, duration), "into", prev)
        prev[1] += duration

        return

    out.append([level, duration])

def clean_edge_durations(edges, deglitch_us, debug=LOG_NONE):
    """Return Flipper-style cleaned (level, duration_us) edge durations."""
    out = []

    for level, duration in edges:
        append_edge_duration(out, level, duration, deglitch_us, debug=debug)
    cleaned = [(level, duration) for level, duration in out]

    if log_enabled(debug, LOG_CAPTURE_DETAIL):
        _log(debug, LOG_CAPTURE_DETAIL, "cleaned edges", len(edges), "->", len(cleaned))

    return cleaned

def summarize_edges(edges, max_rows=46, debug=LOG_CAPTURE_DETAIL):

    if not log_enabled(debug, LOG_CAPTURE_DETAIL):

        return

    _log(debug, LOG_CAPTURE_DETAIL, "edges count", len(edges))

    for edge_index, edge in enumerate(edges[:max_rows]):
        _log(debug, LOG_CAPTURE_DETAIL, "edge", edge_index, edge)

    if len(edges) > max_rows:
        _log(debug, LOG_CAPTURE_DETAIL, "...", len(edges) - max_rows, "more edges")

def summarize_pulses(pulses, max_rows=46, debug=LOG_FRAMING_DETAIL):

    if not log_enabled(debug, LOG_FRAMING_DETAIL):

        return

    pulse_count = pulses.num_pulses
    _log(debug, LOG_FRAMING_DETAIL, "pulse_count", pulse_count)

    if pulse_count:
        pulse_samples = pulses.pulse[:pulse_count]
        gap_samples = pulses.gap[:pulse_count]

        _log(debug, LOG_FRAMING_DETAIL, "min/max pulse", min(pulse_samples), max(pulse_samples))
        _log(debug, LOG_FRAMING_DETAIL, "min/max gap", min(gap_samples), max(gap_samples))

    for pulse_index in range(min(pulse_count, max_rows)):
        _log(
            debug,
            LOG_FRAMING_DETAIL,
            pulse_index,
            "pulse_samples", pulses.pulse[pulse_index],
            "gap_samples", pulses.gap[pulse_index],
        )

    if pulse_count > max_rows:
        _log(debug, LOG_FRAMING_DETAIL, "...", pulse_count - max_rows, "more pulse/gap pairs")

# ============================================================================
# Acquisition Engine
# ============================================================================

class AcquisitionEngine:
    """PIO GDO0 edge-duration engine backed by a CC1101 radio.

    AcquisitionEngine is the acquisition front end. It configures the radio for
    the selected rtl_433 device, starts RX, starts the PIO state machine, and
    drains edge durations from GDO0.

    Construction intentionally requires radio=... so the engine can always
    configure the CC1101 before capture.
    """

    def __init__(self, radio, sm_freq=2_000_000, max_count=0x7fffffff, debug=LOG_NONE):

        if rp2 is None:
            raise RuntimeError("rp2 PIO is not available on this MicroPython port")

        if radio is None:
            raise ValueError("AcquisitionEngine requires radio=")

        self.radio = radio
        self.pin = radio.gdo0
        self.debug = debug
        self.sm_freq = sm_freq
        self.max_count = max_count
        # Each decrement consumes two PIO clock cycles. At 2 MHz, one counter
        # decrement corresponds to approximately 1 µs.
        self.us_per_count = (2_000_000.0 / sm_freq)
        self.sm = rp2.StateMachine(
            0,
            _edge_duration_capture,
            freq=sm_freq,
            in_base=self.pin,
            jmp_pin=self.pin,
        )
        self._started = False
        self._next_level = 1

    def _log(self, level, *args):
        _log(self.debug, level, *args)

    def dump_radio_config(self, label):
        """Dump the live CC1101 state for this engine's required radio."""
        self._log(LOG_RF, label, "dump begin")
        self.radio.dump_basic_status()
        self.radio.dump_key_config()
        self.radio.dump_gdo()
        self._log(LOG_RF, label, "dump end")

    def configure_for_device(self, device):
        """Apply the device CC1101 profile and start RX before PIO capture."""
        registers = getattr(device, "cc1101_registers", None)
        rx_bw_khz = getattr(device, "cc1101_rx_bw_khz", None)
        data_rate_kbps = getattr(device, "cc1101_data_rate_kbps", None)

        if hasattr(self.radio, "debug"):
            self.radio.debug = self.debug

        self._log(
            LOG_STATS,
            "configuring CC1101 from device profile",
            getattr(device, "name", device),
            "rx_bw_khz", rx_bw_khz,
            "data_rate_kbps", data_rate_kbps,
            "registers", "yes" if registers else "no",
        )

        self.radio.configure_cc1101_async_ook(
            rx_bw_khz=rx_bw_khz,
            data_rate_kbps=data_rate_kbps,
            registers=registers,
        )

        started = self.radio.start_rx()
        self._log(LOG_RF, "radio.start_rx()", started)

        return started

    def start(self):

        if not self._started:
            self.sm.active(0)
            self.sm.put(self.max_count)
            self._next_level = 1
            self.sm.active(1)
            self._started = True
            self._log(LOG_RF, "PIO acquisition started")

    def stop(self):
        self.sm.active(0)
        self._started = False
        self._next_level = 1
        self._log(LOG_RF, "PIO acquisition stopped")

    def _remaining_to_us(self, remaining):
        counts = self.max_count - remaining

        if counts < 0:
            counts = 0

        return int(counts * self.us_per_count + 0.5)

    def drain_edges(self, max_edges=512, timeout_ms=250, min_duration_us=0,
                    deglitch_us=0, debug=None):
        """Drain up to max_edges from the PIO RX FIFO.

        Returns (level, duration_us) tuples. timeout_ms limits how long this
        call waits for data; it does not attempt to capture a full RF packet.

        Prefer min_duration_us=0 while debugging. Filtering at this source layer
        drops one side of an edge pair and can destroy pulse/gap alignment.

        deglitch_us applies Flipper-style edge merging before PulseDetectEdges.
        Pass deglitch_us=0 to inspect the raw PIO stream.
        """
        import time

        log_debug = self.debug if debug is None else debug
        self.start()
        out = []
        start = time.ticks_ms()
        last_activity = start

        raw_edges = 0
        dropped_min = 0

        while raw_edges < max_edges:

            if self.sm.rx_fifo():
                remaining = self.sm.get()
                last_activity = time.ticks_ms()
                raw_edges += 1
                dur_us = self._remaining_to_us(remaining)
                level = self._next_level
                self._next_level = 0 if self._next_level else 1

                if dur_us >= min_duration_us:

                    if deglitch_us and deglitch_us > 0:
                        append_edge_duration(out, level, dur_us, deglitch_us, debug=log_debug)

                    else:
                        out.append((level, dur_us))

                else:
                    dropped_min += 1

            else:
                now = time.ticks_ms()

                if time.ticks_diff(now, last_activity) >= timeout_ms:

                    break

        if deglitch_us and deglitch_us > 0:
            edges = [(level, duration) for level, duration in out]

        else:
            edges = out

        if (
            raw_edges >= CAPTURE_OVERVIEW_MIN_EDGES
            or dropped_min
            or log_enabled(log_debug, LOG_CAPTURE_DETAIL)
        ):
            _log(log_debug, LOG_CAPTURE, "drain_edges",
                 "raw", raw_edges,
                 "returned", len(edges),
                 "dropped_min", dropped_min)

        return edges

def _decoded_len(device):

    return len(getattr(device, "decoded", []))

def _new_decoded_items(device, previous_len):

    return getattr(device, "decoded", [])[previous_len:]

def _device_acquisition_value(device, name, explicit_value, default_value):

    if explicit_value is not None:

        return explicit_value
    value = getattr(device, name, None)

    return default_value if value is None else value

class _StopCapture(Exception):
    pass

class _DetectorDeviceProfile:
    """Shared detector profile for one RF stream and multiple devices.

    The slicers and decoders still receive the real device objects.  This
    lightweight profile is used only by PulseDetectEdges, which has to frame a
    single edge stream before any individual device can claim the packet.
    """

    def __init__(self, devices):
        primary = devices[0]
        self.name = "multi-device detector profile"
        self.pulse_level = primary.pulse_level

        # If any configured device can start without a lead-in, the shared
        # detector must allow that.  Otherwise keyfob-like devices can be
        # discarded before their PWM slicer ever sees the packet.
        self.enable_lead_in = True

        for device in devices:

            if not getattr(device, "enable_lead_in", True):
                self.enable_lead_in = False

                break

        # The detector uses reset_limit_us/tolerance_us only as generic framing
        # guidance.  Use the shortest positive reset so devices with shorter
        # reset gaps are not forced to wait for a longer protocol.
        reset_limit_us = None
        tolerance_us = 0

        for device in devices:
            candidate = getattr(device, "reset_limit_us", 0)

            if candidate and candidate > 0:

                if reset_limit_us is None or candidate < reset_limit_us:
                    reset_limit_us = candidate
            candidate_tolerance = getattr(device, "tolerance_us", 0)

            if candidate_tolerance and candidate_tolerance > tolerance_us:
                tolerance_us = candidate_tolerance

        self.reset_limit_us = 0 if reset_limit_us is None else reset_limit_us
        self.tolerance_us = tolerance_us

def _validate_devices(devices):

    if devices is None:
        raise ValueError("run_pio_capture_loop requires devices=")

    if not isinstance(devices, (list, tuple)):
        raise TypeError("devices must be a list or tuple")

    if len(devices) == 0:
        raise ValueError("devices cannot be empty")

    primary = devices[0]
    primary_pulse_level = getattr(primary, "pulse_level", None)

    for index, device in enumerate(devices):

        if device is None:
            raise ValueError("devices cannot contain None")

        if getattr(device, "pulse_level", None) != primary_pulse_level:
            raise ValueError("all devices must use the same pulse_level")

        if not hasattr(device, "modulation"):
            raise ValueError("device missing modulation")

        if not hasattr(device, "decode_fn"):
            raise ValueError("device missing decode_fn")

    return devices

def _device_names(devices):
    names = []

    for device in devices:
        names.append(getattr(device, "name", device))

    return names

def _device_acquisition_min(devices, name, default_value):
    value = None

    for device in devices:
        candidate = getattr(device, name, None)

        if candidate is None:

            continue

        if value is None or candidate < value:
            value = candidate

    return default_value if value is None else value

def _device_acquisition_max(devices, name, default_value):
    value = None

    for device in devices:
        candidate = getattr(device, name, None)

        if candidate is None:

            continue

        if value is None or candidate > value:
            value = candidate

    return default_value if value is None else value

# ============================================================================
# Capture Loop
# ============================================================================

class PioCaptureLoop:
    """Continuous PIO capture loop for one RF stream and multiple devices."""

    def __init__(
        self,
        engine,
        devices,
        max_edges=None,
        timeout_ms=None,
        sample_rate=1000000,
        stop_on_decode=False,
        decoded_callback=None,
        maintenance_callback=None,
        debug=LOG_PIPELINE_OVERVIEW,
        log_file_path=None,
        log_append=False,
        log_to_console=True
    ):

        if engine is None:
            raise ValueError("PioCaptureLoop requires engine=")

        self.engine = engine
        self.devices = _validate_devices(devices)
        self.primary_device = self.devices[0]
        self.detector_device = _DetectorDeviceProfile(self.devices)

        self.sample_rate = sample_rate
        self.stop_on_decode = stop_on_decode
        self.decoded_callback = decoded_callback
        self.maintenance_callback = maintenance_callback
        self.debug = coerce_debug(debug)

        self.log_file_path = log_file_path
        self.log_append = log_append
        self.log_to_console = log_to_console

        self._log_state = None
        self._configured_logging = (
            log_file_path is not None
            or log_append
            or log_to_console is not True
        )

        # Explicit arguments override device acquisition metadata.  Otherwise,
        # choose values that can capture the broadest configured device set.
        self.max_edges = (
            max_edges if max_edges is not None else
            _device_acquisition_max(self.devices, "capture_max_edges", 512)
        )
        self.timeout_ms = (
            timeout_ms if timeout_ms is not None else
            _device_acquisition_max(self.devices, "capture_timeout_ms", 75)
        )
        self.min_duration_us = _device_acquisition_min(
            self.devices,
            "capture_min_duration_us",
            _device_acquisition_min(self.devices, "min_duration_us", 0),
        )
        self.deglitch_us = _device_acquisition_min(
            self.devices,
            "capture_deglitch_us",
            _device_acquisition_min(self.devices, "deglitch_us", 0),
        )

        self.detector = None
        self.total_events = 0
        self.packages = 0
        self.small_packages = 0
        self.oversized_packages = 0
        self.discarded_idle_edges = 0
        self.suppressed_tiny_captures = 0
        self.suppressed_tiny_capture_edges = 0
        self.suppressed_tiny_capture_max_edges = 0
        self.pending_edges = []
        self.chunk_index = 0
        self.done_logged = False

        self.min_slice_pulses = 16
        self.max_slice_pulses = 300
        self.discard_leading_idle_us = 5000

    def run(self):
        from .pulse_detect import PulseDetectEdges

        self._configure_logging()
        self._configure_engine()

        self.detector = PulseDetectEdges(
            pulse_level=self.detector_device.pulse_level,
            sample_rate=self.sample_rate,
            device=self.detector_device,
            debug=self.debug,
        )

        self._log_start()

        # Start a protected block because this operation may not be available on every runtime.
        try:

            while True:
                edges = self._drain_edges()
                self._process_capture(edges)
                self.chunk_index += 1

                # Give the host application an opportunity to perform periodic
                # maintenance between capture cycles (battery checks, sleep mode,
                # statistics, etc.). This callback should return promptly unless
                # it intentionally wants to pause RF processing.
                if self.maintenance_callback is not None:
                    self.maintenance_callback()
                
                machine.idle()
        # Handle the error path without crashing the capture or test run.
        except KeyboardInterrupt:
            _log(self.debug, LOG_STATS, "capture loop interrupted")
        # Always run this cleanup step, even if the protected block failed.
        finally:
            self.engine.stop()

            if self._configured_logging:
                self._log_done()
                restore_log_state(self._log_state)

        self._log_done()

        return self.total_events

    def _configure_logging(self):
        self._log_state = get_log_state()

        if self._configured_logging:
            configure_logging(
                log_file_path=self.log_file_path,
                append=self.log_append,
                to_console=self.log_to_console,
            )

    def _configure_engine(self):

        if hasattr(self.engine, "debug"):
            self.engine.debug = self.debug

        _log(self.debug, LOG_STATS, "using supplied PIO engine")
        _log(self.debug, LOG_STATS, "devices", _device_names(self.devices))
        _log(self.debug, LOG_STATS, "primary device", getattr(self.primary_device, "name", self.primary_device))
        _log(self.debug, LOG_STATS,
             "detector profile",
             "pulse_level", self.detector_device.pulse_level,
             "enable_lead_in", self.detector_device.enable_lead_in,
             "reset_limit_us", self.detector_device.reset_limit_us,
             "tolerance_us", self.detector_device.tolerance_us)

        self.engine.configure_for_device(self.primary_device)

    def _log_start(self):
        _log(self.debug, LOG_STATS, "Starting PIO capture loop")
        _log(self.debug, LOG_STATS, "logging", format_debug_mask(self.debug))
        _log(self.debug, LOG_STATS,
             "pulse_level", self.detector_device.pulse_level,
             "max_edges", self.max_edges,
             "timeout_ms", self.timeout_ms,
             "min_duration_us", self.min_duration_us,
             "deglitch_us", self.deglitch_us)

    def _drain_edges(self):
        
        if gc.mem_free() < 50_000:
            gc.collect()
            
        edges = self.engine.drain_edges(
            max_edges=self.max_edges,
            timeout_ms=self.timeout_ms,
            min_duration_us=self.min_duration_us,
            deglitch_us=self.deglitch_us,
            debug=self.debug,
        )

        capture_full = len(edges) >= self.max_edges
        edge_count = len(edges)
        capture_is_tiny = (
            edge_count > 0
            and edge_count < CAPTURE_OVERVIEW_MIN_EDGES
            and not capture_full
            and not log_enabled(self.debug, LOG_CAPTURE_DETAIL)
        )

        if capture_is_tiny:
            self.suppressed_tiny_captures += 1
            self.suppressed_tiny_capture_edges += edge_count

            if edge_count > self.suppressed_tiny_capture_max_edges:
                self.suppressed_tiny_capture_max_edges = edge_count

        _log_capture_summary(
            self.debug,
            self.chunk_index,
            edge_count,
            self.max_edges,
            capture_full,
        )

        return edges

    def _process_capture(self, edges):

        if self.pending_edges:
            edges = self.pending_edges + edges
            self.pending_edges = []

        if not edges:
            _log(self.debug, LOG_CAPTURE_DETAIL, "chunk", self.chunk_index, "no edges")

            return

        # Reuse the existing pending_edges list as our working buffer and append
        # newly captured edges, avoiding a temporary list allocation from '+'.
        if self.pending_edges:
            self.pending_edges.extend(edges)
            edges = self.pending_edges
            self.pending_edges = []

        if not edges:
            _log(self.debug, LOG_CAPTURE_DETAIL, "chunk", self.chunk_index, "only discarded idle edges")

            return

        if log_enabled(self.debug, LOG_CAPTURE_DETAIL):
            _log(self.debug, LOG_CAPTURE_DETAIL, "chunk", self.chunk_index)
            summarize_edges(edges, debug=self.debug)

        _log(self.debug, LOG_FRAMING_DETAIL,
             "detector before",
             "state", self.detector.ook_state,
             "pulses", self.detector._pulses.num_pulses,
             "max_pulse_samples", self.detector.max_pulse_samples)

        self._process_edges(edges)
        
        gc.collect()

    def _discard_leading_idle_edges(self, edges):
        from .pulse_detect import PD_OOK_STATE_IDLE

        while (
            edges
            and self.detector.ook_state == PD_OOK_STATE_IDLE
            and self.detector._pulses.num_pulses == 0
            and edges[0][1] > self.discard_leading_idle_us
        ):
            _log(self.debug, LOG_CAPTURE_DETAIL, "discard leading idle edge:", edges[0])
            del edges[0]
            self.discarded_idle_edges += 1

        return edges

    def _process_edges(self, edges):
        from .pulse_detect import PULSE_DATA_OOK

        while edges:
            kind, pulses = self.detector.package(edges=edges, debug=LOG_NONE)
            consumed_edges = self.detector.consumed_edges

            if consumed_edges > 0:
                del edges[:consumed_edges]

            else:
                del edges[:]

            if kind != PULSE_DATA_OOK:
                self.pending_edges = edges

                break

            self._process_package(kind, pulses)

    def _process_package(self, kind, pulses):

        if log_enabled(self.debug, LOG_FRAMING_DETAIL) and pulses.num_pulses:
            _log(self.debug, LOG_FRAMING_DETAIL,
                 "state", "pulses", pulses.num_pulses,
                 "kind", kind,
                 "detector_state", self.detector.ook_state,
                 "max_pulse_samples", self.detector.max_pulse_samples)

        if pulses.num_pulses:
            gaps = pulses.gap[:pulses.num_pulses]
            _log(self.debug, LOG_FRAMING,
                 "package summary",
                 "pulses", pulses.num_pulses,
                 "first_gap", gaps[0],
                 "last_gap", gaps[-1],
                 "largest_gap", max(gaps))

        pulses.sync_lengths()
        pulse_count = pulses.num_pulses

        if pulse_count < self.min_slice_pulses:
            self.small_packages += 1
            _log(self.debug, LOG_FRAMING,
                 "small package", self.small_packages,
                 "pulses", pulse_count)

            if log_enabled(self.debug, LOG_FRAMING_DETAIL):
                summarize_pulses(pulses, max_rows=12, debug=self.debug)

            return

        self.packages += 1
        _log(self.debug, LOG_FRAMING_DETAIL,
             "package", self.packages,
             "pulses", pulse_count)

        if pulse_count > self.max_slice_pulses:
            self.oversized_packages += 1
            _log(self.debug, LOG_FRAMING,
                 "oversized package; skipping slice",
                 "limit", self.max_slice_pulses,
                 "pulses", pulse_count)

            return

        if log_enabled(self.debug, LOG_FRAMING_DETAIL):
            summarize_pulses(pulses, debug=self.debug)

        self._decode_with_devices(pulses)

    def _decode_with_devices(self, pulses):

        for device in self.devices:
            stop = self._decode_with_device(pulses, device)

            if stop:

                return True

        return False

    def _decode_with_device(self, pulses, device):
        from .pulse_slicer import pulse_slicer_pwm, pulse_slicer_ppm, OOK_PULSE_PWM, OOK_PULSE_PPM

        _log(self.debug, LOG_SLICER,
             "slicer", getattr(device, "name", device),
             device.modulation,
             "pulses", pulses.num_pulses)

        decoded_before = _decoded_len(device)

        if device.modulation == OOK_PULSE_PPM:
            events = pulse_slicer_ppm(pulses, device, self.debug)
        # Check the next mutually exclusive case after the previous condition did not match.
        elif device.modulation == OOK_PULSE_PWM:
            events = pulse_slicer_pwm(pulses, device, self.debug)

        else:
            events = 0
            _log(self.debug, LOG_SLICER,
                 "unsupported modulation",
                 getattr(device, "name", device),
                 device.modulation)

        self.total_events += events

        if not events:

            return False

        decoded = getattr(device, "decoded", [])

        _log(self.debug, LOG_DECODER,
             "device", getattr(device, "name", device),
             "events", events)
        _log(self.debug, LOG_DECODER, "decoded:", decoded)

        decoded_after = len(decoded)

        if self.decoded_callback is not None:
            for i in range(decoded_before, decoded_after):
                item = decoded[i]
                if not isinstance(item, dict):
                    raise TypeError("decoded callback item must be dict")
                self.decoded_callback(item)

        # Device decoders accumulate decoded packets in device.decoded. Once the
        # callback has consumed them, clear the list to prevent unbounded heap
        # growth during continuous operation.
        del decoded[:]

        if self.stop_on_decode:
            _log(self.debug, LOG_STATS, "stop_on_decode; exiting capture loop")
            self._log_done()
            raise _StopCapture

        return False

    def _log_done(self):

        if self.done_logged:

            return
        self.done_logged = True
        _log(self.debug, LOG_STATS,
             "done; packages", self.packages,
             "small skipped", self.small_packages,
             "oversized skipped", self.oversized_packages,
             "discarded idle edges", self.discarded_idle_edges,
             "tiny captures suppressed", self.suppressed_tiny_captures,
             "tiny capture edges", self.suppressed_tiny_capture_edges,
             "largest tiny capture", self.suppressed_tiny_capture_max_edges,
             "tiny capture threshold", CAPTURE_OVERVIEW_MIN_EDGES,
             "events", self.total_events)

# ============================================================================
# Public API
# ============================================================================

def run_pio_capture_loop(
    engine,
    devices,
    max_edges=None,
    timeout_ms=None,
    sample_rate=1000000,
    stop_on_decode=False,
    decoded_callback=None,
    maintenance_callback=None,
    debug=LOG_PIPELINE_OVERVIEW,
    log_file_path=None,
    log_append=False,
    log_to_console=True):
    """Run an rtl_433-style continuous PIO capture loop.

    devices must be a non-empty list or tuple.  devices[0] supplies the shared
    CC1101 radio profile.  The capture and detector path runs once, and each
    completed PulseData package is tried against every configured device.
    """
    loop = PioCaptureLoop(
        engine=engine,
        devices=devices,
        max_edges=max_edges,
        timeout_ms=timeout_ms,
        sample_rate=sample_rate,
        stop_on_decode=stop_on_decode,
        decoded_callback=decoded_callback,
        maintenance_callback=maintenance_callback,
        debug=debug,
        log_file_path=log_file_path,
        log_append=log_append,
        log_to_console=log_to_console,
    )
    # Start a protected block because this operation may not be available on every runtime.
    try:

        return loop.run()
    # Handle the error path without crashing the capture or test run.
    except _StopCapture:

        return loop.total_events
