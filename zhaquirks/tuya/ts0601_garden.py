"""Tuya Garden Watering"""

from typing import Dict, Optional, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Groups, Ota, Scenes, Time, PowerConfiguration, AnalogOutput

from zigpy.zcl.clusters.measurement import FlowMeasurement

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from zhaquirks.tuya import TuyaManufCluster, TuyaNewManufCluster, TuyaLocalCluster, TuyaPowerConfigurationCluster2AA
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaOnOff, TuyaOnOffManufCluster, TuyaDPType, TuyaMCUCluster


class TuyaGardenWateringCountdown(AnalogOutput, TuyaLocalCluster):
    """Analog output for valve open countdown time."""


class TuyaGardenWateringWaterConsumed(FlowMeasurement, TuyaLocalCluster):
    """Tuya Water consumed cluster."""


class TuyaGardenWateringPowerConfiguration(PowerConfiguration, TuyaLocalCluster):
    """Tuya PowerConfiguration."""


class TuyaGardenManufCluster(TuyaMCUCluster):
    """On/Off Tuya cluster with extra device attributes."""

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
            dp_type=TuyaDPType.BOOL,
        ),
        5: DPToAttributeMapping(
            TuyaGardenWateringWaterConsumed.ep_attribute,
            "measured_value",
            TuyaDPType.VALUE,
            # lambda x: x,
        ),
        7: DPToAttributeMapping(
            TuyaGardenWateringPowerConfiguration.ep_attribute,
            "battery_percentage_remaining",
            TuyaDPType.VALUE,
            # I don't know why but I had to multiply the value to get it right in HA
            lambda x: x * 2,
        ),
        11: DPToAttributeMapping(
            TuyaGardenWateringCountdown.ep_attribute,
            "present_value",
            TuyaDPType.VALUE,
            # lambda x: x,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
    }


class TuyaGardenWatering(CustomDevice):
    """Tuya Garden Watering"""

    signature = {
        MODELS_INFO: [("_TZE200_81isopgh", "TS0601")],
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10])
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
                    TuyaOnOff,
                    TuyaGardenWateringWaterConsumed,
                    TuyaGardenWateringPowerConfiguration,
                    TuyaGardenWateringCountdown,
                    TuyaGardenManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }