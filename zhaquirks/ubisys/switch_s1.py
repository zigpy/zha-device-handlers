"""Ubisys Switching Actuator S1 quirk."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.const import (
    BUTTON,
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


(
    QuirkBuilder(manufacturer="ubisys", model="S1 (5501)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysInputConfigCluster)
    .enum(
        attribute_name=UbisysInputConfigCluster.AttributeDefs.input_mode.name,
        enum_class=InputMode,
        cluster_id=UbisysInputConfigCluster.cluster_id,
        translation_key="input_mode",
        fallback_name="Input mode",
    )
    .switch(
        attribute_name=UbisysInputConfigCluster.AttributeDefs.detached.name,
        cluster_id=UbisysInputConfigCluster.cluster_id,
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=3)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="3-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=3,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            # this also toggles light by default, but on up + down, so normal switch
            (COMMAND_CLICK, BUTTON): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            (TURN_ON, BUTTON): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.on.name,
            },
            (TURN_OFF, BUTTON): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.off.name,
            },
        }
    )
    .add_to_registry()
)
