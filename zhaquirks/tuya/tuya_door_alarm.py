"""Tuya door/window sensor with siren alarm (_TZE284_u8ouaqsz / TS0601)."""

import zigpy.types as t

from zhaquirks.builder import PERCENTAGE, EntityType, UnitOfTime
from zhaquirks.tuya import TuyaPowerConfigurationCluster2AAA
from zhaquirks.tuya.builder import TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE284_u8ouaqsz", "TS0601")
    # DP 1: magnetic contact of the door/window
    .tuya_contact(dp_id=1)
    # DP 2: battery level in percent (two AAA cells).
    # scale=2 is the Tuya convention: ZHA divides the battery attribute by two
    # again ("per zcl specs battery percent is reported at 200%").
    .tuya_battery(dp_id=2, power_cfg=TuyaPowerConfigurationCluster2AAA)
    # DP 101: siren
    .tuya_switch(
        dp_id=101,
        attribute_name="alarm",
        entity_type=EntityType.CONFIG,
        translation_key="alarm",
        fallback_name="Alarm",
    )
    # DP 102: blinking light during the alarm
    .tuya_switch(
        dp_id=102,
        attribute_name="strobe",
        entity_type=EntityType.CONFIG,
        translation_key="strobe",
        fallback_name="Strobe",
    )
    # DP 103: siren volume in percent
    .tuya_number(
        dp_id=103,
        attribute_name="volume",
        type=t.uint16_t,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        translation_key="volume",
        fallback_name="Volume",
    )
    # DP 104: siren duration in seconds
    .tuya_number(
        dp_id=104,
        attribute_name="duration",
        type=t.uint16_t,
        min_value=3,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="duration",
        fallback_name="Duration",
    )
    # No skip_configuration(): the device only accepts the arming datapoint
    # (DP 101) after the Tuya "spell" has been cast, which happens during the
    # normal configuration. Without it the device answers the write with its
    # current state and never arms.
    .add_to_registry()
)
