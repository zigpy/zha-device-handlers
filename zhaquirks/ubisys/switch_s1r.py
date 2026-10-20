"""Ubisys Switching Actuator S1-R (Series 2) quirk."""

from typing import Any, Final

from zha.quirks import SE_POLL_SUMMATION
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import ButtonEvent, ButtonEventType, QuirkBuilder
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.ubisys import InputMode, UbisysCluster, UbisysInputConfigCluster


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_power_divisor.id: 10,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
    }


class UbisysS1RInputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the S1-R with two inputs.

    Input 1: EP2 -> EP1 (OnOff)
    Input 2: EP3 -> EP1 (OnOff)
    """

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id]

    class AttributeDefs(BaseAttributeDefs):
        """S1-R input configuration attributes for both inputs."""

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=InputMode)
        detached_1: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        input_mode_2: Final = ZCLAttributeDef(id=0x0002, type=InputMode)
        detached_2: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)

    _DEFAULT_VALUES: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: InputMode.Toggle,
        AttributeDefs.detached_1.id: t.Bool.false,
        AttributeDefs.input_mode_2.id: InputMode.Toggle,
        AttributeDefs.detached_2.id: t.Bool.true,
    }

    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("input_mode_1", 0, 2),  # Input 1: index 0, source EP2
        ("input_mode_2", 1, 3),  # Input 2: index 1, source EP3
    )

    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("detached_1", 2, 1),  # EP2 -> EP1
        ("detached_2", 3, 1),  # EP3 -> EP1
    )


(
    QuirkBuilder(manufacturer="ubisys", model="S1-R (5601)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysS1RInputConfigCluster)
    .enum(
        attribute_name=UbisysS1RInputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=InputMode,
        cluster_id=UbisysS1RInputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .switch(
        attribute_name=UbisysS1RInputConfigCluster.AttributeDefs.detached_1.name,
        cluster_id=UbisysS1RInputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .enum(
        attribute_name=UbisysS1RInputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=InputMode,
        cluster_id=UbisysS1RInputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .switch(
        attribute_name=UbisysS1RInputConfigCluster.AttributeDefs.detached_2.name,
        cluster_id=UbisysS1RInputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=1)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="1-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=1,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            # this also toggles light by default
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
        }
    )
    # Factory default input configuration (ubisys technical reference, InputActions):
    # each input is a push-button sending toggle when it goes down. The quirk's
    # "Toggle switch" and "On/off switch" input modes are for latching switches
    # instead (and also send toggle/off on release), so their commands are not
    # modeled as button events.
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_START,
                trigger=(COMMAND_CLICK, BUTTON_1),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=2,
        unique_id_suffix="button_1",
        translation_key="numbered_button",
        fallback_name="Button 1",
        translation_placeholders={"button_number": "1"},
    )
    .button_event(
        events=[
            ButtonEvent(
                event_type=ButtonEventType.PRESS_START,
                trigger=(COMMAND_CLICK, BUTTON_2),
            ),
        ],
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
        endpoint_id=3,
        unique_id_suffix="button_2",
        translation_key="numbered_button",
        fallback_name="Button 2",
        translation_placeholders={"button_number": "2"},
    )
    .add_to_registry()
)
