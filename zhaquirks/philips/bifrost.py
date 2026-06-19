"""Encoder/decoder for the Philips Hue manufacturer-specific frame on cluster 0xFC03.

Spec: https://github.com/chrivers/bifrost/blob/master/doc/hue-zigbee-format.md

Each frame is a header (16-bit LE flag bitmap) followed by an ordered, packed
body where each set flag implies a fixed-size (or self-describing) field.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct

# Cluster 0xFC03 server command id for the multicolor / native-control frame.
HUE_FC03_CLUSTER_ID = 0xFC03
HUE_NATIVE_COMMAND_ID = 0x00

# Gradient color XY values are scaled against the wide-gamut bounds, not 0..1.
GRADIENT_MAX_X = 0.7347
GRADIENT_MAX_Y = 0.8264

# COLOR_XY uses the unit range 0..1 packed into 16-bit LE values.
_COLOR_XY_SCALE = 0xFFFF


class HueEffect(IntEnum):
    """Effect IDs accepted by EFFECT_TYPE."""

    NO_EFFECT = 0x00
    CANDLE = 0x01
    FIREPLACE = 0x02
    PRISM = 0x03
    SUNRISE = 0x09
    SPARKLE = 0x0A
    OPAL = 0x0B
    GLISTEN = 0x0C
    SUNSET = 0x0D
    UNDERWATER = 0x0E
    COSMOS = 0x0F
    SUNBEAM = 0x10
    ENCHANT = 0x11


class GradientStyle(IntEnum):
    """Style values accepted in GRADIENT_COLORS."""

    LINEAR = 0x00
    SCATTERED = 0x02
    MIRRORED = 0x04


# Header flag bit positions (independent of wire order).
_F_ON_OFF = 1 << 0
_F_BRIGHTNESS = 1 << 1
_F_COLOR_MIREK = 1 << 2
_F_COLOR_XY = 1 << 3
_F_FADE_SPEED = 1 << 4
_F_EFFECT_TYPE = 1 << 5
_F_GRADIENT_PARAMS = 1 << 6
_F_EFFECT_SPEED = 1 << 7
_F_GRADIENT_COLORS = 1 << 8


@dataclass(frozen=True)
class GradientColors:
    """Multi-color payload for gradient lightstrips."""

    style: GradientStyle
    colors: tuple[tuple[float, float], ...]  # (x, y), each in 0..GRADIENT_MAX_*

    def __post_init__(self) -> None:
        if not 1 <= len(self.colors) <= 9:
            raise ValueError(
                f"GRADIENT_COLORS must contain 1..9 colors, got {len(self.colors)}"
            )


@dataclass(frozen=True)
class HueFrame:
    """A Philips Hue native-control frame.

    Any subset of fields may be set; only set fields are transmitted, and
    unset properties retain their previous values on the device.
    """

    on_off: bool | None = None
    brightness: int | None = None  # 1..254
    color_mirek: int | None = None  # typically 153..500
    color_xy: tuple[float, float] | None = None  # each 0..1
    fade_speed: int | None = None  # 16-bit; 0 = instant, ~2..8 typical
    effect_type: HueEffect | None = None
    gradient_colors: GradientColors | None = None
    effect_speed: int | None = None  # 0..255
    gradient_params: tuple[float, float] | None = None  # (scale, offset), 0..31.875


def encode(frame: HueFrame) -> bytes:
    """Serialize `frame` into the wire format on cluster 0xFC03."""
    flags = 0
    body = bytearray()

    # Wire order is fixed (and differs from flag bit order).
    if frame.on_off is not None:
        flags |= _F_ON_OFF
        body.append(0x01 if frame.on_off else 0x00)

    if frame.brightness is not None:
        if not 1 <= frame.brightness <= 254:
            raise ValueError(f"BRIGHTNESS must be 1..254, got {frame.brightness}")
        flags |= _F_BRIGHTNESS
        body.append(frame.brightness)

    if frame.color_mirek is not None:
        flags |= _F_COLOR_MIREK
        body += struct.pack("<H", frame.color_mirek)

    if frame.color_xy is not None:
        x, y = frame.color_xy
        flags |= _F_COLOR_XY
        body += struct.pack(
            "<HH",
            _to_unit_u16(x),
            _to_unit_u16(y),
        )

    if frame.fade_speed is not None:
        flags |= _F_FADE_SPEED
        body += struct.pack("<H", frame.fade_speed)

    if frame.effect_type is not None:
        flags |= _F_EFFECT_TYPE
        body.append(int(frame.effect_type))

    if frame.gradient_colors is not None:
        flags |= _F_GRADIENT_COLORS
        body += _encode_gradient_colors(frame.gradient_colors)

    if frame.effect_speed is not None:
        if not 0 <= frame.effect_speed <= 255:
            raise ValueError(f"EFFECT_SPEED must be 0..255, got {frame.effect_speed}")
        flags |= _F_EFFECT_SPEED
        body.append(frame.effect_speed)

    if frame.gradient_params is not None:
        scale, offset = frame.gradient_params
        flags |= _F_GRADIENT_PARAMS
        body.append(_to_fixed_point_5_3(scale))
        body.append(_to_fixed_point_5_3(offset))

    return struct.pack("<H", flags) + bytes(body)


def decode(data: bytes) -> HueFrame:
    """Parse a wire-format frame back into a `HueFrame`."""
    if len(data) < 2:
        raise ValueError("frame too short to contain a header")

    flags = struct.unpack_from("<H", data, 0)[0]
    pos = 2

    kwargs: dict[str, object] = {}

    if flags & _F_ON_OFF:
        kwargs["on_off"] = bool(data[pos])
        pos += 1

    if flags & _F_BRIGHTNESS:
        kwargs["brightness"] = data[pos]
        pos += 1

    if flags & _F_COLOR_MIREK:
        kwargs["color_mirek"] = struct.unpack_from("<H", data, pos)[0]
        pos += 2

    if flags & _F_COLOR_XY:
        x_raw, y_raw = struct.unpack_from("<HH", data, pos)
        kwargs["color_xy"] = (
            x_raw / _COLOR_XY_SCALE,
            y_raw / _COLOR_XY_SCALE,
        )
        pos += 4

    if flags & _F_FADE_SPEED:
        kwargs["fade_speed"] = struct.unpack_from("<H", data, pos)[0]
        pos += 2

    if flags & _F_EFFECT_TYPE:
        kwargs["effect_type"] = HueEffect(data[pos])
        pos += 1

    if flags & _F_GRADIENT_COLORS:
        gradient, consumed = _decode_gradient_colors(data, pos)
        kwargs["gradient_colors"] = gradient
        pos += consumed

    if flags & _F_EFFECT_SPEED:
        kwargs["effect_speed"] = data[pos]
        pos += 1

    if flags & _F_GRADIENT_PARAMS:
        kwargs["gradient_params"] = (
            _from_fixed_point_5_3(data[pos]),
            _from_fixed_point_5_3(data[pos + 1]),
        )
        pos += 2

    if pos != len(data):
        raise ValueError(f"trailing bytes after decoding frame: {data[pos:].hex()}")

    return HueFrame(**kwargs)


def _to_unit_u16(value: float) -> int:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"unit value must be 0.0..1.0, got {value}")
    return round(value * _COLOR_XY_SCALE)


def _to_fixed_point_5_3(value: float) -> int:
    """Encode a fixed-point 5.3 value (upper 5 bits integer, lower 3 bits 1/8)."""
    if not 0.0 <= value <= 31.875:
        raise ValueError(f"fixed-point 5.3 value must be 0..31.875, got {value}")
    return round(value * 8) & 0xFF


def _from_fixed_point_5_3(byte: int) -> float:
    return byte / 8.0


def _encode_gradient_colors(g: GradientColors) -> bytes:
    body = bytearray()
    body.append((len(g.colors) << 4) & 0xF0)
    body.append(int(g.style))
    body += b"\x00\x00"  # reserved
    for x, y in g.colors:
        body += _pack_gradient_xy(x, y)

    return bytes([len(body)]) + bytes(body)


def _decode_gradient_colors(data: bytes, pos: int) -> tuple[GradientColors, int]:
    size = data[pos]  # bytes following this size byte
    block = data[pos + 1 : pos + 1 + size]
    if len(block) != size:
        raise ValueError("GRADIENT_COLORS block truncated")

    color_count = (block[0] >> 4) & 0x0F
    if block[0] & 0x0F != 0:
        raise ValueError("GRADIENT_COLORS reserved low nibble must be zero")
    style = GradientStyle(block[1])
    # block[2:4] reserved

    colors: list[tuple[float, float]] = []
    for i in range(color_count):
        offset = 4 + 3 * i
        if offset + 3 > len(block):
            raise ValueError("GRADIENT_COLORS truncated mid-color")
        colors.append(_unpack_gradient_xy(block[offset : offset + 3]))

    return GradientColors(style=style, colors=tuple(colors)), 1 + size


def _pack_gradient_xy(x: float, y: float) -> bytes:
    """Pack (x, y) into 3 bytes per the Bifrost 12-bit XY layout."""
    if not 0.0 <= x <= GRADIENT_MAX_X:
        raise ValueError(f"gradient X must be 0..{GRADIENT_MAX_X}, got {x}")
    if not 0.0 <= y <= GRADIENT_MAX_Y:
        raise ValueError(f"gradient Y must be 0..{GRADIENT_MAX_Y}, got {y}")
    xi = round(x / GRADIENT_MAX_X * 0xFFF)
    yi = round(y / GRADIENT_MAX_Y * 0xFFF)
    return bytes(
        [
            xi & 0xFF,
            ((xi >> 8) & 0x0F) | ((yi & 0x0F) << 4),
            (yi >> 4) & 0xFF,
        ]
    )


def _unpack_gradient_xy(b: bytes) -> tuple[float, float]:
    xi = b[0] | ((b[1] & 0x0F) << 8)
    yi = (b[2] << 4) | (b[1] >> 4)
    return (
        xi / 0xFFF * GRADIENT_MAX_X,
        yi / 0xFFF * GRADIENT_MAX_Y,
    )
