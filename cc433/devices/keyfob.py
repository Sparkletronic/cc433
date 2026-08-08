# -----------------------------------------------------------------------------
# keyfob.py
# DieseRC / EV1527-style keyfob metadata and decoder logic.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/devices/keyfob.py
# Profile for a 433.92 MHz ASK/OOK motor-control keyfob.
#
# Target hardware described by the seller as:
#   DieseRC Wireless DC Motor Remote Control Switch
#   DC 12V~80V 5A Relay Receiver Controller with 2 Transmitters
#   TYPE 1202M, ASK, supports 1527 encoding
#
# This is an observed-device profile. rtl_433 -A -vvvv did not identify a
# named decoder, but it did characterize the waveform cleanly as fixed-period
# OOK PWM with 25-bit rows.
#
# Observed rtl_433 analyzer output:
#   UP   codes : {25}59d7f78
#   STOP codes : {25}59d7fb8
#   DOWN codes : {25}59d7fd8
#
# Observed timing:
#   short pulse ~= 396-400 us
#   long pulse  ~= 1116-1124 us
#   reset gap   ~= 11300 us, rtl_433 flex reset_limit guess ~= 1084 us
#   fixed pulse+gap period ~= 1464 us

DECODE_ABORT_LENGTH = -1
DECODE_ABORT_EARLY = -2

# rtl_433 displays these 25-bit rows as 7 hex nibbles:
#   {25}59d7f78 / {25}59d7fb8 / {25}59d7fd8
# The last 5 actual command bits are 0x0F / 0x17 / 0x1B respectively.
# Keep the display-suffix map too because it is convenient for comparing logs.
KEYFOB_COMMANDS = {
    0x0F: "up",
    0x17: "stop",
    0x1B: "down",
}

KEYFOB_DISPLAY_COMMANDS = {
    0x78: "up",
    0xB8: "stop",
    0xD8: "down",
}


# Define _append_decoded(), a named step in the decoding/support pipeline.
def _append_decoded(device, data):
    # Check this condition so only the matching signal/data case is handled here.
    if not hasattr(device, "decoded"):
        device.decoded = []
    device.decoded.append(data)


# Define _extract_bits(), a named step in the decoding/support pipeline.
def _extract_bits(bitbuffer, row, bit_len):
    value = 0
    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for bit in range(bit_len):
        value = (value << 1) | bitbuffer.get_bit(row, bit)
    # Return the result to the caller so the next pipeline stage can continue.
    return value


# Define _row_hex(), a named step in the decoding/support pipeline.
def _row_hex(bitbuffer, row, bit_len):
    # Match rtl_433's code display style for non-byte-aligned rows.
    # A 25-bit row is stored in 4 bytes but displayed as 7 nibbles:
    #   bytes 59 D7 F7 80 -> {25}59d7f78
    nibbles = (bit_len + 3) // 4
    # Return the result to the caller so the next pipeline stage can continue.
    return bitbuffer.row_bytes(row).hex().upper()[:nibbles]


# Define keyfob_decode(), a named step in the decoding/support pipeline.
def keyfob_decode(device, bitbuffer):
    """Decode the observed 1202M/ASK three-button motor keyfob.

    Expected rows are 25 bits. The observed layout is treated conservatively:

        first 20 bits : remote id / fixed code
        last 5 bits   : button command

    rtl_433 displays the rows as {25}59d7f78, etc.  Because 25 bits is not
    byte-aligned, the familiar-looking final byte values 0x78/0xB8/0xD8 are
    display suffixes. The actual 5-bit commands are 0x0F/0x17/0x1B.

    Unknown commands are still emitted as decoded packets with button="unknown"
    so bring-up remains observable instead of silently failing.
    """
    decoded = 0

    # Iterate through each item so the pipeline can process one measured/test value at a time.
    for row in range(bitbuffer.num_rows):
        bit_len = bitbuffer.bits_per_row[row]
        # Check this condition so only the matching signal/data case is handled here.
        if bit_len != 25:
            # Skip the rest of this iteration and move on to the next candidate.
            continue

        full = _extract_bits(bitbuffer, row, bit_len)
        remote_id = (full >> 5) & 0xFFFFF
        command = full & 0x1F
        raw_msg = _row_hex(bitbuffer, row, bit_len)
        display_command = int(raw_msg[-2:], 16) if len(raw_msg) >= 2 else 0
        button = KEYFOB_COMMANDS.get(command, "unknown")

        data = {
            "model": "Keyfob-1202M",
            "row": row,
            "bits": bit_len,
            "id": remote_id,
            "command": command,
            "display_command": display_command,
            "button": button,
            "raw_msg": raw_msg,
        }

        # Keep the full 25-bit value too; raw_msg is the best field for
        # comparing against rtl_433 analyzer output such as {25}59d7f78.
        data["code"] = full

        _append_decoded(device, data)
        decoded += 1

    # Return the result to the caller so the next pipeline stage can continue.
    return decoded if decoded else DECODE_ABORT_LENGTH


# Define make_keyfob_device(), a named step in the decoding/support pipeline.
def make_keyfob_device():
    from ..pulse_slicer import Device, OOK_PULSE_PWM

    # Return the result to the caller so the next pipeline stage can continue.
    return Device(
        decode_fn=keyfob_decode,

        # Acquisition profile.  A button press sends repeated short frames, so
        # leave enough edge room to capture multiple frames if present.
        capture_max_edges=1024,
        capture_timeout_ms=300,
        capture_min_duration_us=0,
        capture_deglitch_us=30,
        enable_lead_in=False,

        # Observed from rtl_433 -A -vvvv on this TYPE 1202M ASK keyfob.
        # rtl_433 flex equivalent:
        #   -X 'n=keyfob,m=OOK_PWM,s=400,l=1120,r=1084,g=0,t=288,y=0'
        gap_limit_us=0,
        long_width_us=1120,
        modulation=OOK_PULSE_PWM,
        name="Keyfob TYPE 1202M ASK / DieseRC motor remote",
        pulse_level=1,
        reset_limit_us=8000,
        short_width_us=400,
        sync_width_us=0,
        tolerance_us=290,

        # CC1101 async OOK baseline already proven with Acurite and inFactory.
        cc1101_rx_bw_khz=270,
        cc1101_data_rate_kbps=3.79,
    )
