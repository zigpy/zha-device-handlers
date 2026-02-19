"""Ubisys Dimmer D1 quirk."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl, OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_CLICK,
    ENDPOINT_ID,
)
from zhaquirks.quirk_ids import SE_POLL_SUMMATION
from zhaquirks.ubisys import InputMode, UbisysCluster, UbisysInputConfigCluster


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysD1InputConfigCluster(UbisysInputConfigCluster):
    """Input configuration for the D1.

    EP2 -> EP1 with OnOff + LevelControl self-bindings.
    """

    BIND_CLUSTERS: list[int] = [OnOff.cluster_id, LevelControl.cluster_id]


(
    QuirkBuilder(manufacturer="ubisys", model="D1 (5503)")
    .replaces(UbisysCluster, endpoint_id=232)
    .adds(UbisysD1InputConfigCluster)
    .enum(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.input_mode.name,
        enum_class=InputMode,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="input_mode",
        fallback_name="Input mode",
    )
    .switch(
        attribute_name=UbisysD1InputConfigCluster.AttributeDefs.detached.name,
        cluster_id=UbisysD1InputConfigCluster.cluster_id,
        translation_key="detached",
        fallback_name="Detached mode",
    )
    .replaces(UbisysElectricalMeasurement, endpoint_id=4)
    # The device exposes total active power on multiple attributes,
    # but only supports attribute reporting on the SE "instantaneous demand" attribute,
    # so we disable the other entities by default
    .change_entity_metadata(
        endpoint_id=4,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="4-2820",  # no translation key and no actual suffix for this
        new_entity_registry_enabled_default=False,
    )
    .change_entity_metadata(
        endpoint_id=4,
        cluster_id=ElectricalMeasurement.cluster_id,
        unique_id_suffix="total_active_power",
        new_entity_registry_enabled_default=False,
    )
    # SmartEnergy summation attributes do not support attribute reporting, need polling
    .exposes_feature(SE_POLL_SUMMATION)
    .device_automation_triggers(
        {
            # this also toggles light by default
            # XXX: move_with_on_off + stop_with_on_off are also fired when holding down
            #  move_with_on_off with move_mode 0 and 1
            (COMMAND_CLICK, BUTTON_1): {
                ENDPOINT_ID: 2,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
            # XXX: move_with_on_off + stop_with_on_off are also fired when holding down
            #  move_with_on_off with move_mode 0 and 1
            (COMMAND_CLICK, BUTTON_2): {
                ENDPOINT_ID: 3,
                CLUSTER_ID: OnOff.cluster_id,
                COMMAND: OnOff.ServerCommandDefs.toggle.name,
            },
        }
    )
    .add_to_registry()
)
