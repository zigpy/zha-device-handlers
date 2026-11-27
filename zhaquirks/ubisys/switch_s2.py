"""Ubisys Switching Actuator S2 quirk."""

from typing import Any, Final

from zha.quirks import SE_POLL_SUMMATION
import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
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
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysS2InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the S2 with two inputs.

    Input 1: EP3 -> EP1 (OnOff)
    Input 2: EP4 -> EP2 (OnOff)
    """

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id]

    class AttributeDefs(BaseAttributeDefs):
        """S2 input configuration attributes for both inputs."""

        input_mode_1: Final = ZCLAttributeDef(id=0x0000, type=InputMode)
        detached_1: Final = ZCLAttributeDef(id=0x0001, type=t.Bool)
        input_mode_2: Final = ZCLAttributeDef(id=0x0002, type=InputMode)
        detached_2: Final = ZCLAttributeDef(id=0x0003, type=t.Bool)

    _DEFAULT_VALUES: dict[int, Any] = {
        AttributeDefs.input_mode_1.id: InputMode.Toggle,
        AttributeDefs.detached_1.id: t.Bool.false,
        AttributeDefs.input_mode_2.id: InputMode.Toggle,
        AttributeDefs.detached_2.id: t.Bool.false,
    }

    _INPUT_MODE_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("input_mode_1", 0, 3),  # Input 1: index 0, source EP3
        ("input_mode_2", 1, 4),  # Input 2: index 1, source EP4
    )

    _DETACHED_CONFIG: tuple[tuple[str, int, int], ...] = (
        ("detached_1", 3, 1),  # EP3 -> EP1
        ("detached_2", 4, 2),  # EP4 -> EP2
    )


(
    QuirkBuilder(manufacturer="ubisys", model="S2 (5502)")
    .applies_to(manufacturer="ubisys", model="S2-R (5602)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysS2InputConfigCluster)
    # Relays are on endpoints 1 and 2, the inputs that control them by default on
    # endpoints 3 and 4, so each channel's child device takes its relay's endpoint and
    # its input's endpoint. The input settings are all on endpoint 1 and are assigned
    # to their channel. The meter on endpoint 5 measures the whole device and stays on
    # the main device. The child device names the channel, so the entity names don't
    # number it.
    .child_device(
        "1",
        endpoint_ids=[1, 3],
        translation_key="channel",
        translation_placeholders={"index": "1"},
        fallback_name="Channel 1",
    )
    .child_device(
        "2",
        endpoint_ids=[2, 4],
        translation_key="channel",
        translation_placeholders={"index": "2"},
        fallback_name="Channel 2",
    )
    .enum(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=InputMode,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        child_device_id="1",
        translation_key="input_mode",
        fallback_name="Input mode",
    )
    .switch(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.detached_1.name,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        child_device_id="1",
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .enum(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=InputMode,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        child_device_id="2",
        translation_key="input_mode",
        fallback_name="Input mode",
    )
    .switch(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.detached_2.name,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        child_device_id="2",
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=5)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=5,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="5-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=5,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # Summation received stuck at 102648430084968, hide for now
    .change_entity_metadata(
        endpoint_id=5,
        cluster_id=Metering.cluster_id,
        unique_id_suffix="summation_received",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_1): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_1): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON_2): {
                ENDPOINT_ID: 4,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON_2): {
                ENDPOINT_ID: 4,
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
        endpoint_id=3,
        unique_id_suffix="button_1",
        translation_key="button",
        fallback_name="Button",
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
        endpoint_id=4,
        unique_id_suffix="button_2",
        translation_key="button",
        fallback_name="Button",
    )
    .add_to_registry()
)
