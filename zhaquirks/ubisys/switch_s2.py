"""Ubisys Switching Actuator S2 quirk."""

from typing import Any, Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

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
from zhaquirks.quirk_ids import SE_POLL_SUMMATION
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

    _ATTRIBUTE_DEFAULTS: dict[int, Any] = {
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
    .enum(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.input_mode_1.name,
        enum_class=InputMode,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .switch(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.detached_1.name,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 1",
        translation_placeholders={"input_id": "1"},
    )
    .enum(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.input_mode_2.name,
        enum_class=InputMode,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        translation_key="input_mode_id",
        fallback_name="Input mode 2",
        translation_placeholders={"input_id": "2"},
    )
    .switch(
        attribute_name=UbisysS2InputConfigCluster.AttributeDefs.detached_2.name,
        cluster_id=UbisysS2InputConfigCluster.cluster_id,
        translation_key="detached_id",
        fallback_name="Detached mode 2",
        translation_placeholders={"input_id": "2"},
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
    .add_to_registry()
)
