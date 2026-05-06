"""Smart button."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import BinaryInput, OnOff
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import BUTTON, CLUSTER_ID, COMMAND, COMMAND_CLICK, ENDPOINT_ID


class LedColors(t.enum8):
    """LED color options."""

    OFF = 0
    RED = 1
    GREEN = 2
    YELLOW = 3


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


class ButtonState(t.enum8):
    """Button state values."""

    Released = 0
    Pressed = 1


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
        unique_id_suffix="button_press_action_delay",
        translation_key="frient_button_press_action_delay",
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
    .enum(
        attribute_name=BinaryInput.AttributeDefs.present_value.name,
        enum_class=ButtonState,
        cluster_id=BinaryInput.cluster_id,
        endpoint_id=32,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="button_state",
        fallback_name="Button state",
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
