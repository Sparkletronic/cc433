# -----------------------------------------------------------------------------
# _helpers.py
# Shared test helpers reduce duplication in host-side tests.
# -----------------------------------------------------------------------------

"""Shared test helpers for cc433 tests."""

import importlib
import unittest


# Define import_or_skip(), a named step in the decoding/support pipeline.
def import_or_skip(module_name):
    # Start a protected block because this operation may not be available on every runtime.
    try:
        # Return the result to the caller so the next pipeline stage can continue.
        return importlib.import_module(module_name)
    # Handle the error path without crashing the capture or test run.
    except ImportError as exc:
        raise unittest.SkipTest("{} is not importable on this host: {}".format(module_name, exc))
    # Handle the error path without crashing the capture or test run.
    except RuntimeError as exc:
        raise unittest.SkipTest("{} is not usable on this host: {}".format(module_name, exc))


# Define add_bits(), a named step in the decoding/support pipeline.
def add_bits(bitbuffer, bits):
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for bit in bits:
        bitbuffer.add_bit(1 if bit in (1, "1", True) else 0)
    # Return the result to the caller so the next pipeline stage can continue.
    return bitbuffer


# Define add_bytes(), a named step in the decoding/support pipeline.
def add_bytes(bitbuffer, data):
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for byte in data:
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for bit in range(8):
            bitbuffer.add_bit((byte >> (7 - bit)) & 1)
    # Return the result to the caller so the next pipeline stage can continue.
    return bitbuffer
