"""SmartPad TS0601 two-gang Zigbee switch with controllable LED indicators.

Matches the confirmed manufacturer/model and EF00 MCU cluster, independent of
IEEE address. LED-mode, child-lock and restore-state writes are disabled.
"""

from typing import Any

from zigpy.device import Device
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import PERCENTAGE, EntityType
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster


def is_smartpad_ts0601(device: Device) -> bool:
    """Avoid matching devices without the Tuya MCU input cluster."""
    endpoint = device.endpoints.get(1)
    return endpoint is not None and TuyaMCUCluster.cluster_id in endpoint.in_clusters


class LedColor(t.enum8):
    """DP103/104 colors; all nine confirmed by the owner on 2026-11-26."""

    Red = 0
    Blue = 1
    Green = 2
    White = 3
    Yellow = 4
    Magenta = 5
    Cyan = 6
    Warm_white = 7
    Warm_yellow = 8


class SmartPadTuyaCluster(TuyaMCUCluster):
    """Reject writes to observational DPs, including via attribute UI."""

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, Any],
        **kwargs: Any,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Validate the complete request before any datapoint is written."""
        allowed = {
            "relay_1",
            "relay_2",
            "led_on_color",
            "led_off_color",
            "led_brightness",
            "led_enable",
        }
        records = self._write_attr_records(attributes)
        for record in records:
            name = self.attributes[record.attrid].name
            value = record.value.value
            if (
                name not in allowed
                or (
                    name in {"led_on_color", "led_off_color"}
                    and int(value) not in range(9)
                )
                or (name == "led_brightness" and not 0 <= int(value) <= 100)
                or (
                    name in {"relay_1", "relay_2", "led_enable"}
                    and int(value) not in (0, 1)
                )
            ):
                return [
                    [
                        foundation.WriteAttributesStatusRecord(
                            foundation.Status.INVALID_VALUE, record.attrid
                        )
                    ]
                ]
        return await super().write_attributes(attributes, **kwargs)


(
    TuyaQuirkBuilder("_TZE28C1000000_zpvusbtv", "TS0601")
    .filter(is_smartpad_ts0601)
    .tuya_switch(
        1,
        "relay_1",
        entity_type=EntityType.STANDARD,
        translation_key="smartpad_channel_1",
        fallback_name="Channel 1",
    )
    .tuya_switch(
        2,
        "relay_2",
        entity_type=EntityType.STANDARD,
        translation_key="smartpad_channel_2",
        fallback_name="Channel 2",
    )
    .tuya_enum(
        103,
        "led_on_color",
        LedColor,
        translation_key="on_led_color",
        fallback_name="On LED color",
    )
    .tuya_enum(
        104,
        "led_off_color",
        LedColor,
        translation_key="off_led_color",
        fallback_name="Off LED color",
    )
    .tuya_number(
        102,
        t.uint32_t,
        "led_brightness",
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        mode="slider",
        translation_key="smartpad_brightness",
        fallback_name="LED brightness",
    )
    .tuya_sensor(
        15,
        "led_mode",
        t.uint8_t,
        converter=int,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="smartpad_dp15",
        fallback_name="LED mode",
    )
    .tuya_switch(
        16, "led_enable", translation_key="led_indicator", fallback_name="LED indicator"
    )
    .command_button(
        "query_data",
        TuyaMCUCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="smartpad_refresh",
        fallback_name="Refresh datapoints",
    )
    .skip_configuration()
    .add_to_registry(replacement_cluster=SmartPadTuyaCluster)
)
