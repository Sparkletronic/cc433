# -----------------------------------------------------------------------------
# debug.py
# Logging flags and helpers. The bit flags let bring-up code expose exactly the right amount of RF detail.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# Start a protected block because this operation may not be available on every runtime.
try:
    from micropython import const
# Handle the error path without crashing the capture or test run.
except ImportError:
    const = lambda x: x

# Bitmask logging sections. Combine with | to enable multiple areas.
LOG_NONE    = const(0)
LOG_RF      = const(1 << 0)   # CC1101 radio configuration/status
LOG_CAPTURE = const(1 << 1)   # PIO draining summaries and non-empty captures
LOG_DETECT  = const(1 << 2)   # PulseDetect / PulseDetectEdges state machine
LOG_EOP     = const(1 << 3)   # End-of-package decisions
LOG_FRAMING = const(1 << 4)   # Package/pulse summaries
LOG_SLICER  = const(1 << 5)   # PWM/PPM slicer summaries and bitbuffer events
LOG_DECODER = const(1 << 6)   # Device decoder events/results/errors
LOG_STATS   = const(1 << 7)   # Aggregate loop counters
LOG_SLICER_DETAIL = const(1 << 8)  # Per-pulse/per-bit slicer classification
LOG_CAPTURE_DETAIL = const(1 << 9) # Empty chunks, raw edge dumps, deglitch merges
LOG_FRAMING_DETAIL = const(1 << 10) # Pulse/gap pair dumps and detailed package shape
LOG_ALL     = const(0xFFFF)

# Common logging presets for field testing. These are masks, not separate
# sections, so callers can still add/remove individual bits with | and &~.
LOG_PIPELINE_OVERVIEW = LOG_RF | LOG_CAPTURE | LOG_FRAMING | LOG_DECODER | LOG_STATS
LOG_NEW_DEVICE = LOG_CAPTURE | LOG_FRAMING | LOG_SLICER | LOG_DECODER
LOG_DETECTOR_DEBUG = LOG_DETECT | LOG_EOP
LOG_SLICER_DEBUG = LOG_SLICER | LOG_SLICER_DETAIL
LOG_CAPTURE_DEBUG = LOG_CAPTURE | LOG_CAPTURE_DETAIL
LOG_FRAMING_DEBUG = LOG_FRAMING | LOG_FRAMING_DETAIL
LOG_BRINGUP_DETAIL = LOG_NEW_DEVICE | LOG_CAPTURE_DETAIL | LOG_FRAMING_DETAIL

_LOG_FILE = None
_LOG_FILE_OWNED = False
_LOG_FLUSH = True
_LOG_TO_CONSOLE = True
_LOG_CONSOLE_DEBUG = None


# Define coerce_debug(), a named step in the decoding/support pipeline.
def coerce_debug(debug=LOG_NONE):
    """Normalize a debug mask to an int for CPython and MicroPython callers."""
    # Check this condition so only the matching signal/data case is handled here.
    if debug is None:
        # Return the result to the caller so the next pipeline stage can continue.
        return LOG_NONE
    # Return the result to the caller so the next pipeline stage can continue.
    return int(debug)


# Define log_enabled(), a named step in the decoding/support pipeline.
def log_enabled(debug, section):
    """Return True when any bit in section is enabled in debug."""
    # Return the result to the caller so the next pipeline stage can continue.
    return (coerce_debug(debug) & int(section)) != 0


_LOG_SECTION_NAMES = (
    (LOG_RF, "RF"),
    (LOG_CAPTURE, "CAPTURE"),
    (LOG_DETECT, "DETECT"),
    (LOG_EOP, "EOP"),
    (LOG_FRAMING, "FRAMING"),
    (LOG_SLICER, "SLICER"),
    (LOG_DECODER, "DECODER"),
    (LOG_STATS, "STATS"),
    (LOG_SLICER_DETAIL, "SLICER_DETAIL"),
    (LOG_CAPTURE_DETAIL, "CAPTURE_DETAIL"),
    (LOG_FRAMING_DETAIL, "FRAMING_DETAIL"),
)


# Define debug_mask_names(), a named step in the decoding/support pipeline.
def debug_mask_names(debug):
    """Return enabled logging section names for a debug mask."""
    debug = coerce_debug(debug)
    # Check this condition so only the matching signal/data case is handled here.
    if debug == LOG_NONE:
        # Return the result to the caller so the next pipeline stage can continue.
        return ["NONE"]
    names = []
    known_bits = 0
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for bit, name in _LOG_SECTION_NAMES:
        known_bits |= int(bit)
        # Check this condition so only the matching signal/data case is handled here.
        if debug & int(bit):
            names.append(name)
    unknown_bits = debug & ~known_bits
    # Check this condition so only the matching signal/data case is handled here.
    if unknown_bits:
        names.append("UNKNOWN(0x%x)" % unknown_bits)
    # Return the result to the caller so the next pipeline stage can continue.
    return names


# Define format_debug_mask(), a named step in the decoding/support pipeline.
def format_debug_mask(debug):
    """Return a compact human-readable description of a debug mask."""
    # Return the result to the caller so the next pipeline stage can continue.
    return "|".join(debug_mask_names(debug))


# Define _line(), a named step in the decoding/support pipeline.
def _line(prefix, args):
    parts = [str(prefix)]
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for arg in args:
        parts.append(str(arg))
    # Return the result to the caller so the next pipeline stage can continue.
    return " ".join(parts)


# Define get_log_state(), a named step in the decoding/support pipeline.
def get_log_state():
    """Return the current process-wide debug sink state."""
    # Return the result to the caller so the next pipeline stage can continue.
    return (
        _LOG_FILE,
        _LOG_FILE_OWNED,
        _LOG_FLUSH,
        _LOG_TO_CONSOLE,
        _LOG_CONSOLE_DEBUG,
    )


# Define restore_log_state(), a named step in the decoding/support pipeline.
def restore_log_state(state):
    """Restore a state returned by get_log_state()."""
    global _LOG_FILE, _LOG_FILE_OWNED, _LOG_FLUSH, _LOG_TO_CONSOLE, _LOG_CONSOLE_DEBUG

    close_log_file()
    (
        _LOG_FILE,
        _LOG_FILE_OWNED,
        _LOG_FLUSH,
        _LOG_TO_CONSOLE,
        _LOG_CONSOLE_DEBUG,
    ) = state


# Define close_log_file(), a named step in the decoding/support pipeline.
def close_log_file():
    """Close the active log file if this module opened it."""
    global _LOG_FILE, _LOG_FILE_OWNED

    # Check this condition so only the matching signal/data case is handled here.
    if _LOG_FILE is not None and _LOG_FILE_OWNED:
        # Start a protected block because this operation may not be available on every runtime.
        try:
            _LOG_FILE.flush()
        # Handle the error path without crashing the capture or test run.
        except Exception:
            pass
        # Start a protected block because this operation may not be available on every runtime.
        try:
            _LOG_FILE.close()
        # Handle the error path without crashing the capture or test run.
        except Exception:
            pass

    _LOG_FILE = None
    _LOG_FILE_OWNED = False


# Define configure_logging(), a named step in the decoding/support pipeline.
def configure_logging(log_file_path=None, log_file=None, append=False,
                      flush=True, to_console=True, console_debug=None):
    """Configure the shared debug sink.

    debug controls which logging sections are emitted. console_debug optionally
    throttles what is printed to Thonny/stdout while the file still receives all
    messages allowed by debug.

    Example:
        run_pio_capture_loop(...,
                             debug=LOG_CAPTURE | LOG_FRAMING | LOG_DECODER,
                             log_file_path="/trace.txt",
                             log_console_debug=LOG_STATS | LOG_DECODER)
    """
    global _LOG_FILE, _LOG_FILE_OWNED, _LOG_FLUSH, _LOG_TO_CONSOLE, _LOG_CONSOLE_DEBUG

    close_log_file()

    # Check this condition so only the matching signal/data case is handled here.
    if log_file is not None:
        _LOG_FILE = log_file
        _LOG_FILE_OWNED = False
    # Check the next mutually exclusive case after the previous condition did not match.
    elif log_file_path is not None:
        mode = "a" if append else "w"
        _LOG_FILE = open(log_file_path, mode)
        _LOG_FILE_OWNED = True
    # Handle the fallback case when none of the earlier conditions matched.
    else:
        _LOG_FILE = None
        _LOG_FILE_OWNED = False

    _LOG_FLUSH = bool(flush)
    _LOG_TO_CONSOLE = bool(to_console)
    _LOG_CONSOLE_DEBUG = console_debug


# Define log(), a named step in the decoding/support pipeline.
def log(prefix, debug, section, *args):
    """Uniform section-bitmask logger used by the CC1101/PIO edge path."""
    # Check this condition so only the matching signal/data case is handled here.
    if not log_enabled(debug, section):
        # Return the result to the caller so the next pipeline stage can continue.
        return

    line = _line(prefix, args)

    console_debug = debug if _LOG_CONSOLE_DEBUG is None else _LOG_CONSOLE_DEBUG
    # Check this condition so only the matching signal/data case is handled here.
    if _LOG_TO_CONSOLE and log_enabled(console_debug, section):
        print(line)

    # Check this condition so only the matching signal/data case is handled here.
    if _LOG_FILE is not None:
        # Start a protected block because this operation may not be available on every runtime.
        try:
            _LOG_FILE.write(line)
            _LOG_FILE.write("\n")
            # Check this condition so only the matching signal/data case is handled here.
            if _LOG_FLUSH:
                _LOG_FILE.flush()
        # Handle the error path without crashing the capture or test run.
        except Exception:
            # Logging should never break capture. Fall back to console if possible.
            # Check this condition so only the matching signal/data case is handled here.
            if _LOG_TO_CONSOLE:
                print("[debug] log file write failed")
