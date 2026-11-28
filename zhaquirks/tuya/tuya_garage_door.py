"""Tuya garage door openers (TS0603).

Adds v2 quirk support for TS0603-based garage door openers that are not
covered by the legacy ts0601_garage.py quirk.

Devices:
  - _TZE608_c75zqghm (TS0603) — single toggle button, inverted door contact
  - _TZE608_fmemczv1 (TS0603) — single toggle button, inverted door contact

TS0601 variants (_TZE200_nklqjk62, _TZE204_nklqjk62, _TZE284_nklqjk62) are
handled by the legacy ts0601_garage.py quirk.
"""

import zigpy.types as t

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    NumberDeviceClass,
    UnitOfTime,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaDoorAlarm(t.enum8):
    """Tuya garage door alarm status enum."""

    Open_time_alarm = 0x00
    Run_time_alarm = 0x01
    Normal = 0x02


(
    TuyaQuirkBuilder("_TZE608_c75zqghm", "TS0603")
    .applies_to("_TZE608_fmemczv1", "TS0603")
    .tuya_dp_attribute(
        dp_id=1,
        attribute_name="garage_door_trigger",
        type=t.Bool,
    )
    .write_attr_button(
        attribute_name="garage_door_trigger",
        entity_type=EntityType.STANDARD,
        cluster_id=TUYA_CLUSTER_ID,
        attribute_value=True,
        translation_key="toggle_door",
        fallback_name="Toggle door",
    )
    .tuya_number(
        dp_id=2,
        attribute_name="relay_countdown",
        type=t.uint32_t,
        min_value=0,
        max_value=43200,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="relay_countdown",
        fallback_name="Relay countdown",
    )
    .tuya_dp_attribute(
        dp_id=3,
        attribute_name="door_contact",
        type=t.Bool,
        dp_converter=lambda x: not x,
    )
    .binary_sensor(
        attribute_name="door_contact",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.GARAGE_DOOR,
        translation_key="door_contact",
        fallback_name="Door state",
    )
    .tuya_number(
        dp_id=4,
        attribute_name="run_time",
        type=t.uint32_t,
        min_value=0,
        max_value=120,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="run_time",
        fallback_name="Run time",
    )
    .tuya_number(
        dp_id=5,
        attribute_name="open_alarm_time",
        type=t.uint32_t,
        min_value=0,
        max_value=86400,
        step=1,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="open_alarm_time",
        fallback_name="Open alarm time",
    )
    .tuya_enum(
        dp_id=12,
        attribute_name="alarm",
        enum_class=TuyaDoorAlarm,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="alarm",
        fallback_name="Alarm",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
