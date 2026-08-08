from machine import Pin, SPI


class ManagedSPI:
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

        if self.miso_pin is not None:
            kwargs["miso"] = self.miso_pin

        self.spi = SPI(bus_id, **kwargs)

    def __repr__(self):
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


class SpiBusManager:
    _spi_instances = {}

    @classmethod
    def get_spi(cls, key, bus_id, sck, mosi, miso=None, baudrate=1_000_000, polarity=0, phase=0):
        if key in cls._spi_instances:
            obj = cls._spi_instances[key]
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
        return obj