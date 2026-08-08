# -----------------------------------------------------------------------------
# baseband.py
# Baseband constants and helpers describe the kind of OOK pulse modulation a device uses.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/baseband.py
# MicroPython subset of rtl_433 baseband.h constants/helpers used by pulse_detect.py.

# Start a protected block because this operation may not be available on every runtime.
try:
    import math
# Handle the error path without crashing the capture or test run.
except ImportError:
    math = None


# Define _pow10(), a named step in the decoding/support pipeline.
def _pow10(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return 10 ** x


# Define amp_to_db(), a named step in the decoding/support pipeline.
def amp_to_db(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return 10.0 * (math.log10(x) if x > 0 and math else 0) - 42.1442


# Define mag_to_db(), a named step in the decoding/support pipeline.
def mag_to_db(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return 20.0 * (math.log10(x) if x > 0 and math else 0) - 84.2884


# Define db_to_amp(), a named step in the decoding/support pipeline.
def db_to_amp(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return int(_pow10((x + 42.1442) / 10.0))


# Define db_to_mag(), a named step in the decoding/support pipeline.
def db_to_mag(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return int(_pow10((x + 84.2884) / 20.0))


# Define db_to_amp_f(), a named step in the decoding/support pipeline.
def db_to_amp_f(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return int(0.5 + _pow10(x / 10.0))


# Define db_to_mag_f(), a named step in the decoding/support pipeline.
def db_to_mag_f(x):
    # Return the result to the caller so the next pipeline stage can continue.
    return int(0.5 + _pow10(x / 20.0))


# Define min_(), a named step in the decoding/support pipeline.
def min_(a, b):
    # Return the result to the caller so the next pipeline stage can continue.
    return a if a < b else b


# Define max_(), a named step in the decoding/support pipeline.
def max_(a, b):
    # Return the result to the caller so the next pipeline stage can continue.
    return a if a > b else b


# rtl_433 pulse_detect.c OOK level constants for amplitude estimates.
OOK_MAX_HIGH_LEVEL = db_to_amp(0.0)
OOK_MAX_LOW_LEVEL = db_to_amp(-15.0)
