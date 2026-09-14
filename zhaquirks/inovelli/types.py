"""Types for inovelli."""

from zigpy import types


class MMWaveArea(types.Struct):
    """A single mmWave sensor area definition.

    Used for interference, detection, and stay areas on the VZM32-SN. Bounds
    are in millimeters on the x (width/left-right), y (depth/near-far), and
    z (height/floor-ceiling) axes, relative to the switch.
    """

    x_min: types.int16s
    x_max: types.int16s
    y_min: types.int16s
    y_max: types.int16s
    z_min: types.int16s
    z_max: types.int16s


class MMWaveTarget(types.Struct):
    """A single detected target reported by the mmWave radar.

    Positions are in millimeters. dop is the Doppler velocity and target_id is
    a device-assigned tracking identifier.
    """

    x: types.int16s
    y: types.int16s
    z: types.int16s
    dop: types.int16s
    target_id: types.int8s


class AllLEDEffectType(types.enum8):
    """All LED effect type for Inovelli Blue Series switch."""

    Off = 0x00
    Solid = 0x01
    Fast_Blink = 0x02
    Slow_Blink = 0x03
    Pulse = 0x04
    Chase = 0x05
    Open_Close = 0x06
    Small_To_Big = 0x07
    Aurora = 0x08
    Slow_Falling = 0x09
    Medium_Falling = 0x0A
    Fast_Falling = 0x0B
    Slow_Rising = 0x0C
    Medium_Rising = 0x0D
    Fast_Rising = 0x0E
    Medium_Blink = 0x0F
    Slow_Chase = 0x10
    Fast_Chase = 0x11
    Fast_Siren = 0x12
    Slow_Siren = 0x13
    Clear = 0xFF


class SingleLEDEffectType(types.enum8):
    """Single LED effect type for Inovelli Blue Series switch."""

    Off = 0x00
    Solid = 0x01
    Fast_Blink = 0x02
    Slow_Blink = 0x03
    Pulse = 0x04
    Chase = 0x05
    Falling = 0x06
    Rising = 0x07
    Aurora = 0x08
    Clear = 0xFF
