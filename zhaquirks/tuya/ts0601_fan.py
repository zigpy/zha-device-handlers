from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zhaquirks.tuya.builder import TuyaQuirkBuilder
import zigpy.types as t


class PowerOnState(t.enum8):
    """Tuya power on state enum."""

    Off = 0x00
    On = 0x01


class FanSpeed(t.enum8):
    """Enum for the fan's speed."""

    Level_1 = 0x00
    Level_2 = 0x01
    Level_3 = 0x02
    Level_4 = 0x03
    Level_5 = 0x04

(
    TuyaQuirkBuilder("_TZE284_z5jz7wpo", "TS0601")
    .tuya_switch(  # Fan switch
        dp_id=1,
        attribute_name="on_off",
        entity_type=EntityType.STANDARD,
        translation_key="switch",
        fallback_name="switch",
    )
    .tuya_enum(  # Fan speed. Unfortunately, when the device is turned by changing this value, the "on_off"-value does not change accordingly. In the Tuya-app, it is not possible to change the fan's speed when the device is turned off. Thus this issue does not matter to them.
        dp_id=3,
        attribute_name="speed",
        enum_class=FanSpeed,
        translation_key="speed",
        fallback_name="Speed",
        entity_type=EntityType.STANDARD,
    )
    # I tried using a "tuya_number" instead of a tuya_enum. The following displayed the value correctly (even though one off from the device's display), but does not let me set the value via ZHA.
    # .tuya_number(
    #    dp_id=3,
    #    attribute_name="speed",
    #    type=t.uint16_t,
    #    entity_type=EntityType.STANDARD,
    #    device_class=NumberDeviceClass.SPEED,
    #    unit=None,
    #    min_value=0,
    #    max_value=4,
    #    step=1,
    #    translation_key="speed",
    #    fallback_name="fan speed",
    # )
    .tuya_number(  # Fan countdown -> after a certain number of seconds, the device will change toggle the on-off-state. If it is toggled by some other source in the meantime, the countdown is deactivated.
        dp_id=2,
        attribute_name="timer_duration",
        type=t.uint16_t,
        entity_type=EntityType.STANDARD,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        min_value=0,
        max_value=43200,
        step=1,
        translation_key="timer_duration",
        fallback_name="timer",
    )
    .tuya_enum(  # The app offers three states: on, off and remember last state. The latter does not work, so I don't offer it.
        dp_id=11,
        attribute_name="power_on_state",
        enum_class=PowerOnState,
        translation_key="power_on_state",
        fallback_name="Power On State",
    )
    # According to the Tuya-App (when paired to a Tuya-gateway) and the guide to find DPs (https://www.zigbee2mqtt.io/advanced/support-new-devices/03_find_tuya_data_points.html),
    # the device offers two more DPs (both are also not available in Zigbee2Mqtt)
    # 10 ("Mode"): This has only one possible value: "white". There is no reason to include it.
    # 12 ("Indicator status setting"): It has three values in the App: "Indicator off", "Indicate on/off status (The status of the indicator signals that the fan is on or off)", "Indicate switch position (When the fan is off, it can indicate the position of the switch at night)". This setting seems to not be working at all. This setting does not work. It does not change anything on the device.
    .skip_configuration()
    .add_to_registry()
)
