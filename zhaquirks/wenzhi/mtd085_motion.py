"""Wenzhi/LeapMMW MTD085-ZB mmWave presence sensor.

These TS0225 variants expose IAS Zone without a Tuya MCU cluster. Only motion
detection is supported; illuminance, distance and configuration are unavailable.
The Tuya attribute-read spell is required to initialize occupancy reporting.
"""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZ321C_fkzihax8", "TS0225")
    .applies_to("_TZ321C_4slreunp", "TS0225")
    .tuya_enchantment()
    .add_to_registry()
)
