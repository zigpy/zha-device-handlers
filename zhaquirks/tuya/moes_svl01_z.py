"""MOES SVL01-Z mmWave Radar Detection Smart Wall Light Switch."""

import zigpy.types as t

from zhaquirks.builder import NumberDeviceClass
from zhaquirks.tuya import PowerOnState
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class AutoOnMode(t.enum8):
    """Automatic-on channel selection."""

    off = 0x00
    all = 0x01
    ch1 = 0x02
    ch2 = 0x03
    ch3 = 0x04
    ch1_and_ch2 = 0x05
    ch2_and_ch3 = 0x06
    ch1_and_ch3 = 0x07


class AutoOffMode(t.enum8):
    """Automatic-off channel selection."""

    off = 0x00
    all = 0x01
    ch1 = 0x02
    ch2 = 0x03
    ch3 = 0x04
    ch1_and_ch2 = 0x05
    ch2_and_ch3 = 0x06
    ch1_and_ch3 = 0x07


(
    TuyaQuirkBuilder("_TZE200_llvwkkde", "TS0601")
    .tuya_enchantment(data_query_spell=True)
    .tuya_binary_sensor(
        dp_id=101,
        attribute_name="presence",
        device_class="occupancy",
        entity_type="standard",
        translation_key="presence",
        fallback_name="Presence",
    )
    .tuya_number(
        dp_id=102,
        type=t.uint8_t,
        attribute_name="sensitivity",
        min_value=0,
        max_value=19,
        step=1,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .tuya_number(
        dp_id=103,
        type=t.uint16_t,
        attribute_name="trigger_hold",
        min_value=5,
        max_value=28800,
        step=1,
        unit="s",
        device_class=NumberDeviceClass.DURATION,
        translation_key="trigger_hold",
        fallback_name="Trigger hold",
    )
    .tuya_enum(
        dp_id=14,
        attribute_name="power_on_state",
        enum_class=PowerOnState,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight",
        translation_key="backlight",
        fallback_name="Backlight",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="auto_on",
        enum_class=AutoOnMode,
        translation_key="auto_on",
        fallback_name="Auto on",
    )
    .tuya_enum(
        dp_id=105,
        attribute_name="auto_off",
        enum_class=AutoOffMode,
        translation_key="auto_off",
        fallback_name="Auto off",
    )
    .skip_configuration()
    .add_to_registry()
)
