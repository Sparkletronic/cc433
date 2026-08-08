# -----------------------------------------------------------------------------
# infactory.py
# inFactory temperature/humidity device metadata and decoder logic.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/devices/infactory.py
# MicroPython subset of rtl_433 devices/infactory.c

DECODE_ABORT_LENGTH = -1
DECODE_ABORT_EARLY = -2
DECODE_FAIL_MIC = -3

# Define crc4(), a named step in the decoding/support pipeline.
def crc4(data, n, poly, init):
    """rtl_433 bit_util.c crc4() over n full bytes."""
    remainder = (init & 0x0F) << 4
    poly_shifted = poly << 4

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for i in range(n):
        remainder ^= data[i]
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for _ in range(8):
            # Check this condition so only the matching signal/data case is handled here.
            if remainder & 0x80:
                remainder = (remainder << 1) ^ poly_shifted
            # Handle the fallback case when none of the earlier conditions matched.
            else:
                remainder <<= 1

    # Return the result to the caller so the next pipeline stage can continue.
    return (remainder >> 4) & 0x0F


# Define infactory_crc_check(), a named step in the decoding/support pipeline.
def infactory_crc_check(b):
    msg = bytearray(b[:5])
    msg_crc = msg[1] >> 4

    # For CRC computation, channel bits are placed at the CRC position.
    msg[1] = (msg[1] & 0x0F) | ((msg[4] & 0x0F) << 4)

    crc = crc4(msg, 4, 0x13, 0)
    crc ^= msg[4] >> 4

    # Return the result to the caller so the next pipeline stage can continue.
    return crc == msg_crc


# Define infactory_decode(), a named step in the decoding/support pipeline.
def infactory_decode(device, bitbuffer):
    # rtl_433 infactory_decode() only inspects row 0.
    bit_len = bitbuffer.bits_per_row[0]

    # Check this condition so only the matching signal/data case is handled here.
    if bit_len != 40 and bit_len != 41:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_ABORT_LENGTH

    b = bitbuffer.row_bytes(0)
    # Check this condition so only the matching signal/data case is handled here.
    if len(b) < 5:
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_ABORT_LENGTH

    # Channel bits must not be zero.
    # Check this condition so only the matching signal/data case is handled here.
    if not (b[4] & 0x0F):
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_ABORT_EARLY

    # Check this condition so only the matching signal/data case is handled here.
    if not infactory_crc_check(b):
        # Return the result to the caller so the next pipeline stage can continue.
        return DECODE_FAIL_MIC

    sensor_id = b[0]
    button = (b[1] >> 3) & 1
    battery_low = (b[1] >> 2) & 1
    temp_raw = (b[2] << 4) | (b[3] >> 4)
    humidity = ((b[3] & 0x0F) * 10) + (b[4] >> 4)
    channel = b[4] & 0x03
    temp_f = (temp_raw - 900) * 0.1

    data = {
        "model": "inFactory-TH",
        "id": sensor_id,
        "channel": channel,
        "battery_ok": not battery_low,
        "button": button,
        "temperature_f": temp_f,
        "humidity": humidity,
        "mic": "CRC",
        "raw_msg": bytes(b[:5]).hex().upper(),
    }

    # Check this condition so only the matching signal/data case is handled here.
    if not hasattr(device, "decoded"):
        device.decoded = []
    device.decoded.append(data)
    # Return the result to the caller so the next pipeline stage can continue.
    return 1


# Define make_infactory_device(), a named step in the decoding/support pipeline.
def make_infactory_device():
    from ..pulse_slicer import Device, OOK_PULSE_PPM

    # Return the result to the caller so the next pipeline stage can continue.
    return Device(
        decode_fn=infactory_decode,
        capture_max_edges=1024,
        capture_timeout_ms=75,
        capture_min_duration_us=0,
        capture_deglitch_us=0,
        enable_lead_in=False,
        gap_limit_us=0,       # rtl_433 note: pulse_slicer_ppm does not use gap_limit_us if tolerance_us is set
        long_width_us=4000,
        modulation=OOK_PULSE_PPM,
        name="inFactory, nor-tec, FreeTec NC-3982-913 temperature humidity sensor",
        pulse_level=1,
        cc1101_rx_bw_khz=270,
        cc1101_data_rate_kbps=3.79,
        reset_limit_us=5000,
        short_width_us=2000,
        sync_width_us=500,
        tolerance_us=750,
    )
