"""Ubisys Control Unit C4 quirk."""

from typing import Any, Final

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ubisys import InputMode, UbisysCluster, UbisysInputConfigCluster


class UbisysC4InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the C4 with four inputs.

    Input 1: EP1, input_index 0
    Input 2: EP2, input_index 1
    Input 3: EP3, input_index 2
    Input 4: EP4, input_index 3
    No outputs, so no detached mode.
    """

    class AttributeDefs(BaseAttributeDefs):
        """C4 input configuration attributes for all four inputs."""

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=InputMode)
        input_mode_2: Final = ZCLAttributeDef(id=0x0001, type=InputMode)
        input_mode_3: Final = ZCLAttributeDef(id=0x0002, type=InputMode)
        input_mode_4: Final = ZCLAttributeDef(id=0x0003, type=InputMode)

    _ATTRIBUTE_DEFAULTS: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: InputMode.Toggle,
        AttributeDefs.input_mode_2.id: InputMode.Toggle,
        AttributeDefs.input_mode_3.id: InputMode.Toggle,
        AttributeDefs.input_mode_4.id: InputMode.Toggle,
    }

    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("input_mode_1", 0, 1),  # Input 1: index 0, source EP1
        ("input_mode_2", 1, 2),  # Input 2: index 1, source EP2
        ("input_mode_3", 2, 3),  # Input 3: index 2, source EP3
        ("input_mode_4", 3, 4),  # Input 4: index 3, source EP4
    )

    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = ()


(
    QuirkBuilder(manufacturer="ubisys", model="C4 (5504)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysC4InputConfigCluster)
    .enum(
        attribute_name=UbisysC4InputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=InputMode,
        cluster_id=UbisysC4InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .enum(
        attribute_name=UbisysC4InputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=InputMode,
        cluster_id=UbisysC4InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .enum(
        attribute_name=UbisysC4InputConfigCluster.AttributeDefs.input_mode_3.name,
        enum_class=InputMode,
        cluster_id=UbisysC4InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 3",
        translation_placeholders={"input_id": "3"},
    )
    .enum(
        attribute_name=UbisysC4InputConfigCluster.AttributeDefs.input_mode_4.name,
        enum_class=InputMode,
        cluster_id=UbisysC4InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 4",
        translation_placeholders={"input_id": "4"},
    )
    .device_automation_triggers(
        {
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_1): {
                ENDPOINT_ID: 1,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_2): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_3): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_3): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_3): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_4): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_4): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_4): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
        }
    )
    .add_to_registry()
)
