"""Tuya fingerbot."""

from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTime
import zigpy.types as t

from zhaquirks.const import BatterySize
from zhaquirks.tuya import TUYA_SEND_DATA
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class FingerBotMode(t.enum8):
    """FingerBot mode."""

    CLICK = 0x00
    SWITCH = 0x01
    PROGRAM = 0x02


class FingerBotReverse(t.enum8):
    """FingerBot reverse."""

    UP_ON = 0x00
    UP_OFF = 0x01


(
    TuyaQuirkBuilder("_TZ3210_dse8ogfy", "TS0001")
    .applies_to("_TZ3210_j4pdtz9v", "TS0001")
    .tuya_enum(
        dp_id=101,
        attribute_name="mode",
        enum_class=FingerBotMode,
        translation_key="mode",
        fallback_name="Mode",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="down_movement",
        min_value=50,
        type=t.uint16_t,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="down_movement",
        fallback_name="Down movement",
    )
    .tuya_number(
        dp_id=103,
        attribute_name="sustain_time",
        min_value=0,
        type=t.uint16_t,
        max_value=10,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="sustain_time",
        fallback_name="Sustain time",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="reverse",
        enum_class=FingerBotReverse,
        translation_key="reverse",
        fallback_name="Reverse",
    )
    .tuya_battery(dp_id=105, battery_type=BatterySize.CR2, battery_qty=1)
    .tuya_number(
        dp_id=106,
        attribute_name="up_movement",
        min_value=0,
        type=t.uint16_t,
        max_value=50,
        step=1,
        unit=PERCENTAGE,
        translation_key="up_movement",
        fallback_name="Up movement",
    )
    .tuya_switch(
        dp_id=107,
        attribute_name="touch_control",
        translation_key="touch_control",
        fallback_name="Touch control",
    )
    .tuya_enchantment()
    .add_to_registry(mcu_write_command=TUYA_SEND_DATA)
)
