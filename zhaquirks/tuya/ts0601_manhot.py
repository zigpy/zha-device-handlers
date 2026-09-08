"""Manhot MH03 series OLED screen switches."""

from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import PERCENTAGE, EntityType, UnitOfTime
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class MH03PowerOnState(t.enum8):
    """Relay state restored after a power outage (DP 14)."""

    Off = 0x00
    On = 0x01
    Memory = 0x02


class MH03LightMode(t.enum8):
    """Indicator LED mode (DP 15)."""

    Disabled = 0x00
    Relay = 0x01
    Position = 0x02


class MH03Color(t.enum8):
    """Indicator LED colour (DP 102 when on, DP 103 when off)."""

    Red = 0x00
    Orange = 0x01
    Green = 0x02
    Cyan = 0x03
    Blue = 0x04
    Purple = 0x05
    Magenta = 0x06
    Cold_white = 0x07
    Warm_yellow = 0x08


class MH03PressFun(t.enum8):
    """Long press target (DP 118 all-on, DP 119 all-off)."""

    Disable = 0x00
    Press_switch_1 = 0x01
    Press_switch_2 = 0x02


(
    # Manhot MH03-2Z-OLED, "OLED Screen Switch 2 Gang".
    # Datapoint map ported from zigbee-herdsman-converters,
    # src/devices/manhot.ts ("MH03-2Z-OLED").
    # On the tested unit the upper rocker is gang 2 (DP 2) and the lower one
    # is gang 1 (DP 1), matching the "switch 2" / "switch 1" labels the OLED
    # shows by default.
    TuyaQuirkBuilder("_TZE284_dnhhp8ew", "TS0601")
    .applies_to("_TZE28C1000000_dnhhp8ew", "TS0601")
    # The device only announces endpoint 1; gang 2 needs a virtual endpoint.
    .adds_endpoint(2, device_type=zha.DeviceType.ON_OFF_LIGHT_SWITCH)
    .tuya_onoff(dp_id=1, endpoint_id=1)
    .tuya_onoff(dp_id=2, endpoint_id=2)
    .tuya_number(
        dp_id=7,
        type=t.uint32_t,
        attribute_name="countdown_1",
        min_value=0,
        max_value=43200,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="countdown_1",
        fallback_name="Countdown 1",
    )
    .tuya_number(
        dp_id=8,
        type=t.uint32_t,
        attribute_name="countdown_2",
        min_value=0,
        max_value=43200,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="countdown_2",
        fallback_name="Countdown 2",
    )
    .tuya_enum(
        dp_id=14,
        attribute_name="power_on_state",
        enum_class=MH03PowerOnState,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .tuya_enum(
        dp_id=15,
        attribute_name="light_mode",
        enum_class=MH03LightMode,
        translation_key="light_mode",
        fallback_name="Indicator light mode",
    )
    .tuya_switch(
        dp_id=16,
        attribute_name="backlight_switch",
        entity_type=EntityType.CONFIG,
        translation_key="backlight_switch",
        fallback_name="Backlight",
    )
    .tuya_number(
        dp_id=101,
        type=t.uint32_t,
        attribute_name="backlight_lightness",
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="backlight_lightness",
        fallback_name="Backlight brightness",
    )
    .tuya_enum(
        dp_id=102,
        attribute_name="on_color",
        enum_class=MH03Color,
        translation_key="on_color",
        fallback_name="Light-on color",
    )
    .tuya_enum(
        dp_id=103,
        attribute_name="off_color",
        enum_class=MH03Color,
        translation_key="off_color",
        fallback_name="Light-off color",
    )
    .tuya_number(
        dp_id=104,
        type=t.uint32_t,
        attribute_name="displayoff_delay",
        min_value=10,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="displayoff_delay",
        fallback_name="Screen off delay",
    )
    .tuya_switch(
        dp_id=105,
        attribute_name="child_lock",
        entity_type=EntityType.CONFIG,
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    # DP 106/107 carry the per-gang labels rendered on the OLED screen.
    # There is no text entity platform in quirks v2, so they are exposed as
    # plain writable attributes (ZCL character string, 0xEF6A / 0xEF6B).
    .tuya_dp_attribute(
        dp_id=106,
        attribute_name="sw1_name",
        type=t.CharacterString,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .tuya_dp_attribute(
        dp_id=107,
        attribute_name="sw2_name",
        type=t.CharacterString,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .tuya_enum(
        dp_id=118,
        attribute_name="press_on_fun",
        enum_class=MH03PressFun,
        translation_key="press_on_fun",
        fallback_name="Long press all-on channel",
    )
    .tuya_enum(
        dp_id=119,
        attribute_name="press_off_fun",
        enum_class=MH03PressFun,
        translation_key="press_off_fun",
        fallback_name="Long press all-off channel",
    )
    .skip_configuration()
    .add_to_registry()
)
