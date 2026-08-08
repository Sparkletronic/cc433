# -----------------------------------------------------------------------------
# acurite.py
# Acurite 6045M device metadata and decoder logic.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/devices/acurite.py
# MicroPython subset of rtl_433 devices/acurite.c for Acurite 6045M only.

ACURITE_6045_BITLEN = 72
ACURITE_6045_BYTELEN = 9
ACURITE_MSGTYPE_6045M = 0x2f

DECODE_ABORT_LENGTH = -1
DECODE_FAIL_MIC = -2
DECODE_FAIL_SANITY = -3


# Define acurite_get_channel(), a named step in the decoding/support pipeline.
def acurite_get_channel(byte):
    # Return the result to the caller so the next pipeline stage can continue.
    return ("C", "E", "B", "A")[(byte & 0xC0) >> 6]


# Define add_bytes(), a named step in the decoding/support pipeline.
def add_bytes(bb, n):
    s = 0
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for i in range(n):
        s += bb[i]
    # Return the result to the caller so the next pipeline stage can continue.
    return s


# Define parity8(), a named step in the decoding/support pipeline.
def parity8(x):
    x &= 0xff
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    # Return the result to the caller so the next pipeline stage can continue.
    return x & 1


# Define parity_bytes(), a named step in the decoding/support pipeline.
def parity_bytes(bb, n):
    p = 0
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for i in range(n):
        p ^= parity8(bb[i])
    # Return the result to the caller so the next pipeline stage can continue.
    return p


# Define acurite_txr_check(), a named step in the decoding/support pipeline.
def acurite_txr_check(bb, browlen, explen=ACURITE_6045_BYTELEN):
    # Check this condition so only the matching signal/data case is handled here.
    if browlen < 6:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_ABORT_LENGTH
    # Check this condition so only the matching signal/data case is handled here.
    if browlen < explen:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_ABORT_LENGTH
    # Check this condition so only the matching signal/data case is handled here.
    if (add_bytes(bb, explen - 1) & 0xff) != bb[explen - 1]:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_MIC
    # Bytes 2 ... n-1 have even parity; ID bytes and checksum do not.
    # Check this condition so only the matching signal/data case is handled here.
    if parity_bytes(bb[2:], explen - 3):
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_MIC
    # Check this condition so only the matching signal/data case is handled here.
    if acurite_get_channel(bb[0]) == "E":
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_SANITY
    # Return the result to the caller so the next pipeline stage can continue.
    return 0


# Define acurite_6045_decode_bytes(), a named step in the decoding/support pipeline.
def acurite_6045_decode_bytes(bb):
    channel = acurite_get_channel(bb[0])
    sensor_id = ((bb[0] & 0x3f) << 8) | bb[1]
    battery_low = (bb[2] & 0x40) == 0
    humidity = bb[3] & 0x7f
    # Check this condition so only the matching signal/data case is handled here.
    if humidity > 100:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_SANITY, None

    active = (bb[4] & 0x40) == 0x40
    temp_raw = ((bb[4] & 0x1f) << 7) | (bb[5] & 0x7f)
    temp_f = (temp_raw - 1480) * 0.1
    # Check this condition so only the matching signal/data case is handled here.
    if temp_f < -40.0 or temp_f > 158.0:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_SANITY, None

    exception = 0
    # Check this condition so only the matching signal/data case is handled here.
    if temp_raw & 0x3000:
        exception += 1
    # Check this condition so only the matching signal/data case is handled here.
    if (bb[4] & 0x20) != 0:
        exception += 1

    strike_count = ((bb[6] & 0x7f) << 1) | ((bb[7] & 0x40) >> 6)
    strike_distance = bb[7] & 0x1f
    rfi_detect = (bb[7] & 0x20) == 0x20

    # Return the result to the caller so the next pipeline stage can continue.
    return 1, {
        "model": "Acurite-6045M",
        "id": sensor_id,
        "channel": channel,
        "battery_ok": not battery_low,
        "temperature_f": temp_f,
        "humidity": humidity,
        "strike_count": strike_count,
        "storm_dist_km": strike_distance,
        "active": active,
        "rfi": rfi_detect,
        "exception": exception,
        "raw_msg": bytes(bb[:ACURITE_6045_BYTELEN]).hex().upper(),
    }


# Define acurite_txr_decode(), a named step in the decoding/support pipeline.
def acurite_txr_decode(device, bitbuffer):
    decoded = 0
    last_error = 0

    # rtl_433's Acurite TXR path inverts slicer output before parsing.
    # Keep that behavior explicit and non-mutating so known raw-byte tests can
    # set invert_before_decode=False without corrupting the caller's bitbuffer.
    work = bitbuffer.clone() if getattr(device, "invert_before_decode", True) else bitbuffer
    # Check this condition so only the matching signal/data case is handled here.
    if getattr(device, "invert_before_decode", True):
        work.invert()

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for row in range(work.num_rows):
        row_bit_cnt = work.bits_per_row[row]
        browlen = row_bit_cnt // 8  # rtl_433 rounds down; extra bits are spurious
        # Check this condition so only the matching signal/data case is handled here.
        if browlen < 6:
            # Skip the rest of this iteration and move on to the next candidate.
            continue
        # Check this condition so only the matching signal/data case is handled here.
        if browlen > 10:
            last_error = DECODE_ABORT_LENGTH
            # Skip the rest of this iteration and move on to the next candidate.
            continue
        bb = work.row_bytes(row)
        # Check this condition so only the matching signal/data case is handled here.
        if bb[0] == 0 and bb[1] == 0 and bb[2] == 0 and bb[browlen - 1] == 0:
            # Skip the rest of this iteration and move on to the next candidate.
            continue
        message_type = bb[2] & 0x3f
        # Check this condition so only the matching signal/data case is handled here.
        if message_type != ACURITE_MSGTYPE_6045M:
            last_error = DECODE_FAIL_SANITY
            # Skip the rest of this iteration and move on to the next candidate.
            continue
        ret = acurite_txr_check(bb, browlen, ACURITE_6045_BYTELEN)
        # Check this condition so only the matching signal/data case is handled here.
        if ret != 0:
            last_error = ret
            # Skip the rest of this iteration and move on to the next candidate.
            continue
        ret, data = acurite_6045_decode_bytes(bb)
        # Check this condition so only the matching signal/data case is handled here.
        if ret > 0:
            decoded += ret
            # Check this condition so only the matching signal/data case is handled here.
            if not hasattr(device, "decoded"):
                device.decoded = []
            device.decoded.append(data)
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            last_error = ret
    # Return the result to the caller so the next pipeline stage can continue.
    return decoded if decoded else last_error


# Define make_acurite_6045m_device(), a named step in the decoding/support pipeline.
def make_acurite_6045m_device(invert_before_decode=True):
    from ..pulse_slicer import Device, OOK_PULSE_PWM
    device = Device(
        decode_fn=acurite_txr_decode,
        capture_max_edges=512,
        capture_timeout_ms=75,
        capture_min_duration_us=0,
        capture_deglitch_us=30,
        enable_lead_in=True,
        gap_limit_us=500,
        long_width_us=408,
        modulation=OOK_PULSE_PWM,
        name="Acurite 6045M Lightning Detector",
        pulse_level=1,
        cc1101_rx_bw_khz=270,
        cc1101_data_rate_kbps=3.79,
        reset_limit_us=4000,
        short_width_us=220,
        sync_width_us=620,
        tolerance_us=0,
    )
    device.invert_before_decode = invert_before_decode
    # Return the result to the caller so the next pipeline stage can continue.
    return device
