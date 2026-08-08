# -----------------------------------------------------------------------------
# cc1101_radio.py
# Low-level CC1101 radio driver. This file talks to the SPI radio chip and hides register-level details from the decoding pipeline.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

from micropython import const
from machine import Pin
import time

from ..pulse_slicer import CC1101_ASYNC_OOK_REGISTERS
from ..debug import LOG_NONE, LOG_RF, log

# ============================================================
# CC1101 COMMAND STROBES
# ============================================================

CC1101_SRES = const(0x30)
CC1101_SFSTXON = const(0x31)
CC1101_SXOFF = const(0x32)
CC1101_SCAL = const(0x33)
CC1101_SRX = const(0x34)
CC1101_STX = const(0x35)
CC1101_SIDLE = const(0x36)
CC1101_SAFC = const(0x37)
CC1101_SWOR = const(0x38)
CC1101_SPWD = const(0x39)
CC1101_SFRX = const(0x3A)
CC1101_SFTX = const(0x3B)
CC1101_SWORRST = const(0x3C)
CC1101_SNOP = const(0x3D)

# ============================================================
# CC1101 CONFIGURATION REGISTERS
# ============================================================

CC1101_IOCFG2 = const(0x00)
CC1101_IOCFG1 = const(0x01)
CC1101_IOCFG0 = const(0x02)
CC1101_FIFOTHR = const(0x03)
CC1101_SYNC1 = const(0x04)
CC1101_SYNC0 = const(0x05)
CC1101_PKTLEN = const(0x06)
CC1101_PKTCTRL1 = const(0x07)
CC1101_PKTCTRL0 = const(0x08)
CC1101_ADDR = const(0x09)
CC1101_CHANNR = const(0x0A)
CC1101_FSCTRL1 = const(0x0B)
CC1101_FSCTRL0 = const(0x0C)
CC1101_FREQ2 = const(0x0D)
CC1101_FREQ1 = const(0x0E)
CC1101_FREQ0 = const(0x0F)
CC1101_MDMCFG4 = const(0x10)
CC1101_MDMCFG3 = const(0x11)
CC1101_MDMCFG2 = const(0x12)
CC1101_MDMCFG1 = const(0x13)
CC1101_MDMCFG0 = const(0x14)
CC1101_DEVIATN = const(0x15)
CC1101_MCSM2 = const(0x16)
CC1101_MCSM1 = const(0x17)
CC1101_MCSM0 = const(0x18)
CC1101_FOCCFG = const(0x19)
CC1101_BSCFG = const(0x1A)
CC1101_AGCCTRL2 = const(0x1B)
CC1101_AGCCTRL1 = const(0x1C)
CC1101_AGCCTRL0 = const(0x1D)
CC1101_WOREVT1 = const(0x1E)
CC1101_WOREVT0 = const(0x1F)
CC1101_WORCTRL = const(0x20)
CC1101_FREND1 = const(0x21)
CC1101_FREND0 = const(0x22)
CC1101_FSCAL3 = const(0x23)
CC1101_FSCAL2 = const(0x24)
CC1101_FSCAL1 = const(0x25)
CC1101_FSCAL0 = const(0x26)
CC1101_RCCTRL1 = const(0x27)
CC1101_RCCTRL0 = const(0x28)
CC1101_FSTEST = const(0x29)
CC1101_PTEST = const(0x2A)
CC1101_AGCTEST = const(0x2B)
CC1101_TEST2 = const(0x2C)
CC1101_TEST1 = const(0x2D)
CC1101_TEST0 = const(0x2E)

# ============================================================
# CC1101 STATUS REGISTERS
# ============================================================

CC1101_PARTNUM = const(0x30)
CC1101_VERSION = const(0x31)
CC1101_FREQEST = const(0x32)
CC1101_LQI = const(0x33)
CC1101_RSSI = const(0x34)
CC1101_MARCSTATE = const(0x35)
CC1101_WORTIME1 = const(0x36)
CC1101_WORTIME0 = const(0x37)
CC1101_PKTSTATUS = const(0x38)
CC1101_VCO_VC_DAC = const(0x39)
CC1101_TXBYTES = const(0x3A)
CC1101_RXBYTES = const(0x3B)
CC1101_RCCTRL1_STATUS = const(0x3C)
CC1101_RCCTRL0_STATUS = const(0x3D)

# ============================================================
# CC1101 ACCESS FLAGS
# ============================================================

CC1101_WRITE_BURST = const(0x40)
CC1101_READ_SINGLE = const(0x80)
CC1101_READ_BURST = const(0xC0)

# ============================================================
# GDO CONFIG VALUES
# ============================================================

CC1101_GDOX_RX_FIFO_THR = const(0x00)
CC1101_GDOX_RX_FIFO_OVERFLOW = const(0x04)
CC1101_GDOX_PKT_SYNC_RXTX = const(0x06)
CC1101_GDOX_CRC_OK = const(0x07)
CC1101_GDOX_SERIAL_SYNC_DATA = const(0x0B)
CC1101_GDOX_ASYNC_SERIAL_DATA = const(0x0D)
CC1101_GDOX_HIGH_IMPEDANCE = const(0x2E)

# ============================================================
# MARCSTATE VALUES
# ============================================================

CC1101_MARCSTATE_SLEEP = const(0x00)
CC1101_MARCSTATE_IDLE = const(0x01)
CC1101_MARCSTATE_XOFF = const(0x02)
CC1101_MARCSTATE_VCOON_MC = const(0x03)
CC1101_MARCSTATE_REGON_MC = const(0x04)
CC1101_MARCSTATE_MANCAL = const(0x05)
CC1101_MARCSTATE_VCOON = const(0x06)
CC1101_MARCSTATE_REGON = const(0x07)
CC1101_MARCSTATE_STARTCAL = const(0x08)
CC1101_MARCSTATE_BWBOOST = const(0x09)
CC1101_MARCSTATE_FS_LOCK = const(0x0A)
CC1101_MARCSTATE_IFADCON = const(0x0B)
CC1101_MARCSTATE_ENDCAL = const(0x0C)
CC1101_MARCSTATE_RX = const(0x0D)
CC1101_MARCSTATE_RX_END = const(0x0E)
CC1101_MARCSTATE_RX_RST = const(0x0F)
CC1101_MARCSTATE_TXRX_SWITCH = const(0x10)
CC1101_MARCSTATE_RXFIFO_OVERFLOW = const(0x11)
CC1101_MARCSTATE_FSTXON = const(0x12)
CC1101_MARCSTATE_TX = const(0x13)
CC1101_MARCSTATE_TX_END = const(0x14)
CC1101_MARCSTATE_RXTX_SWITCH = const(0x15)
CC1101_MARCSTATE_TXFIFO_UNDERFLOW = const(0x16)

# ============================================================
# USER OPTIONS
# ============================================================

# RX filter bandwidth presets. Upper nibble of MDMCFG4 only.
BW_BITS_MAP = {
    203: 0x90,
    270: 0x80,
    325: 0x70,
    406: 0x60,
    464: 0x50,
    541: 0x40,
    650: 0x30,
    812: 0x20,
}

# Approx CC1101 data rate settings for 26 MHz crystal.
# key = kbps, value = (DRATE_E lower nibble of MDMCFG4, DRATE_M MDMCFG3)
DATA_RATE_MAP = {
    8.6: (5, 0x83),   # original config, approximately 8.62 kbps
    10:  (10, 0xF8),
    20:  (11, 0xF8),
    40:  (12, 0xF8),
}

# Define the CC1101Radio class, which groups related state and behavior for this stage.
class CC1101Radio:
    """
    Low-level CC1101 control only.
    No protocol logic here.
    """

    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(
        self,
        spi_bus,
        cs_pin,
        gdo0_pin=None,
        gdo2_pin=None,
        debug=LOG_NONE,
    ):
        self.spi_bus = spi_bus
        self.cs = Pin(cs_pin, Pin.OUT, value=1)
        self.gdo0 = (
            Pin(gdo0_pin, Pin.IN)
            # Check this condition so only the matching signal/data case is handled here.
            if gdo0_pin is not None
            else None
        )
        self.gdo2 = (
            Pin(gdo2_pin, Pin.IN)
            # Check this condition so only the matching signal/data case is handled here.
            if gdo2_pin is not None
            else None
        )
        self.debug = debug
        self._rwbuf = bytearray(2)

    # Define _log(), a named step in the decoding/support pipeline.
    def _log(self, level, *args):
        log("[CC1101]", self.debug, level, *args)

    # Define _wait_ready(), a named step in the decoding/support pipeline.
    def _wait_ready(self, timeout_us=1000):
        miso = self.spi_bus.miso_pin
        # Check this condition so only the matching signal/data case is handled here.
        if miso is None:
            # Return the result to the caller so the next pipeline stage can continue.
            return True

        start = time.ticks_us()
        # Continue looping while the runtime condition says more capture or processing work remains.
        while miso.value():
            # Check this condition so only the matching signal/data case is handled here.
            if time.ticks_diff(time.ticks_us(), start) >= timeout_us:
                # Return the result to the caller so the next pipeline stage can continue.
                return False
        # Return the result to the caller so the next pipeline stage can continue.
        return True

    # Define _begin(), a named step in the decoding/support pipeline.
    def _begin(self):
        self.cs.value(0)
        time.sleep_us(5)
        # Check this condition so only the matching signal/data case is handled here.
        if not self._wait_ready():
            self._log(LOG_RF, "CC1101 not ready after CS low")
            self.cs.value(1)
            time.sleep_us(5)
            # Return the result to the caller so the next pipeline stage can continue.
            return False
        # Return the result to the caller so the next pipeline stage can continue.
        return True

    # Define _end(), a named step in the decoding/support pipeline.
    def _end(self):
        time.sleep_us(1)
        self.cs.value(1)
        time.sleep_us(5)

    # Define _select(), a named step in the decoding/support pipeline.
    def _select(self):
        self.cs.value(0)

    # Define _deselect(), a named step in the decoding/support pipeline.
    def _deselect(self):
        self.cs.value(1)

    # Define read_config_reg(), a named step in the decoding/support pipeline.
    def read_config_reg(self, addr):
        # Check this condition so only the matching signal/data case is handled here.
        if not self._begin():
            # Return the result to the caller so the next pipeline stage can continue.
            return None

        self._rwbuf[0] = (addr & 0x3F) | CC1101_READ_SINGLE
        self._rwbuf[1] = 0x00
        self.spi_bus.spi.write_readinto(self._rwbuf, self._rwbuf)

        self._end()
        # Return the result to the caller so the next pipeline stage can continue.
        return self._rwbuf[1]

    # Define read_status_reg(), a named step in the decoding/support pipeline.
    def read_status_reg(self, addr):
        # Check this condition so only the matching signal/data case is handled here.
        if not self._begin():
            # Return the result to the caller so the next pipeline stage can continue.
            return None

        self._rwbuf[0] = (addr & 0x3F) | CC1101_READ_BURST
        self._rwbuf[1] = 0x00
        self.spi_bus.spi.write_readinto(self._rwbuf, self._rwbuf)

        self._end()
        # Return the result to the caller so the next pipeline stage can continue.
        return self._rwbuf[1]

    # Define write_reg(), a named step in the decoding/support pipeline.
    def write_reg(self, addr, value):
        # Check this condition so only the matching signal/data case is handled here.
        if not self._begin():
            # Return the result to the caller so the next pipeline stage can continue.
            return False

        self._rwbuf[0] = addr & 0x3F
        self._rwbuf[1] = value & 0xFF
        self.spi_bus.spi.write(self._rwbuf)

        self._end()
        # Return the result to the caller so the next pipeline stage can continue.
        return True

    # Define strobe(), a named step in the decoding/support pipeline.
    def strobe(self, strobe):
        # Check this condition so only the matching signal/data case is handled here.
        if not self._begin():
            # Return the result to the caller so the next pipeline stage can continue.
            return False

        self.spi_bus.spi.write(bytearray((strobe,)))
        self._end()
        # Return the result to the caller so the next pipeline stage can continue.
        return True

    # Define reset(), a named step in the decoding/support pipeline.
    def reset(self):
        self._deselect()
        time.sleep_us(5)
        self._select()
        time.sleep_us(10)
        self._deselect()
        time.sleep_us(50)
        self.strobe(CC1101_SRES)
        time.sleep_ms(1)
        self._log(LOG_RF, "radio reset complete")

    # Define marcstate(), a named step in the decoding/support pipeline.
    def marcstate(self):
        value = self.read_status_reg(CC1101_MARCSTATE)
        # Check this condition so only the matching signal/data case is handled here.
        if value is None:
            # Return the result to the caller so the next pipeline stage can continue.
            return None
        # Return the result to the caller so the next pipeline stage can continue.
        return value & 0x1F

    # Define dump_basic_status(), a named step in the decoding/support pipeline.
    def dump_basic_status(self):
        # Start a protected block because this operation may not be available on every runtime.
        try:
            partnum = self.read_status_reg(CC1101_PARTNUM)
            version = self.read_status_reg(CC1101_VERSION)
            marc = self.marcstate()
            pktstatus = self.read_status_reg(CC1101_PKTSTATUS)
            rssi = self.read_status_reg(CC1101_RSSI)
            self._log(
                LOG_RF,
                "partnum=", partnum,
                "version=", version,
                "marcstate=", marc,
                "pktstatus=", pktstatus,
                "rssi=", rssi,
            )
        # Handle the error path without crashing the capture or test run.
        except Exception as exc:
            self._log(LOG_RF, "status read failed:", exc)

    # Define dump_key_config(), a named step in the decoding/support pipeline.
    def dump_key_config(self):
        self._log(LOG_RF, "IOCFG0 =", self.read_config_reg(CC1101_IOCFG0))
        self._log(LOG_RF, "PKTCTRL0 =", self.read_config_reg(CC1101_PKTCTRL0))
        self._log(LOG_RF, "MDMCFG4 =", self.read_config_reg(CC1101_MDMCFG4))
        self._log(LOG_RF, "MDMCFG3 =", self.read_config_reg(CC1101_MDMCFG3))
        self._log(LOG_RF, "MDMCFG2 =", self.read_config_reg(CC1101_MDMCFG2))
        self._log(LOG_RF, "FREQ2 =", self.read_config_reg(CC1101_FREQ2))
        self._log(LOG_RF, "FREQ1 =", self.read_config_reg(CC1101_FREQ1))
        self._log(LOG_RF, "FREQ0 =", self.read_config_reg(CC1101_FREQ0))
        self._log(LOG_RF, "MCSM1 =", self.read_config_reg(CC1101_MCSM1))
        self._log(LOG_RF, "MCSM0 =", self.read_config_reg(CC1101_MCSM0))

    # Define configure_async_ook_43392(), a named step in the decoding/support pipeline.
    def configure_async_ook_43392(self, rx_bw_khz=406, data_rate_kbps=20):
        """
        Clean baseline configuration for raw async OOK.
        Bypasses packet engine. rx_bw_khz controls CHANBW; data_rate_kbps
        controls DRATE_E/DRATE_M, which still affects async demod filtering.
        """
        self.reset()

        self.strobe(CC1101_SIDLE)
        self.strobe(CC1101_SFRX)
        self.strobe(CC1101_SFTX)

        # GDO0 emits asynchronous serial data
        self.write_reg(CC1101_IOCFG0, CC1101_GDOX_ASYNC_SERIAL_DATA)
        self.write_reg(CC1101_IOCFG1, CC1101_GDOX_HIGH_IMPEDANCE)
        self.write_reg(CC1101_IOCFG2, CC1101_GDOX_HIGH_IMPEDANCE)

        # Packet engine bypassed
        self.write_reg(CC1101_FIFOTHR, 0x47)
        self.write_reg(CC1101_SYNC1, 0x00)
        self.write_reg(CC1101_SYNC0, 0x00)
        self.write_reg(CC1101_PKTLEN, 0xFF)
        self.write_reg(CC1101_PKTCTRL1, 0x04)
        self.write_reg(CC1101_PKTCTRL0, 0x32)

        self.write_reg(CC1101_ADDR, 0x00)
        self.write_reg(CC1101_CHANNR, 0x00)

        # IF
        self.write_reg(CC1101_FSCTRL1, 0x06)
        self.write_reg(CC1101_FSCTRL0, 0x00)

        # Center frequency 433.92 MHz
        self.write_reg(CC1101_FREQ2, 0x10)
        self.write_reg(CC1101_FREQ1, 0xB0)
        self.write_reg(CC1101_FREQ0, 0x71)

        # Modem setup: OOK
        closest_bw = min(
            BW_BITS_MAP.keys(),
            key=lambda x: abs(x - rx_bw_khz),
        )
        closest_dr = min(
            DATA_RATE_MAP.keys(),
            key=lambda x: abs(x - data_rate_kbps),
        )
        bw_bits = BW_BITS_MAP[closest_bw]
        drate_e, drate_m = DATA_RATE_MAP[closest_dr]
        mdmcfg4 = bw_bits | drate_e
        self.write_reg(CC1101_MDMCFG4, mdmcfg4)
        self.write_reg(CC1101_MDMCFG3, drate_m)
        self.write_reg(CC1101_MDMCFG2, 0x30)
        self.write_reg(CC1101_MDMCFG1, 0x22)
        self.write_reg(CC1101_MDMCFG0, 0xF8)

        self.write_reg(CC1101_DEVIATN, 0x00)

        self.write_reg(CC1101_MCSM2, 0x07)
        self.write_reg(CC1101_MCSM1, 0x30)
        self.write_reg(CC1101_MCSM0, 0x18)

        self.write_reg(CC1101_FOCCFG, 0x16)
        self.write_reg(CC1101_BSCFG, 0x6C)
        
        # Standard AGC (Not restricted, target amplitude 33dB)
        self.write_reg(CC1101_AGCCTRL2, 0x03) 
        self.write_reg(CC1101_AGCCTRL1, 0x40) 
        self.write_reg(CC1101_AGCCTRL0, 0x91) 

        self.write_reg(CC1101_WOREVT1, 0x87)
        self.write_reg(CC1101_WOREVT0, 0x6B)
        self.write_reg(CC1101_WORCTRL, 0xFB)

        self.write_reg(CC1101_FREND1, 0x56)
        self.write_reg(CC1101_FREND0, 0x11)

        self.write_reg(CC1101_FSCAL3, 0xE9)
        self.write_reg(CC1101_FSCAL2, 0x2A)
        self.write_reg(CC1101_FSCAL1, 0x00)
        self.write_reg(CC1101_FSCAL0, 0x1F)

        self.write_reg(CC1101_TEST2, 0x81)
        self.write_reg(CC1101_TEST1, 0x35)
        self.write_reg(CC1101_TEST0, 0x09)

    # Define _write_named_config_registers(), a named step in the decoding/support pipeline.
    def _write_named_config_registers(self, registers):
        reg_map = {
            "ADDR": CC1101_ADDR,
            "AGCCTRL0": CC1101_AGCCTRL0,
            "AGCCTRL1": CC1101_AGCCTRL1,
            "AGCCTRL2": CC1101_AGCCTRL2,
            "BSCFG": CC1101_BSCFG,
            "CHANNR": CC1101_CHANNR,
            "DEVIATN": CC1101_DEVIATN,
            "FIFOTHR": CC1101_FIFOTHR,
            "FOCCFG": CC1101_FOCCFG,
            "FREND0": CC1101_FREND0,
            "FREND1": CC1101_FREND1,
            "FREQ0": CC1101_FREQ0,
            "FREQ1": CC1101_FREQ1,
            "FREQ2": CC1101_FREQ2,
            "FSCAL0": CC1101_FSCAL0,
            "FSCAL1": CC1101_FSCAL1,
            "FSCAL2": CC1101_FSCAL2,
            "FSCAL3": CC1101_FSCAL3,
            "FSCTRL0": CC1101_FSCTRL0,
            "FSCTRL1": CC1101_FSCTRL1,
            "IOCFG0": CC1101_IOCFG0,
            "IOCFG1": CC1101_IOCFG1,
            "IOCFG2": CC1101_IOCFG2,
            "MCSM0": CC1101_MCSM0,
            "MCSM1": CC1101_MCSM1,
            "MCSM2": CC1101_MCSM2,
            "MDMCFG0": CC1101_MDMCFG0,
            "MDMCFG1": CC1101_MDMCFG1,
            "MDMCFG2": CC1101_MDMCFG2,
            "MDMCFG3": CC1101_MDMCFG3,
            "MDMCFG4": CC1101_MDMCFG4,
            "PKTCTRL0": CC1101_PKTCTRL0,
            "PKTCTRL1": CC1101_PKTCTRL1,
            "PKTLEN": CC1101_PKTLEN,
            "SYNC0": CC1101_SYNC0,
            "SYNC1": CC1101_SYNC1,
            "TEST0": CC1101_TEST0,
            "TEST1": CC1101_TEST1,
            "TEST2": CC1101_TEST2,
            "WORCTRL": CC1101_WORCTRL,
            "WOREVT0": CC1101_WOREVT0,
            "WOREVT1": CC1101_WOREVT1,
        }
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for name, value in registers.items():
            self.write_reg(reg_map[name], value)

    # Define configure_cc1101_async_ook(), a named step in the decoding/support pipeline.
    def configure_cc1101_async_ook(self, rx_bw_khz=None, data_rate_kbps=None, registers=None):
        """Configure async OOK using a device-supplied Flipper-style profile.

        registers is the source of truth for behavior preservation. The
        rx_bw_khz/data_rate_kbps arguments are retained as labels/overrides for
        experiment tracking, but this profile writes exact register bytes.
        """
        self.reset()

        self.strobe(CC1101_SIDLE)
        self.strobe(CC1101_SFRX)
        self.strobe(CC1101_SFTX)

        # Check this condition so only the matching signal/data case is handled here.
        if registers is None:
            registers = CC1101_ASYNC_OOK_REGISTERS
        self._write_named_config_registers(registers)

        self._log(LOG_RF, "configured Flipper-style OOK async at 433.92 MHz",
                  "rx_bw_khz=", rx_bw_khz, "data_rate_kbps=", data_rate_kbps)
        self.dump_basic_status()
        self.dump_key_config()

    # Define start_rx(), a named step in the decoding/support pipeline.
    def start_rx(self, timeout_ms=20):
        self.strobe(CC1101_SIDLE)
        self.strobe(CC1101_SFRX)
        self.strobe(CC1101_SRX)

        start = time.ticks_ms()
        seen = []

        # Continue looping while the runtime condition says more capture or processing work remains.
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            state = self.marcstate()
            seen.append(state)

            # Check this condition so only the matching signal/data case is handled here.
            if state == CC1101_MARCSTATE_RX:
                self._log(LOG_RF, "RX started, MARCSTATE=", state, "history=", seen)
                # Return the result to the caller so the next pipeline stage can continue.
                return True

            # Check this condition so only the matching signal/data case is handled here.
            if state in (
                CC1101_MARCSTATE_STARTCAL,
                CC1101_MARCSTATE_BWBOOST,
                CC1101_MARCSTATE_FS_LOCK,
                CC1101_MARCSTATE_IFADCON,
                CC1101_MARCSTATE_ENDCAL,
                CC1101_MARCSTATE_RX_END,
                CC1101_MARCSTATE_RX_RST,
            ):
                time.sleep_ms(1)
                # Skip the rest of this iteration and move on to the next candidate.
                continue

            # Check this condition so only the matching signal/data case is handled here.
            if state == CC1101_MARCSTATE_IDLE:
                time.sleep_ms(1)
                # Skip the rest of this iteration and move on to the next candidate.
                continue

            time.sleep_ms(1)

        self._log(LOG_RF, "RX did not settle, MARCSTATE history=", seen)
        # Return the result to the caller so the next pipeline stage can continue.
        return False

    # Define idle(), a named step in the decoding/support pipeline.
    def idle(self):
        self.strobe(CC1101_SIDLE)
        self._log(LOG_RF, "radio idled, MARCSTATE=", self.marcstate())

    # Define recover_rx(), a named step in the decoding/support pipeline.
    def recover_rx(self):
        self._log(LOG_RF, "recover_rx invoked")
        self.strobe(CC1101_SIDLE)
        self.strobe(CC1101_SFRX)
        self.strobe(CC1101_SRX)
        time.sleep_us(200)
        self._log(LOG_RF, "recover_rx complete, MARCSTATE=", self.marcstate())

    # Define gdo0_state(), a named step in the decoding/support pipeline.
    def gdo0_state(self):
        # Check this condition so only the matching signal/data case is handled here.
        if self.gdo0 is None:
            # Return the result to the caller so the next pipeline stage can continue.
            return None
        # Return the result to the caller so the next pipeline stage can continue.
        return self.gdo0.value()

    # Define gdo2_state(), a named step in the decoding/support pipeline.
    def gdo2_state(self):
        # Check this condition so only the matching signal/data case is handled here.
        if self.gdo2 is None:
            # Return the result to the caller so the next pipeline stage can continue.
            return None
        # Return the result to the caller so the next pipeline stage can continue.
        return self.gdo2.value()

    # Define dump_gdo(), a named step in the decoding/support pipeline.
    def dump_gdo(self):
        self._log(
            LOG_RF,
            "GDO0=",
            self.gdo0.value() if self.gdo0 else None,
            "GDO2=",
            self.gdo2.value() if self.gdo2 else None,
        )

    def sleep(self):
        """
        Put the CC1101 into its lowest-power state.

        The chip must first be in IDLE before the SPWD command is issued.
        The next SPI access automatically wakes the radio.
        """
        self.strobe(CC1101_SIDLE)
        self.strobe(CC1101_SPWD)

        # Give the chip a moment to enter power-down.
        time.sleep_us(10)

        self._log(LOG_RF, "radio sleeping")

    def wake(self):
        """
        Wake the CC1101 after SPWD.

        The first SPI access wakes the chip. Once awake, place the radio back
        into receive mode so async GDO0 output resumes.
        """
        # Any SPI transaction wakes the chip.
        self.strobe(CC1101_SNOP)

        # Allow the oscillator to stabilize.
        time.sleep_us(10)

        # Restore receive mode.
        self.start_rx()

        self._log(LOG_RF, "radio awake")
