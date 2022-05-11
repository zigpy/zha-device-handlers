"""Tuya Garden Watering"""

from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time, PowerConfiguration

from zigpy.zcl.clusters.measurement import FlowMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.tuya import DPToAttributeMapping, TuyaManufCluster, TuyaLocalCluster
from zhaquirks.tuya.mcu import TuyaOnOff, TuyaOnOffManufCluster

class TuyaGardenWateringWaterConsumed(FlowMeasurement, TuyaLocalCluster):
    """Tuya Water consumed cluster."""

class TuyaGardenWateringPowerConfiguration(PowerConfiguration, TuyaLocalCluster):
    """Tuya PowerConfiguration."""

class TuyaGardenManufCluster(TuyaOnOffManufCluster):
    """On/Off Tuya cluster with extra device attributes."""

    dp_to_attribute: Dict[
        int, DPToAttributeMapping
    ] = TuyaOnOffManufCluster.dp_to_attribute.copy()

    dp_to_attribute.update(
        {
            5: DPToAttributeMapping(
                TuyaGardenWateringWaterConsumed.ep_attribute,
                "measured_value",
                lambda x: x
            )
        }
    )

    dp_to_attribute.update(
        {
            7: DPToAttributeMapping(
                TuyaGardenWateringPowerConfiguration.ep_attribute,
                "battery_percentage_remaining",
                lambda x: x,
            )
        }
    )

    data_point_handlers = TuyaOnOffManufCluster.data_point_handlers.copy()
    data_point_handlers.update({5: "_dp_2_attr_update"})
    data_point_handlers.update({7: "_dp_2_attr_update"})

class TuyaGardenWatering(CustomDevice):
    """Tuya Garden Watering"""

    signature = {
        MODELS_INFO: [("_TZE200_81isopgh", "TS0601")],
        # TODO : Add the SimpleDescriptor before the PR
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaGardenManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaManufCluster.cluster_id,
                    TuyaGardenManufCluster,
                    TuyaOnOff,
                    TuyaGardenWateringWaterConsumed,
                    TuyaGardenWateringPowerConfiguration,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }