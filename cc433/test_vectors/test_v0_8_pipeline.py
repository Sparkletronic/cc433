# -----------------------------------------------------------------------------
# test_v0_8_pipeline.py
# Pipeline test vector showing how captured edges should flow through the decoder stages.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/test_vectors/test_v0_8_pipeline.py
# CPython/MicroPython sanity checks for v0.8. These tests avoid hardware.

from ..bitbuffer import BitBuffer
from ..devices.acurite import make_acurite_6045m_device
from ..pulse_detect import PulseDetectEdges, PULSE_DATA_OOK
from ..pulse_slicer import pulse_slicer_pwm
from ..synthetic import bits_to_pwm_pairs, debug_acurite_device


# Define make_edges_from_pairs(), a named step in the decoding/support pipeline.
def make_edges_from_pairs(pairs, pulse_level=1):
    gap_level = 0 if pulse_level else 1
    edges = []
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for pulse_us, gap_us in pairs:
        edges.append((pulse_level, pulse_us))
        edges.append((gap_level, gap_us))
    # Return the result to the caller so the next pipeline stage can continue.
    return edges


# Define check_known_raw_acurite_decode(), a named step in the decoding/support pipeline.
def check_known_raw_acurite_decode():
    bb = BitBuffer()
    raw = bytes.fromhex("c048af12116aebc0ef")
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for b in raw:
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for bit in range(8):
            bb.add_bit((b >> (7 - bit)) & 1)

    device = make_acurite_6045m_device(invert_before_decode=False)
    ret = device.decode_fn(device, bb)
    print("known raw decode ret:", ret)
    print("decoded:", getattr(device, "decoded", None))
    # Return the result to the caller so the next pipeline stage can continue.
    return ret


# Define check_edge_detector_pwm_path(), a named step in the decoding/support pipeline.
def check_edge_detector_pwm_path():
    bits = "101010101100110011110000"
    pairs = bits_to_pwm_pairs(bits)
    edges = make_edges_from_pairs(pairs, pulse_level=1)

    detector = PulseDetectEdges(pulse_level=1, device=debug_acurite_device())
    kind = 0
    pulses = None

    # Deliberately feed awkward chunk sizes so state must continue correctly.
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for i in range(0, len(edges), 7):
        kind, pulses = detector.package(edges[i:i + 7])
        # Check this condition so only the matching signal/data case is handled here.
        if kind == PULSE_DATA_OOK:
            # Stop this loop because the current package or condition is complete.
            break

    # Check this condition so only the matching signal/data case is handled here.
    if kind != PULSE_DATA_OOK:
        kind, pulses = detector.flush()

    pulses.assert_invariants()
    print("edge detector kind:", kind)
    print("pulse rows:", pulses.num_pulses)
    print("first pairs:", list(zip(pulses.pulse[:6], pulses.gap[:6])))

    events = pulse_slicer_pwm(pulses, debug_acurite_device())
    print("debug slicer events:", events)
    # Return the result to the caller so the next pipeline stage can continue.
    return kind, pulses.num_pulses


# Define run_all(), a named step in the decoding/support pipeline.
def run_all():
    raw_ret = check_known_raw_acurite_decode()
    edge_kind, edge_rows = check_edge_detector_pwm_path()
    ok = raw_ret == 1 and edge_kind == PULSE_DATA_OOK and edge_rows > 0
    print("v0.8 sanity:", "PASS" if ok else "FAIL")
    # Return the result to the caller so the next pipeline stage can continue.
    return ok


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    run_all()
