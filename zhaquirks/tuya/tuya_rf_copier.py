"""Tuya Smart RF Copier."""

import zigpy.types as t

from zhaquirks.builder import EntityType
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaIlluminance, TuyaQuirkBuilder


def _register_zrf01() -> None:
    """ZY-ZRF01 model.

    Supports RF frequencies 310, 315, 330, 390, 418, 430, 433, and 580 MHz.
    Illuminance range: 0-3000 lux.

    Note: Learning mode appears unnecessary; setting the button to "Learn" is sufficient.
    """

    class SlotStatus(t.enum8):
        """Per-slot learn status, matches raw Tuya DP values 0/1/2."""

        Learn = 0x00
        Saved = 0x01
        Delete = 0x02

    class Trigger(t.enum8):
        """Single-option replay trigger, matches raw Tuya DP value 0."""

        Transmit = 0x00

    quirk = (
        TuyaQuirkBuilder("_TZE284_tdg4ckyh", "TS0601")
        .tuya_switch(
            dp_id=117,
            attribute_name="rf_learning_mode",
            entity_type=EntityType.STANDARD,
            translation_key="rf_learning_mode",
            fallback_name="RF learning mode",
        )
        .tuya_switch(
            dp_id=118,
            attribute_name="long_packet_mode",
            entity_type=EntityType.STANDARD,
            translation_key="long_packet_mode",
            fallback_name="Long packet mode",
        )
        .tuya_illuminance(dp_id=119, illuminance_cfg=TuyaIlluminance)
    )

    for i in range(1, 9):
        (
            quirk.tuya_enum(
                dp_id=100 + i,
                attribute_name=f"button_{i}",
                enum_class=SlotStatus,
                translation_key=f"button_{i}_code",
                fallback_name=f"Button {i} code",
            )
            .tuya_dp_attribute(
                dp_id=108 + i,
                attribute_name=f"transmit_{i}",
                type=Trigger,
            )
            .write_attr_button(
                attribute_name=f"transmit_{i}",
                cluster_id=TUYA_CLUSTER_ID,
                attribute_value=Trigger.Transmit,
                translation_key=f"button_{i}_transmit",
                fallback_name=f"Button {i} transmit",
            )
        )

    quirk.add_to_registry()


_register_zrf01()
