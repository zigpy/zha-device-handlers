"""Tuya TS0726 switches."""

from zhaquirks.tuya.builder import TuyaQuirkBuilder

# Zemismart and BSEED 2-gang switches. Until the attribute read spell is cast,
# an OnOff command sent to either endpoint switches both gangs. Physical buttons
# are unaffected.
#
# Each gang is a child device, named like the channels of ZHA's automatic split.
# ZHA can't split TS0726 by model: other TS0726 switches expose scene buttons as
# extra OnOff endpoints, which would become channels of their own.
(
    TuyaQuirkBuilder("_TZ3000_icoxotza", "TS0726")
    .applies_to("_TZ3002_zjuvw9zf", "TS0726")
    .tuya_enchantment()
    .child_device(
        "1",
        endpoint_id=1,
        translation_key="channel",
        translation_placeholders={"index": "1"},
        fallback_name="Channel 1",
    )
    .child_device(
        "2",
        endpoint_id=2,
        translation_key="channel",
        translation_placeholders={"index": "2"},
        fallback_name="Channel 2",
    )
    .add_to_registry()
)  # fmt: skip
