# -----------------------------------------------------------------------------
# infactory_cc433_success.py
# Fixture containing a known-good inFactory capture derived from rtl_433 behavior.
# -----------------------------------------------------------------------------

"""Known-good rtl_433 -A inFactory packet fixture.

The printed Pulse data values are rtl_433 analyzer samples from a successful
inFactory decode. The analyzer reported 250 kS/s units, so the fixture keeps
sample_rate=250_000 and stores the pulse/gap rows exactly as printed.

Expected rtl_433 decode:
    model: inFactory-TH
    id: 170
    channel: 1
    battery_ok: 1
    button: 0
    temperature_F: 82.70
    humidity: 45
    mic: CRC
"""

SAMPLE_RATE = 250_000

PULSE_GAP_ROWS = [
    (259, 235),
    (250, 238),
    (255, 233),
    (250, 237),
    (128, 1995),
    (129, 990),
    (129, 489),
    (135, 988),
    (127, 490),
    (130, 991),
    (132, 485),
    (131, 992),
    (127, 493),
    (129, 992),
    (130, 992),
    (126, 995),
    (124, 998),
    (126, 490),
    (131, 488),
    (127, 490),
    (126, 493),
    (131, 493),
    (130, 990),
    (132, 991),
    (128, 491),
    (128, 993),
    (127, 492),
    (124, 998),
    (129, 992),
    (128, 994),
    (127, 994),
    (127, 994),
    (127, 994),
    (132, 486),
    (130, 992),
    (127, 491),
    (125, 495),
    (131, 492),
    (129, 993),
    (127, 492),
    (130, 989),
    (132, 487),
    (133, 485),
    (129, 488),
    (127, 997),
    (125, 2591),
]

EXPECTED_ROWS = [40]
EXPECTED_HEX_ROWS = ["AAF06BF451"]

EXPECTED_DECODE = {
    "model": "inFactory-TH",
    "id": 170,
    "channel": 1,
    "battery_ok": True,
    "button": 0,
    "temperature_F": 82.7,
    "humidity": 45,
    "mic": "CRC",
    "raw_msg": "AAF06BF451",
}
