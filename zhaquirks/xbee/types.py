"""Types used to serialize and deserialize XBee commands.

Most of them are taken from https://github.com/zigpy/zigpy-xbee/blob/dev/zigpy_xbee/types.py
"""

import enum

import zigpy.types


class Bytes(bytes):
    """Bytes serializable class."""

    def serialize(self):
        """Serialize Bytes."""
        return self

    @classmethod
    def deserialize(cls, data):
        """Deserialize Bytes."""
        return cls(data), b""


class ATCommand(Bytes):
    """AT command serializable class."""

    @classmethod
    def deserialize(cls, data):
        """Deserialize ATCommand."""
        return cls(data[:2]), data[2:]


class int_t(int):
    """Signed int type."""

    _signed = True

    def serialize(self):
        """Serialize int_t."""
        return self.to_bytes(self._size, "big", signed=self._signed)

    @classmethod
    def deserialize(cls, data):
        """Deserialize int_t."""
        # Work around https://bugs.python.org/issue23640
        r = cls(int.from_bytes(data[: cls._size], "big", signed=cls._signed))
        data = data[cls._size :]
        return r, data


class uint_t(int_t):
    """Unsigned int type."""

    _signed = False


class uint8_t(uint_t):
    """Unsigned int 8 bit type."""

    _size = 1


class int16_t(int_t):
    """Signed int 16 bit type."""

    _size = 2


class uint16_t(uint_t):
    """Unsigned int 16 bit type."""

    _size = 2


class uint32_t(uint_t):
    """Unsigned int 32 bit type."""

    _size = 4


class uint64_t(uint_t):
    """Unsigned int 64 bit type."""

    _size = 8


class Bool(uint8_t, enum.Enum):
    """Boolean type with values true and false."""

    false = 0x00  # An alias for zero, used for clarity.
    true = 0x01  # An alias for one, used for clarity.


class EUI64(zigpy.types.EUI64):
    """EUI64 serializable class."""

    @classmethod
    def deserialize(cls, data):
        """Deserialize EUI64."""
        r, data = super().deserialize(data)
        return cls(r[::-1]), data

    def serialize(self):
        """Serialize EUI64."""
        assert self._length == len(self)
        return super().serialize()[::-1]


class FrameId(uint8_t):
    """Frame ID type."""

    pass


class NWK(int):
    """Network address serializable class."""

    _signed = False
    _size = 2

    def serialize(self):
        """Serialize NWK."""
        return self.to_bytes(self._size, "big", signed=self._signed)

    @classmethod
    def deserialize(cls, data):
        """Deserialize NWK."""
        r = cls(int.from_bytes(data[: cls._size], "big", signed=cls._signed))
        data = data[cls._size :]
        return r, data


class BinaryString(str):
    """Class to parse and serialize binary data as string."""

    def serialize(self):
        """Serialize string into bytes."""
        return bytes(self, encoding="latin1")

    @classmethod
    def deserialize(cls, data):
        """Interpret data as string."""
        data = str(data, encoding="latin1")
        return (cls(data), b"")


class IOSample(dict):
    """Parse an XBee IO sample report."""

    serialize = None

    @classmethod
    def deserialize(cls, data):
        """Deserialize an xbee IO sample report.

        xbee digital sample format
        Sample set count byte 0
        Digital mask byte 1, 2
        Analog mask byte 3
        Digital samples byte 4, 5 (if any sample exists)
        Analog Sample, 2 bytes per
        """
        sample_sets = int.from_bytes(data[0:1], byteorder="big")
        if sample_sets != 1:
            raise ValueError("Number of sets is not 1")
        digital_mask = data[1:3]
        analog_mask = data[3:4]
        digital_sample = data[4:6]
        num_bits = 15
        digital_pins = [
            (int.from_bytes(digital_mask, byteorder="big") >> bit) & 1
            for bit in range(num_bits - 1, -1, -1)
        ]
        digital_pins = list(reversed(digital_pins))
        analog_pins = [
            (int.from_bytes(analog_mask, byteorder="big") >> bit) & 1
            for bit in range(8 - 1, -1, -1)
        ]
        analog_pins = list(reversed(analog_pins))
        if 1 in digital_pins:
            digital_samples = [
                (int.from_bytes(digital_sample, byteorder="big") >> bit) & 1
                for bit in range(num_bits - 1, -1, -1)
            ]
            digital_samples = list(reversed(digital_samples))
            sample_index = 6
        else:
            # skip digital samples block
            digital_samples = digital_pins
            sample_index = 4
        analog_samples = []
        for apin in analog_pins:
            if apin == 1:
                analog_samples.append(
                    int.from_bytes(
                        data[sample_index : sample_index + 2], byteorder="big"
                    )
                )
                sample_index += 2
            else:
                analog_samples.append(None)
        for dpin in range(len(digital_pins)):
            if digital_pins[dpin] == 0:
                digital_samples[dpin] = None

        return (
            {
                "digital_samples": digital_samples,
                "analog_samples": analog_samples,
            },
            data[sample_index:],
        )
