# -----------------------------------------------------------------------------
# managed_spi.py
# Small SPI ownership wrapper used so radio access is explicit and predictable on MicroPython boards.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

from machine import Pin, SPI


# Define the ManagedSPI class, which groups related state and behavior for this stage.
class ManagedSPI:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self, key, bus_id, sck, mosi, miso=None, baudrate=1_000_000, polarity=0, phase=0):
        self.key = key
        self.bus_id = bus_id
        self.sck_pin_num = sck
        self.mosi_pin_num = mosi
        self.miso_pin_num = miso
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase

        # Keep actual Pin objects around
        self.sck_pin = Pin(sck) if sck is not None else None
        self.mosi_pin = Pin(mosi) if mosi is not None else None
        self.miso_pin = Pin(miso, Pin.IN) if miso is not None else None

        kwargs = {
            "baudrate": baudrate,
            "polarity": polarity,
            "phase": phase,
            "sck": self.sck_pin,
            "mosi": self.mosi_pin,
        }

        # Check this condition so only the matching signal/data case is handled here.
        if self.miso_pin is not None:
            kwargs["miso"] = self.miso_pin

        self.spi = SPI(bus_id, **kwargs)

    # Define __repr__(), a named step in the decoding/support pipeline.
    def __repr__(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return (
            "ManagedSPI("
            "key={!r}, bus_id={}, sck={}, mosi={}, miso={}, baudrate={}, polarity={}, phase={}"
            ")".format(
                self.key,
                self.bus_id,
                self.sck_pin_num,
                self.mosi_pin_num,
                self.miso_pin_num,
                self.baudrate,
                self.polarity,
                self.phase,
            )
        )


# Define the SpiBusManager class, which groups related state and behavior for this stage.
class SpiBusManager:
    _spi_instances = {}

    @classmethod
    # Define get_spi(), a named step in the decoding/support pipeline.
    def get_spi(cls, key, bus_id, sck, mosi, miso=None, baudrate=1_000_000, polarity=0, phase=0):
        # Check this condition so only the matching signal/data case is handled here.
        if key in cls._spi_instances:
            obj = cls._spi_instances[key]
            # Check this condition so only the matching signal/data case is handled here.
            if (
                obj.bus_id != bus_id
                or obj.sck_pin_num != sck
                or obj.mosi_pin_num != mosi
                or obj.miso_pin_num != miso
                or obj.baudrate != baudrate
                or obj.polarity != polarity
                or obj.phase != phase
            ):
                raise ValueError("SPI key '{}' already exists with different configuration".format(key))
            # Return the result to the caller so the next pipeline stage can continue.
            return obj

        obj = ManagedSPI(
            key=key,
            bus_id=bus_id,
            sck=sck,
            mosi=mosi,
            miso=miso,
            baudrate=baudrate,
            polarity=polarity,
            phase=phase,
        )
        cls._spi_instances[key] = obj
        # Return the result to the caller so the next pipeline stage can continue.
        return obj
