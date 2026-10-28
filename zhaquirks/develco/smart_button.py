"""Smart button."""

from typing import Final

import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import EntityType, QuirkBuilder, UnitOfTime
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import BUTTON, CLUSTER_ID, COMMAND, COMMAND_CLICK, ENDPOINT_ID


class LedColors(t.enum8):
    """LED color options."""

    Off = 0
    Red = 1
    Green = 2
    Yellow = 3


class CustomOnOff(CustomCluster, OnOff):
    """Custom OnOff cluster to prevent entity creation."""

    cluster_id = OnOff.cluster_id

    class AttributeDefs(OnOff.AttributeDefs):
        """Add manufacturer specific attributes for button configuration."""

        button_press_action_delay: Final = ZCLAttributeDef(
            id=0x8001,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=0x1015,
        )
        button_press_blink_led: Final = ZCLAttributeDef(
            id=0x8002,
            type=LedColors,
            access="rw",
            manufacturer_code=0x1015,
        )


(
    QuirkBuilder("frient A/S", "SBTZB-110")
    .applies_to("Develco Products A/S", "SBTZB-110")
    .replaces(CustomOnOff, endpoint_id=32, cluster_type=ClusterType.Client)
    .prevent_default_entity_creation(
        endpoint_id=32,
        cluster_id=OnOff.cluster_id,
        function=lambda entity: entity.device_class == "opening",
    )
    .prevent_default_entity_creation(
        endpoint_id=32,
        cluster_id=BinaryInput.cluster_id,
        function=lambda entity: entity.translation_key == "binary_input",
    )
    .number(
        attribute_name=CustomOnOff.AttributeDefs.button_press_action_delay.name,
        cluster_id=CustomOnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=32,
        min_value=0,
        max_value=8000,
        unit=UnitOfTime.MILLISECONDS,
        step=1,
        mode="box",
        translation_key="button_press_action_delay",
        fallback_name="Button press action delay",
    )
    .enum(
        attribute_name=CustomOnOff.AttributeDefs.button_press_blink_led.name,
        enum_class=LedColors,
        cluster_id=CustomOnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=32,
        entity_type=EntityType.CONFIG,
        translation_key="button_press_blink_led",
        fallback_name="LED color",
    )
    .device_automation_triggers(
        {
            (COMMAND_CLICK, BUTTON): {
                ENDPOINT_ID: 32,
                CLUSTER_ID: int(OnOff.cluster_id),
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    .add_to_registry()
)
