"""Ubisys Switching Actuator S1 quirk."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.const import BUTTON, CLUSTER_ID, COMMAND, COMMAND_CLICK, ENDPOINT_ID
from zhaquirks.quirk_ids import SE_POLL_SUMMATION


class UbisysElectricalMeasurement(CustomCluster, ElectricalMeasurement):
    """Sets divisor attributes missing on the device."""

    _CONSTANT_ATTRIBUTES = {
        ElectricalMeasurement.AttributeDefs.ac_current_divisor.id: 1000,
        ElectricalMeasurement.AttributeDefs.ac_frequency_divisor.id: 1000,
    }


class UbisysCluster(CustomCluster):
    """Ubisys custom cluster 0xFC00."""

    cluster_id = 0xFC00
    name = "Ubisys Cluster 0xFC00"
    ep_attribute = "ubisys_cluster_0xfc00"

    class AttributeDefs(BaseAttributeDefs):
        """Ubisys attribute definitions."""

        input_configurations: Final = ZCLAttributeDef(
            id=0x0000, type=t.LVList[t.uint8_t, t.uint16_t], manufacturer_code=None
        )
        input_actions: Final = ZCLAttributeDef(
            id=0x0001, type=t.LVList[t.LVBytes, t.uint16_t], manufacturer_code=None
        )
        cluster_revision: Final = ZCLAttributeDef(
            id=0xFFFD, type=t.uint16_t, manufacturer_code=None
        )


(
    QuirkBuilder(manufacturer="ubisys", model="S1 (5501)")
    .replaces(UbisysCluster, endpoint_id=232)
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
        }
    )
    .add_to_registry()
)
